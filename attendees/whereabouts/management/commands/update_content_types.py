from address.models import Address
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from schedule.models.events import EventRelation

from attendees.whereabouts.models import (
    Campus,
    Division,
    Organization,
    Property,
    Room,
    Suite,
)


class Command(BaseCommand):
    help = "Update extra content type columns after migrations and content type data seeded, no arguments needed"

    def handle(self, *args, **options):
        self.stdout.write("checking ContentType data ..")

        if ContentType._meta.db_table not in connection.introspection.table_names():
            raise CommandError(
                f"Fail! Cannot find the table {ContentType._meta.db_table}, did the migration run?"
            )

        if ContentType.objects.count() < 1:
            raise CommandError(
                "ContentType data does not exist! Please try again after 30 sec."
            )

        self.stdout.write("update extra data for ContentType ...")

        cursor = connection.cursor()
        cursor.execute(
            f"""
                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=2,
                      endpoint='/{Room._meta.app_label}/api/organizational_rooms/',
                      hint='single room/office'
                  WHERE app_label='{Room._meta.app_label}'
                    AND model='{Room._meta.model_name}';

                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=3,
                      endpoint='/{Suite._meta.app_label}/api/organizational_suites/',
                      hint='entire floor/space'
                  WHERE app_label='{Suite._meta.app_label}'
                    AND model='{Suite._meta.model_name}';

                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=4,
                      endpoint='/{Property._meta.app_label}/api/organizational_properties/',
                      hint='entire building/villa/lodge'
                  WHERE app_label='{Property._meta.app_label}'
                    AND model='{Property._meta.model_name}';

                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=5,
                      endpoint='/{Campus._meta.app_label}/api/organizational_campuses/',
                      hint='entire campus/park'
                  WHERE app_label='{Campus._meta.app_label}'
                    AND model='{Campus._meta.model_name}';

                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=6,
                      hint='entire division/department',
                      endpoint='/{Division._meta.app_label}/api/user_divisions/'
                  WHERE app_label='{Division._meta.app_label}'
                    AND model='{Division._meta.model_name}';

                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=7,
                      endpoint='/{Organization._meta.app_label}/api/user_organizations/',
                      hint='entire organization'
                  WHERE app_label='{Organization._meta.app_label}'
                    AND model='{Organization._meta.model_name}';

                UPDATE {ContentType._meta.db_table}
                  SET genres='location',
                      display_order=8,
                      hint='street address',
                      endpoint='/{Organization._meta.app_label}/api/all_addresses/'
                  WHERE app_label='{Address._meta.app_label}'
                    AND model='{Address._meta.model_name}';

                COMMENT ON COLUMN {EventRelation._meta.db_table}.distinction
                  IS 'location: <{ContentType._meta.db_table}.model>#<{ContentType._meta.db_table}.id>';
                    """
        )

        self.stdout.write("done!")
