import hashlib
import io
import json
from pathlib import Path

import pytest

from environment.aef import Budget, EvidenceError, RangeFile, RangeStore, decode, select_tiles

URL = "https://storage.googleapis.com/alphaearth_foundations/satellite_embedding/v1/annual/2025/10N/test.tiff"


class Response(io.BytesIO):
    status = 206

    def __init__(self, value, start=0, total=None, etag='"one"'):
        super().__init__(value)
        self.headers = {"Content-Range": f"bytes {start}-{start + len(value) - 1}/{total or len(value)}", "ETag": etag}


def test_range_seek_reads_exact_bytes_and_caches():
    content = bytes(range(256)) * 200
    calls = []

    def request(req, timeout):
        calls.append(req)
        start, end = map(int, req.headers["Range"].split("=")[1].split("-"))
        return Response(content[start : end + 1], start, len(content))

    store = RangeStore(URL, Budget(), request)
    file = RangeFile(store)
    file.seek(25000)
    assert file.read(64) == content[25000:25064]
    file.seek(25000)
    assert file.read(64) == content[25000:25064]
    assert len(calls) == 2 and calls[1].headers["If-match"] == '"one"'
    assert store.budget.used_bytes == 16384 + 64
    file.seek(0, 2)
    assert file.read(1) == b""


@pytest.mark.parametrize("violation", ["status", "etag", "range", "truncated", "budget", "deadline"])
def test_range_failures_cannot_return_a_pixel(violation):
    def request(req, timeout):
        response = Response(b"x" * 16384)
        if violation == "status":
            response.status = 200
        if violation == "etag":
            response.headers.pop("ETag")
        if violation == "range":
            response.headers["Content-Range"] = "bytes 1-16384/16385"
        if violation == "truncated":
            response.truncate(10)
        return response

    budget = Budget(max_bytes=1 if violation == "budget" else 32000000, seconds=-1 if violation == "deadline" else 45)
    with pytest.raises(EvidenceError):
        RangeStore(URL, budget, request)


def test_nodata_and_nonlinear_decode():
    assert decode([64] * 64)[0] == (64 / 127.5) ** 2
    assert decode([-64] * 64)[0] == -((64 / 127.5) ** 2)
    for values in [[-128] * 64, [True] * 64, [0] * 63, [128] * 64]:
        with pytest.raises(EvidenceError):
            decode(values)


def test_unapproved_remote_url_never_calls_network():
    with pytest.raises(EvidenceError):
        RangeStore("http://127.0.0.1/a.tiff", Budget(), lambda *args: pytest.fail("network called"))


def test_pinned_index_blocks_tamper_and_wrong_point(tmp_path):
    path = tmp_path / "index.csv"
    path.write_text("year,wgs84_west,wgs84_south,wgs84_east,wgs84_north\n2025,-123,47,-122,48\n")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(select_tiles(path, sha, 47.6, -122.3, 2025)) == 1
    for latitude, year, fingerprint in [(47.6, 2024, sha), (30, 2025, sha), (47.6, 2025, "bad")]:
        with pytest.raises(EvidenceError):
            select_tiles(path, fingerprint, latitude, -122.3, year)


def test_committed_real_sample_decodes_and_has_partial_read_identity():
    folder = Path(__file__).resolve().parents[2] / "data" / "environment"
    if not (folder / "aef-samples.json").exists():
        pytest.skip("No public sample collected")
    snapshot = json.loads((folder / "aef-samples.json").read_text())
    evidence = json.loads((folder / "aef-samples.evidence.json").read_text())
    record = snapshot["records"][0]
    assert record["embedding"] == decode(record["raw"])
    assert record["sample_sha256"] == hashlib.sha256(bytes(v & 255 for v in record["raw"])).hexdigest()
    assert evidence["whole_object_sha256"] is None
    assert evidence["bytes_read"] <= 32 * 1024 * 1024 and evidence["requests"] <= 80
    assert evidence["object_etag"] == record["object_etag"]
    assert record["point"] == {"lat": 47.6062, "lon": -122.3321}
