import time
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from address.models import Address
from attendees.whereabouts.models import Place
from attendees.whereabouts.services.coordinates_service import CoordinatesService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Populate missing latitude and longitude for Address records using Google Maps API."

    def add_arguments(self, parser):
        parser.add_argument(
            '--sleep',
            type=float,
            default=0.2,
            help='Time to sleep between API calls in seconds (default: 0.2 to respect rate limits)'
        )

    def handle(self, *args, **options):
        sleep_time = options['sleep']

        # Clean up unused Address records first
        used_address_ids = Place.all_objects.values_list('address_id', flat=True).distinct()
        unused_addresses = Address.objects.exclude(id__in=used_address_ids)

        # Django's delete() returns a tuple (total_deleted, dict_of_deleted_models)
        deleted_count, deleted_details = unused_addresses.delete()
        if deleted_count > 0:
            self.stdout.write(self.style.WARNING(f"Cleaned up {deleted_count} unused Address records."))

        # Find all addresses missing coordinates and having both street_number and route
        # Because CoordinatesService updates siblings, we only need to query distinct address combinations.
        # The service itself protects against redundant API calls if siblings were already updated in a previous iteration.
        missing_coords_addresses = (
            Address.objects.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
            .exclude(Q(street_number__isnull=True) | Q(street_number=''))
            .exclude(Q(route__isnull=True) | Q(route=''))
        )

        # Optimize by getting only distinct combinations of street_number, route, locality
        # to feed into the service, minimizing the loop size.
        distinct_addresses = missing_coords_addresses.order_by(
            'street_number', 'route', 'locality_id'
        ).distinct(
            'street_number', 'route', 'locality_id'
        )

        total_to_process = distinct_addresses.count()
        self.stdout.write(self.style.WARNING(f"Found {total_to_process} distinct addresses missing coordinates."))

        if total_to_process == 0:
            self.stdout.write(self.style.SUCCESS("All addresses have coordinates. Exiting."))
            return

        success_count = 0
        failure_count = 0

        for index, address in enumerate(distinct_addresses, start=1):
            self.stdout.write(f"Processing {index}/{total_to_process}: Address ID {address.id}...")

            result = CoordinatesService.geocode_address(address.id)

            if result:
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f"  -> Success"))
            else:
                failure_count += 1
                self.stdout.write(self.style.ERROR(f"  -> Failed or Skipped"))

            # Sleep to respect rate limits
            time.sleep(sleep_time)

        self.stdout.write(self.style.SUCCESS(
            f"Finished. Successfully geocoded {success_count} address groups. Failed/Skipped: {failure_count}."
        ))
