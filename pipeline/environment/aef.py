"""Read one 10m AEF pixel via budgeted HTTP ranges and Rasterio's custom opener.

The index can be a reviewed complete-row subset of the official CSV. Its hash
identifies only those provided bytes, never the entire upstream index.
"""

import csv
import hashlib
import io
import math
import re
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

PREFIX = "https://storage.googleapis.com/alphaearth_foundations/satellite_embedding/v1/annual/"
INDEX_URL = PREFIX + "aef_index.csv"
ATTRIBUTION = "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind."


class EvidenceError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError("Redirect rejected")


@dataclass
class Budget:
    max_bytes: int = 32 * 1024 * 1024
    max_requests: int = 80
    seconds: float = 45
    used_bytes: int = 0
    requests: int = 0
    started: float = field(default_factory=time.monotonic)

    def remaining(self):
        value = self.seconds - (time.monotonic() - self.started)
        if value <= 0:
            raise EvidenceError("AEF elapsed-time budget exceeded")
        return value


class RangeStore:
    """Shared range evidence and budget, independent cursors for GDAL handles."""

    def __init__(self, url, budget, opener=None):
        if not re.fullmatch(re.escape(PREFIX) + r"\d{4}/\d{1,2}[NS]/[A-Za-z0-9_-]+\.tiff", url):
            raise EvidenceError("Unapproved AEF object URL")
        self.url, self.budget = url, budget
        self.open = opener or urllib.request.build_opener(NoRedirect()).open
        self.length = None
        self.etag = None
        self.ranges = []
        self.cache = []
        self.read_range(0, 16384)

    def read_range(self, start, count):
        self.budget.remaining()
        if count <= 0:
            return b""
        for offset, data in self.cache:
            if start >= offset and start + count <= offset + len(data):
                return data[start - offset : start - offset + count]
        if count > self.budget.max_bytes - self.budget.used_bytes or self.budget.requests >= self.budget.max_requests:
            raise EvidenceError("AEF byte/request budget exceeded")
        headers = {"Range": f"bytes={start}-{start + count - 1}", "Accept-Encoding": "identity"}
        if self.etag:
            headers["If-Match"] = self.etag
        self.budget.requests += 1
        with self.open(urllib.request.Request(self.url, headers=headers), timeout=min(10, self.budget.remaining())) as response:
            if response.status != 206:
                raise EvidenceError("AEF server did not honor bounded range")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if not match or int(match[1]) != start or int(match[2]) >= start + count:
                raise EvidenceError("Invalid content range")
            total, last = int(match[3]), int(match[2])
            expected = min(count, total - start)
            if last - start + 1 != expected or expected <= 0:
                raise EvidenceError("Incomplete content range")
            etag = response.headers.get("ETag")
            if not etag or etag.startswith("W/") or (self.etag and etag != self.etag) or (self.length and total != self.length):
                raise EvidenceError("AEF object identity changed or is absent")
            self.etag, self.length = etag, total
            chunks = []
            remaining = expected
            while remaining:
                self.budget.remaining()
                part = response.read(min(65536, remaining))
                self.budget.used_bytes += len(part)
                if not part:
                    raise EvidenceError("Truncated AEF response")
                chunks.append(part)
                remaining -= len(part)
            self.budget.remaining()
            data = b"".join(chunks)
        self.cache.append((start, data))
        self.ranges.append({"start": start, "end": start + len(data) - 1, "sha256": hashlib.sha256(data).hexdigest()})
        return data

    def opener(self, path, mode="rb"):
        if path != "sample.tiff" or mode not in ("r", "rb"):
            raise FileNotFoundError(path)
        return RangeFile(self)


class RangeFile(io.RawIOBase):
    def __init__(self, store):
        self.store, self.position = store, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position + offset if whence == 1 else self.store.length + offset
        if whence not in (0, 1, 2) or position < 0:
            raise EvidenceError("Invalid seek")
        self.position = position
        return position

    def read(self, size=-1):
        remaining = max(0, self.store.length - self.position)
        count = remaining if size < 0 else min(size, remaining)
        data = self.store.read_range(self.position, count)
        self.position += len(data)
        return data


def decode(values):
    if len(values) != 64 or any(type(v) is not int or v < -127 or v > 127 for v in values):
        raise EvidenceError("AEF pixel is nodata or invalid int8/64-band data")
    return [math.copysign((v / 127.5) ** 2, v) if v else 0.0 for v in values]


