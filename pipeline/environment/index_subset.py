"""Extract a bounded, hash-evidenced complete-row subset of the official AEF index.

An explicit byte offset is a search hint, not a spatial assertion. No matching
row fails closed. Example Seattle range: offset 18000000, bytes 8000000.
"""

import argparse
import csv
import hashlib
import io
import json
import multiprocessing
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from environment.aef import INDEX_URL, EvidenceError, NoRedirect


def extract(offset, size, lat, lon):
    if type(offset) is not int or offset < 0 or not 8192 <= size <= 8_000_000:
        raise EvidenceError("Invalid index range budget")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise EvidenceError("Invalid point")
    opened = urllib.request.build_opener(NoRedirect()).open
    started = time.monotonic()
    etag = None
    evidence = []

    def read(start, length):
        nonlocal etag
        remaining = 30 - (time.monotonic() - started)
        if remaining <= 0:
            raise EvidenceError("Index deadline exceeded")
        headers = {"Range": f"bytes={start}-{start + length - 1}", "Accept-Encoding": "identity"}
        if etag:
            headers["If-Match"] = etag
        with opened(urllib.request.Request(INDEX_URL, headers=headers), timeout=min(10, remaining)) as response:
            if response.status != 206 or not response.headers.get("Content-Range", "").startswith(
                f"bytes {start}-{start + length - 1}/"
            ):
                raise EvidenceError("Index range was not honored")
            identity = response.headers.get("ETag")
            if not identity or (etag and identity != etag):
                raise EvidenceError("Index identity changed")
            etag = identity
            data = response.read(length)
            if len(data) != length or time.monotonic() - started > 30:
                raise EvidenceError("Truncated or late index read")
            evidence.append({"content_range": response.headers["Content-Range"], "sha256": hashlib.sha256(data).hexdigest()})
            return data

    header = read(0, 8192).split(b"\n", 1)[0].decode()
    data = read(offset, size)
    lines = data.split(b"\n")[1:-1]  # Discard both partial boundary rows.
    rows = list(csv.DictReader(io.StringIO(header + "\n" + b"\n".join(lines).decode())))
    selected = [
        r
        for r in rows
        if float(r["wgs84_west"]) <= lon <= float(r["wgs84_east"]) and float(r["wgs84_south"]) <= lat <= float(r["wgs84_north"])
    ]
    if not selected:
        raise EvidenceError("No matching complete rows in this bounded range")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=header.split(","), lineterminator="\n")
    writer.writeheader()
    writer.writerows(selected)
    content = output.getvalue().encode()
    return content, {
        "schema_version": "aef-index-subset-v1",
        "source_url": INDEX_URL,
        "source_etag": etag,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "ranges": evidence,
        "bytes_read": size + 8192,
        "requests": 2,
        "subset_sha256": hashlib.sha256(content).hexdigest(),
        "point": {"lat": lat, "lon": lon},
        "rows": len(selected),
        "whole_index_sha256": None,
    }


def worker(connection, args):
    try:
        connection.send({"ok": True, "result": extract(args.offset, args.bytes, args.lat, args.lon)})
    except Exception as error:
        connection.send({"ok": False, "reason": str(error)[:500]})
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offset", type=int, required=True)
    parser.add_argument("--bytes", type=int, default=8_000_000)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-public-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_public_network:
        parser.error("Explicit public network opt-in required")
    # Import the module target so Windows spawn does not look for __main__.worker.
    from environment.index_subset import worker as target

    parent, child = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(target=target, args=(child, args))
    process.start()
    child.close()
    try:
        if not parent.poll(35):
            raise EvidenceError("Index process deadline exceeded")
        result = parent.recv()
    finally:
        if process.is_alive():
            process.terminate()
        process.join(3)
        parent.close()
    if not result["ok"]:
        raise EvidenceError(result["reason"])
    content, evidence = result["result"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    args.output.with_suffix(".evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
