"""
MACI Mathematical Utilities.

Core math for the negotiation engine:
- Friction Exchange Rate (local delegate logic)
- Convergence Window enforcement (global orchestrator logic)
"""

from datetime import datetime


def calculate_friction_cost(
    price_cents: int,
    layover_minutes: int,
    friction_weight_cents: int = 2500,
) -> int:
    """
    Calculate the friction-adjusted total cost of a flight.

    Formula: Cost_total = P_base + (h_layover × W_f)

    Args:
        price_cents: Base ticket price in cents.
        layover_minutes: Total layover duration in minutes.
        friction_weight_cents: Cost penalty per hour of layover in cents.
                              Default: 2500 ($25/hour).

    Returns:
        Friction-adjusted cost in cents (integer).

    Example:
        $300 flight with 4-hour layover at $25/hr friction:
        30000 + (4.0 × 2500) = 40000 cents ($400 effective cost)
    """
    layover_hours = layover_minutes / 60.0
    friction_penalty = int(layover_hours * friction_weight_cents)
    return price_cents + friction_penalty


def calculate_arrival_spread_minutes(arrival_times: list[datetime]) -> int:
    """
    Calculate the spread between the earliest and latest arrival times.

    Args:
        arrival_times: List of UTC arrival datetimes from all clusters.

    Returns:
        Spread in minutes (integer).
    """
    if len(arrival_times) <= 1:
        return 0

    earliest = min(arrival_times)
    latest = max(arrival_times)
    spread_seconds = (latest - earliest).total_seconds()
    return int(spread_seconds / 60)


def check_convergence(
    arrival_times: list[datetime],
    max_spread_minutes: int,
) -> tuple[bool, int]:
    """
    Check if all cluster arrivals are within the allowed convergence window.

    Args:
        arrival_times: List of UTC arrival datetimes from all clusters.
        max_spread_minutes: Maximum allowed Δt_max in minutes.

    Returns:
        Tuple of (converged: bool, actual_spread_minutes: int).
    """
    spread = calculate_arrival_spread_minutes(arrival_times)
    return spread <= max_spread_minutes, spread


def compute_required_arrival_shift(
    outlier_arrival: datetime,
    target_arrival: datetime,
) -> int:
    """
    Calculate how many minutes an outlier cluster must shift its arrival.

    Positive = must arrive earlier. Negative = must arrive later.

    Args:
        outlier_arrival: The outlier cluster's current arrival time.
        target_arrival: The target arrival time to converge toward.

    Returns:
        Required shift in minutes (positive = earlier, negative = later).
    """
    delta_seconds = (outlier_arrival - target_arrival).total_seconds()
    return int(delta_seconds / 60)


def find_outlier_cluster(
    cluster_arrivals: dict[str, datetime],
    max_spread_minutes: int,
) -> str | None:
    """
    Identify the cluster whose arrival time is furthest from the group median.

    This is the cluster the orchestrator will ask to renegotiate.

    Args:
        cluster_arrivals: Dict of {cluster_key: arrival_utc}.
        max_spread_minutes: Maximum allowed arrival spread.

    Returns:
        The cluster_key of the outlier, or None if already converged.
    """
    if len(cluster_arrivals) <= 1:
        return None

    arrivals = list(cluster_arrivals.values())
    converged, _ = check_convergence(arrivals, max_spread_minutes)
    if converged:
        return None

    # Find the median arrival time
    sorted_arrivals = sorted(arrivals)
    median_idx = len(sorted_arrivals) // 2
    median_arrival = sorted_arrivals[median_idx]

    # Find the cluster furthest from the median
    max_distance = 0
    outlier_key = None
    for key, arrival in cluster_arrivals.items():
        distance = abs((arrival - median_arrival).total_seconds())
        if distance > max_distance:
            max_distance = distance
            outlier_key = key

    return outlier_key
