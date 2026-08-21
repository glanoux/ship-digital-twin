"""
Predictive layer: is the ship burning more fuel than it should?

This is what separates a *predictive* twin from a *descriptive* one (see
docs/concepts.md). A descriptive twin just reports "current fuel rate is
X L/h". A predictive twin also knows what X *should* be for the current
speed -- from a reference model, here a fixed calm-water curve representing
the ship's as-built performance -- and can therefore surface a deviation
that isn't visible in any single sensor reading. In practice: this is how
hull fouling, propeller damage, or engine degradation get caught before
they become a bigger problem.

Note this module never reads simulation.ship_simulator's hidden fouling
state -- only observable telemetry (speed, actual fuel rate). It has to
detect the drift the same way a real analytics layer would: by comparison
with the baseline, not by cheating and reading the ship's internals.
"""

from dataclasses import dataclass

# As-built calm-water reference curve (e.g. from sea trials / towing-tank
# data at commissioning). Deliberately independent of whatever the simulator
# does internally -- a real baseline would come from the ship's spec sheet,
# not from peeking at "ground truth".
BASELINE_FUEL_K = 0.55


def expected_fuel_rate_lph(speed_knots: float) -> float:
    return BASELINE_FUEL_K * speed_knots ** 3


@dataclass
class PerformanceReport:
    avg_deviation_pct: float | None
    status: str
    n_samples: int


def analyze(history: list[dict], min_speed_knots: float = 5.0, window: int = 300) -> PerformanceReport:
    """Compare recent actual fuel rate against the baseline-expected rate."""
    recent = history[-window:]
    deviations = []
    for row in recent:
        speed = row["speed_knots"]
        if speed < min_speed_knots:
            continue
        expected = expected_fuel_rate_lph(speed)
        if expected < 1.0:
            continue
        deviations.append((row["fuel_rate_lph"] - expected) / expected * 100.0)

    if not deviations:
        return PerformanceReport(None, "insufficient data", 0)

    avg = sum(deviations) / len(deviations)
    if avg < 5:
        status = "nominal"
    elif avg < 15:
        status = "elevated -- monitor"
    else:
        status = "hull fouling likely -- schedule inspection"
    return PerformanceReport(avg_deviation_pct=avg, status=status, n_samples=len(deviations))
