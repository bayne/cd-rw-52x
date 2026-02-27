"""Format a datetime as a human-readable relative time string."""

from datetime import datetime


def relative_time(dt: datetime) -> str:
    """Return a short relative time string like '5m ago', '2h ago', '3d ago'."""
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}m ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    if seconds < 86400 * 30:
        days = int(seconds / 86400)
        return f"{days}d ago"
    if seconds < 86400 * 365:
        months = int(seconds / (86400 * 30))
        return f"{months}mo ago"
    years = int(seconds / (86400 * 365))
    return f"{years}y ago"
