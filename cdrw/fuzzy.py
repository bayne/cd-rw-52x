"""Simple fuzzy matching: check if all characters of pattern appear in order in text."""


def fuzzy_match(pattern: str, text: str) -> tuple[bool, list[int]]:
    """Check if pattern fuzzy-matches text (case-insensitive).

    Returns (matched, indices) where indices are positions in text that matched.
    Indices are guaranteed to be in ascending order.
    """
    if not pattern:
        return True, []

    pattern_lower = pattern.lower()
    text_lower = text.lower()

    indices: list[int] = []
    pi = 0
    for ti, ch in enumerate(text_lower):
        if pi < len(pattern_lower) and ch == pattern_lower[pi]:
            indices.append(ti)
            pi += 1

    matched = pi == len(pattern_lower)
    return matched, indices if matched else []
