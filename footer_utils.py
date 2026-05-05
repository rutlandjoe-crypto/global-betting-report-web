from datetime import datetime
from zoneinfo import ZoneInfo


DISCLAIMER_LONG = (
    "This report is an automated summary of game data, designed to support—not replace—"
    "human sports journalism."
)

DISCLAIMER_SHORT = (
    "Automated game data summary built to support—not replace—human sports journalism."
)


def format_timestamp(dt: datetime | None = None, tz_name: str = "America/New_York") -> str:
    """
    Return a newsroom-style timestamp like:
    April 7, 2026 | 7:17 AM ET
    """
    tz = ZoneInfo(tz_name)
    now = dt.astimezone(tz) if dt else datetime.now(tz)

    tz_label_map = {
        "America/New_York": "ET",
        "America/Chicago": "CT",
        "America/Denver": "MT",
        "America/Los_Angeles": "PT",
    }
    tz_label = tz_label_map.get(tz_name, now.tzname() or "")

    month = now.strftime("%B")
    day = now.day
    year = now.year
    time_str = now.strftime("%I:%M %p").lstrip("0")

    return f"{month} {day}, {year} | {time_str} {tz_label}"


def build_report_footer(
    platform: str,
    dt: datetime | None = None,
    tz_name: str = "America/New_York",
    x_handle: str = "@GlobalSportsRep",
) -> str:
    """
    Build a standardized footer for Substack, Telegram, or X.
    """
    platform_key = platform.strip().lower()
    timestamp = format_timestamp(dt=dt, tz_name=tz_name)

    if platform_key == "substack":
        return (
            f"{DISCLAIMER_LONG}\n\n"
            f"Generated: {timestamp}\n\n"
            f"Follow Global Sports Report on X: {x_handle}"
        )

    if platform_key == "telegram":
        return (
            f"{DISCLAIMER_LONG}\n\n"
            f"{timestamp}\n\n"
            f"Follow {x_handle} for daily updates."
        )

    if platform_key in {"x", "twitter"}:
        return (
            f"{DISCLAIMER_SHORT}\n\n"
            f"Follow {x_handle}"
        )

    raise ValueError(f"Unsupported platform: {platform}")