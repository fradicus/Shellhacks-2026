import hashlib
import io
from email.message import Message
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from national.fetch import FetchError, _safe_url, _SafeRedirect, refresh


def zipped(name="safe.txt", payload=b"public data"):
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return output.getvalue()


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, url, *, declared=None):
        super().__init__(data)
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "application/zip"
        self.headers["Content-Length"] = str(len(data) if declared is None else declared)

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Opener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout):
        return self.response


def entry(data, **changes):
    value = {
        "id": "reviewed",
        "cache_name": "reviewed.zip",
        "url": "https://public.example/reviewed.zip",
        "allowed_hosts": ["public.example"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "max_bytes": len(data) + 10,
        "content_types": ["application/zip"],
        "max_members": 5,
        "max_uncompressed_bytes": 100,
    }
    value.update(changes)
    return value


def test_refresh_is_bounded_hash_checked_and_atomic(tmp_path):
    data = zipped()
    path = refresh(entry(data), tmp_path, Opener(Response(data, "https://public.example/reviewed.zip")))
    assert path.read_bytes() == data


def test_refresh_rejects_oversize_and_unsafe_archive(tmp_path):
    data = zipped()
    response = Response(data, "https://public.example/reviewed.zip", declared=9999)
    with pytest.raises(FetchError, match="oversized"):
        refresh(entry(data), tmp_path, Opener(response))
    assert response.closed
    unsafe = zipped("../escape.txt")
    with pytest.raises(FetchError, match="unsafe member"):
        refresh(entry(unsafe), tmp_path, Opener(Response(unsafe, "https://public.example/reviewed.zip")))
    assert not (tmp_path / "data" / "national" / "cache" / "reviewed.zip").exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://public.example/reviewed.zip",
        "https://user:password@public.example/reviewed.zip",
        "https://other.example/reviewed.zip",
        "https://public.example/reviewed.zip#token",
    ],
)
def test_source_url_must_remain_allowlisted_credential_free_https(url):
    with pytest.raises(FetchError):
        _safe_url(url, {"public.example"})


def test_redirect_handler_validates_every_hop_and_enforces_limit():
    handler = _SafeRedirect({"public.example"})
    with pytest.raises(FetchError, match="credential-free HTTPS"):
        handler.redirect_request(None, None, 302, "", {}, "http://public.example/reviewed.zip")
    with pytest.raises(FetchError, match="not allowlisted"):
        handler.redirect_request(None, None, 302, "", {}, "https://other.example/reviewed.zip")
    handler.hops = 5
    with pytest.raises(FetchError, match="redirect limit"):
        handler.redirect_request(None, None, 302, "", {}, "https://public.example/reviewed.zip")
