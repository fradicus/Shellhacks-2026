---
name: gemini-api
description: How Gridlock calls the Google Gemini API - SDKs, model selection, structured JSON output, PDF input, function calling, and the four Gemini features. Use for any Gemini code.
---

# Gemini API

Key: `GEMINI_API_KEY` from Google AI Studio (https://aistudio.google.com/apikey). Model: `GEMINI_MODEL`
env; set it to the newest Flash model listed in AI Studio (fast, cheap, free tier). Use Pro only if Flash quality fails a check.

SDKs: Python `google-genai` (`from google import genai; client = genai.Client()`), Node `@google/genai`.
Both read `GEMINI_API_KEY` from env.

## Structured output (always)
```python
resp = client.models.generate_content(
    model=os.environ["GEMINI_MODEL"], contents=[prompt],
    config={"response_mime_type": "application/json", "response_schema": MyPydanticModel})
data = resp.parsed
```
Invalid or missing -> retry once -> raise. Never regex JSON out of free text.

## PDF input
Small page ranges: upload with `client.files.upload(file=path)` and pass the file in `contents`, or send
`pdftotext` output as text (cheaper, usually enough for tables).

## The four features
1. **Row joining** (GPC tables): input page text, output `[{zone, year, teams, name, need_date, sponsor}]`.
2. **Geocode adjudication**: input project name/zone/description + <= 5 OSM candidates (name, tags, lat/lon, county). Output `{choice_index | null, confidence: medium|low, reason}`.
3. **Coordination brief**: input one overlap record (both projects, distance, gap, estimate). Output `{headline, brief (<=120 words), shareable: [crews|equipment|freight|row|outage_window]}`. System prompt: "Use only numbers present in the input."
4. **`/api/ask`**: function calling with one declared tool `query_overlaps({filters, sort, limit})`; execute via the Backend's whitelisted executor; second call turns results into a 1-2 sentence answer. Return `{answer, ids}`.

Cache pipeline outputs in `data/` so reruns don't re-bill. Log model name with each stored output.
