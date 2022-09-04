from datetime import datetime

import pghistory
import pytz
from celery.utils.log import get_task_logger
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import send_mail

from attendees.occasions.models import Meet, MessageTemplate
from attendees.occasions.services import AttendanceService
from config import celery_app

from .services.gathering_service import GatheringService

logger = get_task_logger(__name__)


def mail_result(mail_variables):
    """
    A function to email results to a single recipient
    :param mail_variables: dictionary of mail variables
    :return: text saying number of email triggered such as 1 or 0
    """
    mold = MessageTemplate.objects.get(pk=mail_variables["message_template_id"])
    emails_triggered = send_mail(
        subject=mold.templates["subject"].format(**mail_variables),
        message="nobody see pure text",
        from_email=None,   # use the EMAIL_HOST_USER setting when None
        recipient_list=[mail_variables["recipient"]],
        html_message=mold.templates["html_content"].format(**mail_variables),
    )
    return f'{emails_triggered} email(s) triggered.'


@celery_app.task()
@pghistory.context(modifier='batch create gatherings')
def batch_create_gatherings(meet_infos):
    """
    A Celery task to periodically generate gatherings taking arguments from model of "periodic task"
    :param meet_infos: a list of meet infos including meet_name, meet_slug, month_adding & recipients' emails, example:

                    {
                        "meet_infos": [
                          {
                            "desc": "Valid JSON with single key 'meet_infos' is required",
                            "meet_name": "The Rock",
                            "meet_slug": "d7c8Fd_cfcch_junior_regular_the_rock",
                            "months_adding": 1,
                            "recipients": ["to@email.com"]
                          }
                        ]
                    }

    Todo 20220202: use signal for mailing status https://anymail.dev/en/stable/sending/signals/
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
            results["explain"] = f"Meet with slug '{meet_info['meet_slug']}' cannot be found or invalid."
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = message_template.templates["email_log"].format(**results)
            return results

        results["meet_name"] = meet.display_name
        results["organization"] = meet.assembly.division.organization.display_name
        tzname = (
            meet.infos["default_time_zone"]
            or meet.assembly.division.organization.infos["default_time_zone"]
            or settings.CLIENT_DEFAULT_TIME_ZONE
        )
        time_zone = pytz.timezone(tzname)
        results["tzname"] = tzname
        results["time_triggered"] = begin.astimezone(time_zone).strftime(
            "%Y-%m-%d %H:%M%p"
        )
        message_template = MessageTemplate.objects.filter(
            type="batch_create_gatherings", organization=meet.assembly.division.organization
        ).first()

        if not message_template:
            results[
                "explain"
            ] = (f"MessageTemplate with type 'batch_create_gatherings' under Organization"
                             f" '{results['organization']}' cannot be found.")
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = no_mold_template.format(**results)
            return results

        results["message_template_id"] = message_template.id

        if not meet_info["months_adding"]:
            results[
                "explain"
            ] = f"'months_adding' in the PeriodicTask argument JSON cannot be found or invalid."
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = message_template.templates["email_log"].format(**results)
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
                results["email_logs"][recipient] = message_template.templates["email_log"].format(**results)

    return results


@celery_app.task()
@pghistory.context(modifier='batch create attendances')
def batch_create_attendances(meet_infos):
    """
    A Celery task to periodically generate attendances taking arguments from model of "periodic task"
    :param meet_infos: a list of meet infos including meet_name, meet_slug, month_adding & recipients' emails, example:

                    {
                        "meet_infos": [
                          {
                            "desc": "Valid JSON with single key 'meet_infos' is required",
                            "meet_name": "The Rock",
                            "meet_slug": "d7c8Fd_cfcch_junior_regular_the_rock",
                            "months_adding": 1,
                            "recipients": ["to@email.com"]
                          }
                        ]
                    }

    Note: it does NOT auto create gatherings!
    Todo 20220202: use signal for mailing status https://anymail.dev/en/stable/sending/signals/
    return result dictionary of logs including last processing parameters
    """
    begin = datetime.utcnow().replace(microsecond=0)
    logger.info(
        (f"batch_create_attendances task ran at {begin.isoformat()}"
         f"(UTC) from {__package__}/occasions/tasks.py with {meet_infos}.")
    )
    no_mold_template = ("Auto generating attendances for the meet '{meet_name}' from {begin} to {end}({tzname}),"
                        "result: {number_created} attendance(s) created. Info: {explain}. emailing to {recipient},"
                        "email status: {email_status}")
    results = {
        "organization": "unknown",
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
            results["explain"] = f"Meet with slug '{meet_info['meet_slug']}' cannot be found or invalid."
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = message_template.templates["email_log"].format(**results)
            return results

        results["meet_name"] = meet.display_name
        results["organization"] = meet.assembly.division.organization.display_name
        tzname = (
            meet.infos["default_time_zone"]
            or meet.assembly.division.organization.infos["default_time_zone"]
            or settings.CLIENT_DEFAULT_TIME_ZONE
        )
        time_zone = pytz.timezone(tzname)
        results["tzname"] = tzname
        results["time_triggered"] = begin.astimezone(time_zone).strftime(
            "%Y-%m-%d %H:%M%p"
        )
        message_template = MessageTemplate.objects.filter(
            type="batch_create_attendances", organization=meet.assembly.division.organization
        ).first()

        if not message_template:
            results[
                "explain"
            ] = (f"MessageTemplate with type 'batch_create_attendances' under Organization"
                             f" '{results['organization']}' cannot be found.")
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = no_mold_template.format(**results)
            return results

        results["message_template_id"] = message_template.id

        if not meet_info["months_adding"]:
            results[
                "explain"
            ] = f"'months_adding' in the PeriodicTask argument JSON cannot be found or invalid."
            if meet_info["recipients"] and type(meet_info["recipients"]) is list:
                for recipient in meet_info["recipients"]:
                    results["recipient"] = recipient
                    results["email_status"][recipient] = mail_result(results)
                    results["email_logs"][recipient] = message_template.templates["email_log"].format(**results)
            return results

        end = datetime.utcnow() + relativedelta(months=+meet_info["months_adding"])
        attendance_results = AttendanceService.batch_create(
            begin=begin.isoformat(sep="T", timespec="milliseconds") + "Z",
            end=end.isoformat(sep="T", timespec="milliseconds") + "Z",
            meet_slug=meet_info["meet_slug"],
            meet=meet,
            user_time_zone=time_zone,
        )

        results["begin"] = attendance_results["begin"]
        results["end"] = attendance_results["end"]
        results["success"] = attendance_results["success"]
        results["number_created"] = attendance_results["attendance_created"]
        results["explain"] = attendance_results["explain"]

        if meet_info["recipients"] and type(meet_info["recipients"]) is list:
            for recipient in meet_info["recipients"]:
                results["recipient"] = recipient
                results["email_status"] = mail_result(results)
                results["email_logs"][recipient] = message_template.templates["email_log"].format(**results)

    return results
