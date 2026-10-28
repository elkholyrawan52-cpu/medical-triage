"""Certainty Factor (MYCIN-style) combination for positive evidence."""


def combine(cf1: float, cf2: float) -> float:
    """CF = CF1 + CF2 * (1 - CF1)"""
    return cf1 + cf2 * (1 - cf1)


def combine_all(cfs):
    total = 0.0
    for cf in cfs:
        total = combine(total, cf)
    return total
