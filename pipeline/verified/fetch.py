from __future__ import annotations

import hashlib
import io
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

ARCHIVE_URL = "https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip"
ARCHIVE_SHA256 = "77ce49c60ac5a6bad50c442fc401aad5404a21da875dc5cbaba353af5ede54de"
MAX_ARCHIVE_BYTES = 10_000_000
MAX_MEMBER_BYTES = 5_000_000
MAX_REDIRECTS = 4


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _approved(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == "www.eia.gov" and not parsed.username and not parsed.password


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def fetch_archive(url: str = ARCHIVE_URL) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect)
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not _approved(current):
            raise ValueError("EIA refresh URL must remain credential-free HTTPS on www.eia.gov")
        try:
            response = opener.open(urllib.request.Request(current, headers={"User-Agent": "GridBridge/1.0"}), timeout=20)
        except urllib.error.HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                raise
            location = error.headers.get("Location")
            if not location:
                raise ValueError("EIA refresh redirect omitted Location") from error
            current = urljoin(current, location)
            continue
        try:
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_ARCHIVE_BYTES:
                raise ValueError("EIA archive exceeds the bounded download size")
            data = response.read(MAX_ARCHIVE_BYTES + 1)
        finally:
            response.close()
        if len(data) > MAX_ARCHIVE_BYTES:
            raise ValueError("EIA archive exceeds the bounded download size")
        return data
    raise ValueError("EIA refresh exceeded the redirect bound")


def checked_archive(path: Path, *, refresh: bool = False) -> tuple[bytes, dict[str, bytes]]:
    if refresh:
        data = fetch_archive()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    elif path.exists():
        data = path.read_bytes()
    else:
        raise FileNotFoundError(f"reviewed EIA cache missing: {path}")
    if sha256_bytes(data) != ARCHIVE_SHA256:
        raise ValueError("EIA archive hash does not match the reviewed 2024 final release")
    wanted = {"Frame_2024.xlsx", "Utility_Data_2024.xlsx", "Service_Territory_2024.xlsx"}
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            leaf = Path(info.filename).name
            if leaf not in wanted:
                continue
            if info.flag_bits & 1 or info.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"unsafe or oversized EIA archive member: {leaf}")
            members[leaf] = archive.read(info)
    missing = wanted - members.keys()
    if missing:
        raise ValueError(f"EIA archive is missing reviewed members: {sorted(missing)}")
    return data, members