def select_tiles(index: Path, expected_hash: str, lat: float, lon: float, year: int):
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise EvidenceError("Invalid point")
    if type(year) is not int or not 2017 <= year <= 2100:
        raise EvidenceError("Invalid year")
    if index.stat().st_size > 64 * 1024 * 1024:
        raise EvidenceError("Index exceeds 64MiB: provide an explicitly reviewed complete-row subset")
    content = index.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise EvidenceError("Index hash mismatch")
    rows = []
    for row in csv.DictReader(io.StringIO(content.decode("utf-8"))):
        if int(row["year"]) != year:
            continue
        if float(row["wgs84_west"]) <= lon <= float(row["wgs84_east"]) and float(row["wgs84_south"]) <= lat <= float(
            row["wgs84_north"]
        ):
            rows.append(row)
    if not rows or len(rows) > 4:
        raise EvidenceError("Index has no bounded unambiguous candidate set for point/year")
    return rows


def sample(index, expected_hash, lat, lon, year, budget=None):
    import rasterio
    from rasterio.warp import transform
    from rasterio.windows import Window

    budget = budget or Budget()
    rows = select_tiles(Path(index), expected_hash, lat, lon, year)
    errors = []
    for row in rows:
        url = row["path"].replace("gs://alphaearth_foundations/", "https://storage.googleapis.com/alphaearth_foundations/")
        if f"/annual/{year}/" not in url:
            raise EvidenceError("Index year/object disagreement")
        store = RangeStore(url, budget)
        try:
            # Custom opener is essential: plain file-like input is copied wholesale by Rasterio.
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_NUM_THREADS="1"):
                with rasterio.open("sample.tiff", opener=store.opener, driver="GTiff") as dataset:
                    if dataset.count != 64 or set(dataset.dtypes) != {"int8"} or dataset.nodata != -128:
                        raise EvidenceError("Unexpected AEF raster bands/dtype/nodata")
                    if str(dataset.crs) != row["crs"] or dataset.res != (10.0, 10.0):
                        raise EvidenceError("Unexpected AEF CRS/pixel size")
                    bounds = dataset.bounds
                    normalized = (
                        min(bounds.left, bounds.right),
                        min(bounds.bottom, bounds.top),
                        max(bounds.left, bounds.right),
                        max(bounds.bottom, bounds.top),
                    )
                    if normalized != tuple(float(row[k]) for k in ("utm_west", "utm_south", "utm_east", "utm_north")):
                        raise EvidenceError("Index/raster bounds mismatch")
                    x, y = transform("EPSG:4326", dataset.crs, [lon], [lat])
                    pixel_row, col = dataset.index(x[0], y[0])
                    if not 0 <= pixel_row < dataset.height or not 0 <= col < dataset.width:
                        raise EvidenceError("Point outside raster")
                    raw = [int(v) for v in dataset.read(window=Window(col, pixel_row, 1, 1))[:, 0, 0]]
                    embedding = decode(raw)
                    record = {
                        "point": {"lat": lat, "lon": lon},
                        "year": year,
                        "object_url": url,
                        "object_etag": store.etag,
                        "index_sha256": expected_hash,
                        "sample_sha256": hashlib.sha256(bytes(v & 255 for v in raw)).hexdigest(),
                        "crs": str(dataset.crs),
                        "row": pixel_row,
                        "col": col,
                        "pixel_size_m": 10,
                        "raw": raw,
                        "embedding": embedding,
                        "attribution": ATTRIBUTION,
                    }
            budget.remaining()
            evidence = {
                "index_source_url": INDEX_URL,
                "index_scope": "exact provided CSV bytes; may be a reviewed subset",
                "index_sha256": expected_hash,
                "object_url": url,
                "object_etag": store.etag,
                "object_size": store.length,
                "ranges": store.ranges,
                "bytes_read": budget.used_bytes,
                "requests": budget.requests,
                "elapsed_seconds": time.monotonic() - budget.started,
                "whole_object_sha256": None,
                "rasterio_version": rasterio.__version__,
            }
            return record, evidence
        except EvidenceError as error:
            errors.append(str(error))
    raise EvidenceError("; ".join(errors) or "No valid pixel")


def worker(connection, args):
    """Importable spawn target, including on Windows."""
    try:
        connection.send({"ok": True, "result": sample(args.index, args.index_sha256, args.lat, args.lon, args.year)})
    except Exception as error:
        connection.send({"ok": False, "reason": str(error)[:500]})
    finally:
        connection.close()
