"""Bounded HTTPS retrieval for the reviewed national source allowlist."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, BinaryIO
from zipfile import BadZipFile, ZipFile

from common import REPO_ROOT
from national.registry import cache_path, entries

CHUNK = 64 * 1024
MAX_REDIRECTS = 5


class FetchError(ValueError):
    pass


def _safe_url(value: str, hosts: set[str]) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise FetchError("source URL must be credential-free HTTPS")
    if parsed.hostname.lower() not in hosts:
        raise FetchError(f"source host {parsed.hostname!r} is not allowlisted")
    if parsed.fragment:
        raise FetchError("source URL fragments are not allowed")
    return value


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts: set[str]) -> None:
        self.hosts = hosts
        self.hops = 0

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        self.hops += 1
        if self.hops > MAX_REDIRECTS:
            raise FetchError("source exceeded redirect limit")
        _safe_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_archive(path: Path, entry: dict[str, Any]) -> None:
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > entry.get("max_members", 512):
                raise FetchError("archive has too many members")
            total = 0
            for member in members:
                name = member.filename.replace("\\", "/")
                if name.startswith("/") or ".." in Path(name).parts:
                    raise FetchError("archive contains an unsafe member path")
                if member.flag_bits & 0x1:
                    raise FetchError("encrypted archive members are not allowed")
                total += member.file_size
                if total > entry.get("max_uncompressed_bytes", 128 * 1024 * 1024):
                    raise FetchError("archive exceeds the uncompressed size limit")
    except BadZipFile as exc:
        raise FetchError("source is not a valid ZIP/XLSX archive") from exc


def _read_bounded(response: BinaryIO, limit: int, destination: Path) -> str:
    digest = hashlib.sha256()
    size = 0
    with destination.open("wb") as output:
        while chunk := response.read(CHUNK):
            size += len(chunk)
            if size > limit:
                raise FetchError(f"source exceeded {limit} bytes")
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def refresh(entry: dict[str, Any], root: Path = REPO_ROOT, opener: Any | None = None) -> Path:
    hosts = {host.lower() for host in entry["allowed_hosts"]}
    url = _safe_url(entry["url"], hosts)
    handler = _SafeRedirect(hosts)
    client = opener or urllib.request.build_opener(handler)
    request = urllib.request.Request(url, headers={"User-Agent": "GridBridge/1.0 national-source-refresh"})
    destination = cache_path(entry, root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    temp = Path(tmp_name)
    try:
        with client.open(request, timeout=30) as response:
            final_url = response.geturl()
            _safe_url(final_url, hosts)
            status = getattr(response, "status", 200)
            if status != 200:
                raise FetchError(f"source returned HTTP {status}")
            length = response.headers.get("Content-Length")
            if length and int(length) > entry["max_bytes"]:
                raise FetchError("source declared an oversized response")
            content_type = response.headers.get_content_type()
            if content_type not in entry["content_types"]:
                raise FetchError(f"unexpected source content type {content_type!r}")
            digest = _read_bounded(response, entry["max_bytes"], temp)
        if digest != entry["sha256"]:
            raise FetchError(f"source SHA-256 changed: {digest}")
        _validate_archive(temp, entry)
        temp.replace(destination)
        return destination
    except (OSError, urllib.error.URLError) as exc:
        raise FetchError(f"source retrieval failed: {type(exc).__name__}") from exc
    finally:
        temp.unlink(missing_ok=True)


def refresh_ids(source_ids: list[str], root: Path = REPO_ROOT) -> list[Path]:
    allowed = entries(root)
    unknown = sorted(set(source_ids) - set(allowed))
    if unknown:
        raise FetchError(f"unknown source ids: {unknown}")
    return [refresh(allowed[source_id], root) for source_id in source_ids]
