"""Fail closed on shape, citations, cross-fact numbers and prohibited claims."""

import json
import re
from decimal import Decimal, InvalidOperation

from jsonschema import Draft202012Validator

PROMPT_VERSION = "coordination-brief-v2"
SCHEMA_VERSION = "coordination-response-v1"
ACTIVITIES = ("crews", "equipment", "freight/mobilization", "matting", "outage window", "landowner outreach", "procurement")
ITEM = {"type": "object", "additionalProperties": False, "required": ["text", "fact_ids"], "properties": {
    "text": {"type": "string", "minLength": 1, "maxLength": 2000},
    "fact_ids": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}}}}
RESPONSE_SCHEMA = {"type": "object", "additionalProperties": False,
                   "required": ["supported_facts", "possible_shared_activities", "questions", "limitations"], "properties": {
    "supported_facts": {"type": "array", "minItems": 1, "maxItems": 20, "items": ITEM},
    "possible_shared_activities": {"type": "array", "maxItems": 7, "items": ITEM},
    "questions": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string", "minLength": 1}},
    "limitations": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
}}
NUMBER = re.compile(r"(?<![A-Za-z0-9])[+-]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][+-]?\d+)?%?")
NUMBER_WORDS = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                          r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
                          r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|"
                          r"dozen|half|quarter|double|triple|percent)\b", re.I)
FORBIDDEN = re.compile(r"\bsavings?\b|\bsave[ds]?\s+(?:money|costs?|\$)|\bbuilt at the same time\b|"
                       r"\bsimultaneous(?:ly)?\b|\bconcurrent(?:ly)?\b|\bconstruction (?:overlap|window)s?\b|"
                       r"\boverlapping construction\b|\b(?:built|constructed|construction)\b.{0,50}"
                       r"\b(?:together|same time|overlap)\b", re.I)


def numbers(value: object) -> set[str]:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    try:
        numeric = {str(Decimal(n.replace(",", "").rstrip("%")).normalize()) + ("%" if n.endswith("%") else "")
                   for n in NUMBER.findall(text)}
    except InvalidOperation:
        numeric = {"invalid_numeric_literal"}
    # Word quantities must themselves occur in cited text; never manufacture a numeric phrase from digits.
    return numeric | {"word:" + n.lower() for n in NUMBER_WORDS.findall(text)}


def typed_numbers_supported(text: str, cited: dict) -> bool:
    """An identifier/year/voltage cannot authorize a distance or gap with the same digits."""
    # No language-to-number inference: display deterministic measurements as supplied digits.
    if NUMBER_WORDS.search(text) and re.search(
            r"\b(?:miles?|mi|days?|distance|gap|apart|kv|volts?|dollars?|costs?|percent)\b|[$%]", text, re.I):
        return False
    dates = list(re.finditer(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b", text))
    for token in NUMBER.finditer(text):
        suffix = text[token.end():].lower()
        prefix = text[:token.start()].lower()
        eligible = {}
        if re.match(r"\s*(?:miles?|mi)\b", suffix):
            eligible = {k: v for k, v in cited.items() if k in ("match.distance_mi", "match.distance_display_mi")}
        elif re.match(r"\s*days?\b", suffix):
            eligible = {k: v for k, v in cited.items() if k == "match.time_gap_days"}
        elif re.match(r"\s*kv\b", suffix):
            eligible = {k: v for k, v in cited.items() if k.endswith((".name", ".description"))
                        and re.search(re.escape(token.group()) + r"\s*kv\b", str(v), re.I)}
        elif any(d.start() <= token.start() < d.end() for d in dates):
            eligible = {k: v for k, v in cited.items() if k.endswith(".in_service") or k == "match.analysis_date"}
        elif re.search(r"\b(?:project|id|code)\s*[:#]?\s*$", prefix):
            eligible = {k: v for k, v in cited.items() if k.endswith((".native_id", ".owner_code"))}
        elif re.search(r"\b(?:gap|days?)\b", text, re.I):
            eligible = {k: v for k, v in cited.items() if k == "match.time_gap_days"}
        elif re.search(r"\b(?:distance|miles?|apart)\b", text, re.I):
            eligible = {k: v for k, v in cited.items() if k in ("match.distance_mi", "match.distance_display_mi")}
        elif re.search(r"\b(?:date|milestone|in.service)\b", text, re.I):
            eligible = {k: v for k, v in cited.items() if k.endswith(".in_service") or k == "match.analysis_date"}
        allowed = set().union(*(numbers(v) for v in eligible.values()))
        if numbers(token.group()) - allowed:
            return False
    # There is no monetary/percentage fact in this projection; numbers cannot become such quantities.
    if NUMBER.search(text) and re.search(r"[$%]|\b(?:dollars?|costs?|percent)\b", text, re.I):
        return False
    return True


def validate_response(raw: str, facts: list[dict]) -> tuple[dict | None, list[str]]:
    if len(raw) > 100_000:
        return None, ["response_too_large"]
    try:
        response = json.loads(raw)
    except (ValueError, TypeError):
        return None, ["invalid_json"]
    if list(Draft202012Validator(RESPONSE_SCHEMA).iter_errors(response)):
        return None, ["invalid_response_shape"]
    by_id = {f["id"]: f["value"] for f in facts}
    errors = []
    for group in ("supported_facts", "possible_shared_activities"):
        for item in response[group]:
            refs = item["fact_ids"]
            if any(ref not in by_id for ref in refs):
                errors.append("unknown_fact_id")
            allowed = set().union(*(numbers(by_id[ref]) for ref in refs if ref in by_id))
            if numbers(item["text"]) - allowed:
                errors.append("number_not_in_cited_facts")
            if not typed_numbers_supported(item["text"], {ref: by_id[ref] for ref in refs if ref in by_id}):
                errors.append("numeric_fact_type_mismatch")
            if group == "possible_shared_activities":
                text = item["text"].casefold()
                if (not any(activity in text for activity in ACTIVITIES)
                        or not re.search(r"\b(possible|could|may|potential)\b", text)):
                    errors.append("activity_not_allowed_or_not_tentative")
    all_numbers = set().union(*(numbers(f["value"]) for f in facts))
    for text in response["questions"] + response["limitations"]:
        if numbers(text) - all_numbers:
            errors.append("number_not_in_input")
        if not typed_numbers_supported(text, by_id):
            errors.append("numeric_fact_type_mismatch")
    texts = [item["text"] for group in ("supported_facts", "possible_shared_activities") for item in response[group]]
    texts += response["questions"] + response["limitations"]
    if any(FORBIDDEN.search(text) for text in texts):
        errors.append("prohibited_claim")
    return response, sorted(set(errors))
