from __future__ import annotations

from app.config import INTAKE_RETENTION_DAYS
from app.intake import repo
from app.intake.storage import delete_job_files


def sweep_intake_retention() -> int:
    """
    Delete intake jobs (and DB rows) older than INTAKE_RETENTION_DAYS.

    Returns number of jobs removed.
    """
    days = int(INTAKE_RETENTION_DAYS)
    if days <= 0:
        return 0
    ids = repo.list_jobs_older_than_days(days)
    n = 0
    for jid in ids:
        delete_job_files(jid)
        if repo.delete_job_cascade(jid):
            n += 1
    return n
