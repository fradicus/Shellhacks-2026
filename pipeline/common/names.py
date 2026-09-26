import re

_PAREN = re.compile(r"\([^)]*\)")
_NUMBER = re.compile(r"#\s*\d+")
_NOISE = re.compile(r"\b(SUBSTATION|SUB|PRIMARY|SS|TS)\b")
_SPACES = re.compile(r"\s+")


def norm_name(s: str) -> str:
    """Normalize a substation name for candidate matching: 'Thurmond Dam (USA) #5 Sub' -> 'THURMOND DAM'."""
    s = _PAREN.sub(" ", s.upper())
    s = _NUMBER.sub(" ", s)
    s = _NOISE.sub(" ", s)
    return _SPACES.sub(" ", s).strip()
