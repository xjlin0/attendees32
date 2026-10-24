from datetime import datetime
from celery.utils.log import get_task_logger
import pghistory
from config import celery_app
from attendees.persons.services import AttendeeService

logger = get_task_logger(__name__)


@celery_app.task()
@pghistory.context(modifier="advancing grades task")
def advance_grades(organization_infos=None, organization_slug=None, dry_run=False):
    """
    Periodic / on-demand Celery task to advance school grades for attendees.
    Can take arguments from model of 'periodic task' or management command.

    :param organization_infos: optional list of dicts, e.g. [{"organization_slug": "..."}]
    :param organization_slug: optional string for a single organization slug
    :param dry_run: boolean, if True does not commit changes to DB
    :return: dictionary of logs and processing results
    """
    begin = datetime.utcnow().replace(microsecond=0)
    logger.info(
        f"advance_grades task ran at {begin.isoformat()}(UTC) from "
        f"{__package__}/persons/tasks.py with organization_infos={organization_infos}, "
        f"organization_slug={organization_slug}, dry_run={dry_run}."
    )
    results = AttendeeService.advance_grades(
        organization_infos=organization_infos,
        organization_slug=organization_slug,
        dry_run=dry_run,
    )
    logger.info(
        f"advance_grades task finished: updated={results.get('total_updated', 0)}, "
        f"capped={results.get('total_capped', 0)}, "
        f"orgs_processed={results.get('organizations_processed', 0)}, "
        f"orgs_skipped={results.get('organizations_skipped', 0)}."
    )
    return results
