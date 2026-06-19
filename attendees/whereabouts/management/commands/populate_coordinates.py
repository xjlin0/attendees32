import time
import logging
from django.core.management.base import BaseCommand
from address.models import Address
from attendees.whereabouts.services.geocoding_service import GeocodingService

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
        
        # Find all addresses missing coordinates
        # Because GeocodingService updates siblings, we only need to query distinct address combinations.
        # However, for simplicity and to ensure we don't miss any edge cases, we'll iterate through all missing.
        # The service itself protects against redundant API calls if siblings were already updated in a previous iteration.
        missing_coords_addresses = Address.objects.filter(
            latitude__isnull=True
        ) | Address.objects.filter(
            longitude__isnull=True
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
            
            result = GeocodingService.geocode_address(address.id)
            
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
