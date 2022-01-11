import os
import ssl
from datetime import datetime

import pytz
from celery.utils.log import get_task_logger
from dateutil.relativedelta import relativedelta
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from attendees.occasions.models import Meet, MessageTemplate
from config import celery_app

from .services.gathering_service import GatheringService

logger = get_task_logger(__name__)


def mail_result(mail_variables):
    """
    A function to email results to a single recipient
    :param mail_variables: dictionary of mail variables
    :return: status code of email such as '204'
    Todo 20210904 tried regenerate certificates, etc but only one work is to disable it by the following openssl
    """
    try:  # https://stackoverflow.com/a/55320969/4257237
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:  # Legacy Python that doesn't verify HTTPS certificates by default
        pass
    else:  # Handle target environment that doesn't support HTTPS verification
        ssl._create_default_https_context = _create_unverified_https_context

    sg = mail_variables["sg"]
    mold = mail_variables["mold"]
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=mail_variables["recipient"],
        subject=mold.templates["subject"].format(**mail_variables),
        html_content=mold.templates["html_content"].format(**mail_variables),
    )
    response = sg.send(message)
    return response.status_code


@celery_app.task()
def batch_create_gatherings(meet_infos):
    """
    A Celery task to periodically generate gatherings.
    :param meet_infos: a list of meet infos including meet_name, meet_slug, month_adding and recipients' emails
    return result dictionary of logs including last processing parameters
    """
    begin = datetime.utcnow().replace(microsecond=0)
    logger.info(
        (f"batch_create_gatherings task ran at {begin.isoformat()}"
         f"(UTC) from {__package__}/occasions/tasks.py with {meet_infos}.")
    )
    no_mold_template = ("Auto generating gatherings for the meet '{meet_name}' from {begin} to {end}({tzname}),"
                        "result: {number_created} gathering(s) created. Info: {explain}. emailing to {recipient},"
                        "email status: {email_status}")
    results = {
        "organization": "unknown",
        "sg": SendGridAPIClient(
            api_key=os.environ.get("SENDGRID_API_KEY")
        ),  # from sendgrid.env
        "success": False,
        "meet_name": "unknown",
        "explain": "unknown",
        "begin": begin,
        "end": begin,
        "tzname": settings.CLIENT_DEFAULT_TIME_ZONE,
        "env_name": settings.ENV_NAME,
        "number_created": 0,
        "time_triggered": begin.astimezone(
            pytz.timezone(settings.CLIENT_DEFAULT_TIME_ZONE)
        ).strftime("%Y-%m-%d %H:%M%p"),
        "email_status": None,
        "email_logs": {},
    }

    for meet_info in meet_infos:
        meet = Meet.objects.filter(slug=meet_info["meet_slug"]).first()
        results["meet_name"] = meet_info["meet_name"]
        if not meet:
            results[
                "explain"
            ] = f"Meet with slug '{meet_info['meet_slug']}' cannot be found or invalid."
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    # results["email_logs"][recipient] = mold.templates[
                    #     "email_log"
                    # ].format(**results)
            return results

        results["meet_name"] = meet.display_name
        results["organization"] = meet.assembly.division.organization
        tzname = (
            meet.infos["default_time_zone"]
            or results["organization"].infos["default_time_zone"]
            or settings.CLIENT_DEFAULT_TIME_ZONE
        )
        time_zone = pytz.timezone(tzname)
        results["tzname"] = tzname
        results["time_triggered"] = begin.astimezone(time_zone).strftime(
            "%Y-%m-%d %H:%M%p"
        )
        mold = MessageTemplate.objects.filter(
            type="batch_create_gatherings", organization=results["organization"]
        ).first()

        if not mold:
            results[
                "explain"
            ] = (f"MessageTemplate with type 'batch_create_gatherings' under Organization"
                             f" '{results['organization']}' cannot be found.")
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = no_mold_template.format(
                        **results
                    )
            return results

        results["mold"] = mold

        if not meet_info["months_adding"]:
            results[
                "explain"
            ] = f"'months_adding' in the PeriodicTask argument JSON cannot be found or invalid."
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = mold.templates[
                        "email_log"
                    ].format(**results)
            return results

        end = datetime.utcnow() + relativedelta(months=+meet_info["months_adding"])
        gathering_results = GatheringService.batch_create(
            begin=begin.isoformat(sep="T", timespec="milliseconds") + "Z",
            end=end.isoformat(sep="T", timespec="milliseconds") + "Z",
            meet_slug=meet_info["meet_slug"],
            duration=0,
            meet=meet,
            user_time_zone=time_zone,
        )

        results["begin"] = gathering_results["begin"]
        results["end"] = gathering_results["end"]
        results["success"] = gathering_results["success"]
        results["number_created"] = gathering_results["number_created"]
        results["explain"] = gathering_results["explain"]

        if meet_info["recipients"] and type(meet_info["recipients"]) is list:
            for recipient in meet_info["recipients"]:
                results["recipient"] = recipient
                results["email_status"] = mail_result(results)
                results["email_logs"][recipient] = mold.templates["email_log"].format(
                    **results
                )

    return results
