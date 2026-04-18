"""Calendar-aware date arithmetic for subscription expiry.

A 12-month subscription means "same day next year", not +360 days.
Using timedelta(days=period_months * 30) drifts ~5 days per year against
the calendar, which users notice on long-period plans and which makes
pro-rata refunds inaccurate.
"""

import calendar
from datetime import datetime


def add_months(dt: datetime, months: int) -> datetime:
    """Return dt + N calendar months, clamping day to the target month's length.

    add_months(2026-01-31, 1) -> 2026-02-28 (or 29 on a leap year)
    add_months(2026-03-15, 12) -> 2027-03-15
    """
    if months <= 0:
        return dt
    zero_based = dt.month - 1 + months
    year = dt.year + zero_based // 12
    month = zero_based % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)
