from datetime import datetime, timezone

from croniter import croniter


def compute_next_run(cron_expr: str | None) -> datetime | None:
    if not cron_expr:
        return None
    base = datetime.now(timezone.utc)
    itr = croniter(cron_expr, base)
    return itr.get_next(datetime)