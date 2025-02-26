import re
import sys
import base64

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from datetime import datetime, timedelta, timezone
from itertools import groupby
from operator import itemgetter
from collections import defaultdict

import pghistory
import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

# from schedule.models.events import EventRelation
from partial_date import PartialDate


class PgHistoryPage:
    object_history_template = 'pghistory_template.html'

    def history_view(self, request, object_id, extra_context=None):
        """
        Adds additional context for the custom history template.
        """
        extra_context = extra_context or {}
        extra_context['object_history'] = (
            pghistory.models.AggregateEvent.objects
                .target(self.model(pk=object_id))
                .order_by('pgh_created_at')
                .select_related('pgh_context')
        )
        return super().history_view(
            request, object_id, extra_context=extra_context
        )


class AttendanceBatchCreateResult(object):
    # class Meta:
    #     pass

    def __init__(self, **kwargs):
        for field in ("number_created", "begin", "end", "meet_slug"):
            setattr(self, field, kwargs.get(field, None))


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
    def pgh_default_sql(history_table_name, table_comment='pgh_obj_id is indexed id/pk', index_on_id=False, original_model_table=''):
        if not original_model_table:
            original_model_table = history_table_name.replace('history', '')

        results = f"""
                ALTER TABLE {history_table_name} ALTER COLUMN pgh_created_at SET DEFAULT CURRENT_TIMESTAMP;
                COMMENT ON TABLE {history_table_name} IS 'History table: {table_comment} of {original_model_table}';
                """
        if index_on_id:
            results += f"""CREATE INDEX idx_{history_table_name}_id ON {history_table_name}(id);"""
        return results

    @staticmethod
    def default_sql(table_name):
        return f"""
                ALTER TABLE {table_name} ALTER COLUMN created SET DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE {table_name} ALTER COLUMN modified SET DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE {table_name} ALTER COLUMN is_removed SET DEFAULT false;
               """

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
    def phone_number_formatter(raw_number_text):
        """
        only format US phone (12 digit) as of now
        """
        if raw_number_text:
            return f'({raw_number_text[2:5]}){raw_number_text[5:8]}-{raw_number_text[8:12]}'
        else:
            return ''

    @staticmethod
    def user_infos():
        return {"settings": {}}

    @staticmethod
    def default_infos():
        return {"fixed": {}, "contacts": {}}

    @staticmethod
    def organization_infos():
        return {
            "acronym": "change me in infos",
            "default_time_zone": settings.CLIENT_DEFAULT_TIME_ZONE,
            "settings": {
                "default_directory_meet": None,
                "default_member_meet": None,
                "default_visitor_meet": None,
                "attendee_to_attending": True,
                "past_category_to_attendingmeet_meet": {},
                "attendingmeet_pdf_export_groups": {},
            },
            "groups_see_all_meets_attendees": [],
            "contacts": {},
            "counselor": [],
            "coworker": [],
            "data_admins": [],
        }

    @staticmethod
    def attendee_infos():
        return {
            "names": {},
            "fixed": {
                "mobility": 2,
            },  # also for food_pref and grade, etc
            "contacts": {},
            "emergency_contacts": {},
            "progressions": {},
            "schedulers": {},
            "updating_attendees": {},
        }

    @staticmethod
    def folk_infos():
        return {
            "print_directory": False,
        }

    @staticmethod
    def meet_infos():
        return {
            'allowed_models': ['gathering', 'attendingmeet', 'attendance', 'eventrelation'],  # suppress believe/baptize meets shows up in attendances, etc.
            'allowed_groups': [],
            'default_attendingmeet_in_weeks': 99999,  # 1886 years, for setting new attendingmeet's finish
            "automatic_creation": {
              "Gathering": True,
              "Attendance": True
            },
            "default_time_zone": settings.CLIENT_DEFAULT_TIME_ZONE,
            "gathering_infos": {},
            "attendance": {},
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
    def add_update_attendee_in_infos(instance, requester_attendee_id):
        if requester_attendee_id:
            infos = instance.infos or Utility.relationship_infos()
            if infos.get('updating_attendees'):
                infos['updating_attendees'][requester_attendee_id] = Utility.now_with_timezone().isoformat()
            else:
                infos['updating_attendees'] = {requester_attendee_id: Utility.now_with_timezone().isoformat()}
            instance.infos = infos
            instance.save()

    @staticmethod
    def forever():  # 1923 years from now
        return datetime.now(timezone.utc) + timedelta(weeks=99999)

    @staticmethod
    def now_with_timezone(delta=timedelta(weeks=0)):
        return datetime.now(timezone.utc) + delta

    @staticmethod
    def today_string(format_string='%Y-%m-%d'):
        return datetime.now(pytz.timezone(settings.CLIENT_DEFAULT_TIME_ZONE)).strftime(format_string)

    @staticmethod
    def is_truthy(value):
        converter = defaultdict(lambda: False)
        converter['1'] = True
        converter[1] = True
        converter['True'] = True
        converter[True] = True
        converter['true'] = True
        return converter[value]

    @staticmethod
    def presence(string, default_when_none=None):
        if not string:
            return default_when_none
        else:
            if isinstance(string, PartialDate):
                return string
            if string.isspace():
                return default_when_none
            else:
                return string.strip()

    @staticmethod
    def reformat_partial_date(
        date_text,
        error_context='',
    ):
        parsed_date = None
        if date_text and isinstance(date_text, str):
            date_text = date_text.strip().strip("'").replace('*', '1').strip("/").replace('//', '/')
            if date_text.count("/") == 2:
                month, day, year = date_text.split('/')
                year = year if len(year) > 3 else (f'20{year}' if int(year) < 23 else f'19{year}')
                try:
                    PartialDate.parseDate(f'{year}-{month}-{day}')
                    parsed_date = f'{year}-{month}-{day}'
                except ValidationError:
                    print("\nCannot parse date for date_text: ", date_text, error_context)
            if date_text.count("/") == 1:
                month, year = date_text.split('/')
                year = year if len(year) > 3 else (f'20{year}' if int(year) < 23 else f'19{year}')
                try:
                    PartialDate.parseDate(f'{year}-{month}')
                    parsed_date = f'{year}-{month}'
                except ValidationError:
                    print("\nCannot parse date for date_text: ", date_text, error_context)
            if date_text.count("/") < 1:
                year = date_text if len(date_text) > 3 else (f'20{date_text}' if int(date_text) < 23 else f'19{date_text}')
                try:
                    PartialDate.parseDate(year)
                    parsed_date = year
                except ValidationError:
                    print("\nCannot parse date for date_text: ", date_text, error_context)
        return parsed_date

    @staticmethod
    def parsedate_or_now(
        date_text,
        default_format="%Y-%m-%d",
        default_timezone=pytz.timezone(settings.CLIENT_DEFAULT_TIME_ZONE),
        default_date=None,
        error_context='',
    ):
        parsed_date = default_date if default_date else Utility.now_with_timezone()
        non_decimal = re.compile(r'[^\d\-/]+')
        if date_text and isinstance(date_text, str):
            if date_text.count("/") == 2 and default_format.count("-") == 2:
                default_format = "%m/%d/%Y"
            try:
                parsing_datetime = datetime.strptime(
                    non_decimal.sub('', date_text.strip().strip("'").strip("/")).replace('//', '/'), default_format
                )
                parsed_date = parsing_datetime.astimezone(default_timezone)
            except:
                print("\nCannot parse date for date_text: ", date_text, error_context)

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
            value = original_value.strip().strip("'").replace('*', '1').replace('//', '/') if strip_first else original_value.replace('//', '/')
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
    def get_object_name(instance, method_name='description', object_field=None):
        instance_field = getattr(instance, method_name, None)
        if instance_field and '#' in instance_field:
            model_name, object_id = instance_field.split("#")
            if model_name:
                model = ContentType.objects.filter(model=model_name).first()
                if model:
                    target = model.model_class().objects.filter(pk=object_id).first()
                    if target:
                        if object_field:
                            return getattr(target, object_field)
                        else:
                            return str(target).strip()
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
        Similar to update_or_create(), it'll search by the filters dictionary, get the last by
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
                    obj.save()
            else:
                filters.update(defaults)
                obj = klass(**filters)
                created = True
                obj.save()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(
                f"\nbug: Sending id instead of instance? Utility.update_or_create_last() exception: {e} at line: {exc_tb.tb_lineno}"
            )
            print(f"and data of {klass} obj#{obj.id} has been saved (pk exist)")
            if excpetion_print_data:
                print(f"with defaults: {defaults} and obj: {obj}")
            # breakpoint()
            if exception_save:
                obj.save()
        return obj, created

    @staticmethod
    def transform_result(data, grouping):
        """
        Todo 20220610: This is grouping AFTER queryset, thus the count of items for each group is incorrect after paging.
        Todo 20220610: To make the count correct when grouping, the count needs to be query and grouped at db level
        """
        if grouping:
            grouping_data = []
            for c_title, items in groupby(data, itemgetter(grouping)):
                grouping_data.append({"key": c_title, "items": list(items)})
            return grouping_data

        else:
            return data

    @staticmethod
    def group_count(group_column, counters):
        group_counts = []
        total_count = 0
        for group in counters:
            group_counts.append({'key': group.get(group_column), 'items': None, 'count': group.get('count')})
            total_count += group.get('count')
        return {'data': group_counts, 'totalCount': total_count}

    @staticmethod
    def base64_file(data, name_with_ext=None):  # https://stackoverflow.com/a/54274739
        _format, _img_str = data.split(';base64,')
        _name, ext_group = _format.split('/')
        if not name_with_ext:
            name = _name.split(":")[-1]
            ext = ext_group.split("+")[0]
            return ContentFile(base64.b64decode(_img_str), name='{}.{}'.format(name, ext))
        else:
            return ContentFile(base64.b64decode(_img_str), name='{}'.format(name_with_ext))

        return ContentFile(base64.b64decode(_img_str), name='{}.{}'.format(name, ext))

    # @property
    # def notes(self):
    #     return Note.objects.filter(
    # #       status=self.status,
    #         link_table=self._meta.db_table,
    #         link_id=self.id
    #     )
