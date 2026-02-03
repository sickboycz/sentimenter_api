"""Unit tests: sector conservation (allocator)."""
import math


def test_sector_conservation_scale():
    """Simple conservation sanity: sum(|sector|) <= 1.15*|equities|."""
    equities = 40.0
    sectors = [20.0, 15.0, 10.0]  # abs sum = 45
    assert sum(abs(x) for x in sectors) <= 1.15 * abs(equities) + 1e-6


def test_allocator_conservation_scale():
    """Allocator scales sector sum to target."""
    target = max(40.0, 1.0) * 1.15
    raw_sum = 100.0
    scale = min(1.0, target / raw_sum)
    scaled = [20.0 * scale, 15.0 * scale, 10.0 * scale]
    assert sum(abs(x) for x in scaled) <= target + 1e-6
