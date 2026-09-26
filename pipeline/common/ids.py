def project_id(project_key: str, source_id: str) -> str:
    """`DESC:6807B` + `desc-2024-2028` -> `DESC:6807B@desc-2024-2028` (one record per project per filing)."""
    return f"{project_key}@{source_id}"


def match_id(key_a: str, key_b: str) -> str:
    """Order-independent pair id: the two project keys sorted and joined by `__`."""
    return "__".join(sorted((key_a, key_b)))
