# F39: Bounded acquisition of larger PSC public records

The default 15,000,000-byte response cap excludes the PSC-published FPL plan: the linked 2026 response reports
29,110,791 bytes, and the public index lists the 2025 file as 54,057 KB. Both are exact links obtained from the
PSC's published plan index. A failed byte-cap check is an acquisition limit, not evidence of inaccessible content.

For these two exact regulatory-record links only, allow 65,000,000 bytes per response, 90 seconds per request and
one retry, at most 4 requests total. Keep the ordinary 15 MB / 45 second limits for other sources. Store raw PDFs
outside Git; record actual response bytes, hash, URL and retrieval time. Inspect content restrictions before
extracting candidate construction facts. No permission is inferred to scrape FPL's separately restricted host,
use unseen private attachments, or publish raw PDFs. Partial/oversized/error responses cannot become inputs.

This is a reversible F39 acquisition setting for the already authorized Florida provider audit. Restore the
standard cap by removing the scoped override after these records are acquired. No schema, writer or source
eligibility rule changes. Dates/status/geometry require their normal evidence checks.
