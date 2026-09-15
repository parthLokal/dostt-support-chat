from datetime import UTC, datetime, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ist_now() -> datetime:
    return utcnow() + IST_OFFSET


def is_within_business_hours(dt: datetime | None = None) -> bool:
    """9 AM - 7 PM IST, per the support PRD's callback-consent note."""
    hour = (dt or ist_now()).hour
    return 9 <= hour < 19
