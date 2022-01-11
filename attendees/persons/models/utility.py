import re
import sys
from datetime import datetime, timedelta, timezone

import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

# from schedule.models.events import EventRelation


class GatheringBatchCreateResult(object):
    # class Meta:
    #     pass

    def __init__(self, **kwargs):
        for field in ("number_created", "begin", "end", "meet_slug", "duration"):
            setattr(self, field, kwargs.get(field, None))


class Utility:

    # @property
    # def iso_updated_at(self):
    #     return self.updated.isoformat()

    @property
    def all_notes(self):  # return self.notes.all()
        return self.notes.all() if callable(getattr(self, "notes", None)) else []

    @staticmethod
    def present_check(string):
        if string:
            return not string.isspace()
        return False

    @staticmethod
    def blank_check(string):
        if string:
            return string.isspace()
        return True

    @staticmethod
    def user_infos():
        return {"settings": {}}

    @staticmethod
    def default_infos():
        return {"fixed": {}, "contacts": {}}

    @staticmethod
    def organization_infos():
        return {
            "default_time_zone": settings.CLIENT_DEFAULT_TIME_ZONE,
            "settings": {
                "attendee_to_attending": True,
                "past_category_to_attendingmeet_meet": {},
                "attendingmeet_meet_to_past_category": {},
            },
            "groups_see_all_meets_attendees": [],
            "contacts": {},
            "counselor": [],
            "data_admins": [],
        }

    @staticmethod
    def attendee_infos():
        return {
            "names": {},
            "fixed": {},
            "contacts": {},
            "emergency_contacts": {},
            "schedulers": {},
            "updating_attendees": {},
        }

    @staticmethod
    def relationship_infos():
        return {
            "show_secret": {},
            "updating_attendees": {},
            "comment": None,
            "body": None,
        }

    @staticmethod
    def forever():  # 1923 years from now
        return datetime.now(timezone.utc) + timedelta(weeks=99999)

    @staticmethod
    def now_with_timezone(delta=timedelta(weeks=0)):  # 1923 years from now
        return datetime.now(timezone.utc) + delta

    @staticmethod
    def presence(string, default_when_none=None):
        if not string:
            return default_when_none
        else:
            if string.isspace():
                return default_when_none
            else:
                return string.strip()

    @staticmethod
    def parsedate_or_now(
        date_text,
        default_format="%Y-%m-%d",
        default_timezone=pytz.timezone(settings.CLIENT_DEFAULT_TIME_ZONE),
        default_date=None,
    ):
        parsed_date = default_date if default_date else Utility.now_with_timezone()
        if isinstance(date_text, str):
            if date_text.count("/") == 2 and default_format.count("-") == 2:
                default_format = "%m/%d/%Y"
            try:
                parsing_datetime = datetime.strptime(
                    date_text.strip().strip("'"), default_format
                )
                parsed_date = parsing_datetime.astimezone(default_timezone)
            except:
                print("\nCannot parse date for date_text: ", date_text)

        return parsed_date

    @staticmethod
    def boolean_or_datetext_or_original(original_value, strip_first=True):
        boolean_converter = {
            "TRUE": True,
            "FALSE": False,
            "1": True,
            "0": False,
            1: True,
            0: False,
        }

        if isinstance(original_value, str):
            value = original_value.strip().strip("'") if strip_first else original_value
            if value.upper() in boolean_converter:
                return boolean_converter.get(value.upper())
            else:
                try:
                    if value.count("/") == 2:
                        if len(value.split("/")[-1]) > 2:
                            return datetime.strptime(value, "%m/%d/%Y").strftime(
                                "%Y-%m-%d"
                            )
                        else:
                            return datetime.strptime(value, "%m/%d/%y").strftime(
                                "%Y-%m-%d"
                            )
                    else:
                        return value
                except ValueError:
                    return value
        else:
            return original_value

    @staticmethod
    def underscore(
        word,
    ):  # https://inflection.readthedocs.io/en/latest/_modules/inflection.html
        word = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", word)
        word = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", word)
        word = word.replace("-", "_")
        return word.lower()

    @staticmethod
    def get_location(eventrelation):
        model_name, id = eventrelation.distinction.split("#")
        if model_name:
            model = ContentType.objects.filter(model=model_name).first()
            if model:
                target = model.model_class().objects.filter(pk=id).first()
                if object:
                    return str(target)

        return None

    def update_or_create_last(
        klass,
        order_key="pk",
        update=True,
        defaults={},
        filters={},
        exception_save=False,
        excpetion_print_data=False,
    ):
        """
        Sililar to update_or_create(), it'll search by the filters dictionary, get the last by
        order_by, update its values specified by defaults dictionary, return created and obj

        :param order_key: order by condition.
        :param update: boolean: do you want to update the object if any matched?
        :param defaults: new values will be updated to the matched object
        :param filters:
        :param exception_save: resave in the exception block, internally used only for import debug
        :return: tuple of updated/created object, created boolean
        """
        obj = klass.objects.filter(**filters).order_by(order_key).last()
        created = False
        try:
            if obj:
                if update and defaults:
                    for key, value in defaults.items():
                        setattr(obj, key, value)
            else:
                filters.update(defaults)
                obj = klass(**filters)
                created = True
            obj.save()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(
                f"\nKnown bug: Utility.update_or_create_last() exception: {e} at line: {exc_tb.tb_lineno}"
            )
            print(f"and data of {klass} obj#{obj.id} has been saved (pk exist)")
            if excpetion_print_data:
                print(f"with defaults: {defaults} and obj: {obj}")
            # breakpoint()
            if exception_save:
                obj.save()
        return obj, created

    # @property
    # def notes(self):
    #     return Note.objects.filter(
    # #       status=self.status,
    #         link_table=self._meta.db_table,
    #         link_id=self.id
    #     )
