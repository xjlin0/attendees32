import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from attendees.occasions.models.price import Price
from attendees.occasions.models.assembly import Assembly
from attendees.whereabouts.models import Division, Organization
from attendees.persons.models import Category
from django.contrib.auth.models import Group


@pytest.mark.django_db
class TestPrice:
    def setup_method(self):
        self.group = Group.objects.create(name="Test Group")
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.division = Division.objects.create(display_name="Test Division", slug="test-division", organization=self.organization, audience_auth_group=self.group)
        self.category = Category.objects.create(display_name="Test Category", type="test", display_order=1)
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )


    def test_create_price(self):
        start = datetime.now(timezone.utc)
        finish = start + timedelta(days=1)
        price = Price.objects.create(
            assembly=self.assembly,
            start=start,
            finish=finish,
            display_name="Early Bird",
            price_type="earlybird",
            price_value=Decimal("99.99"),
        )
        assert price.pk is not None
        assert price.assembly == self.assembly
        assert price.display_name == "Early Bird"
        assert price.price_type == "earlybird"
        assert price.price_value == Decimal("99.99")
        assert price.start == start
        assert price.finish == finish

    def test_price_str(self):
        start = datetime(2025, 5, 29, 10, 0, tzinfo=timezone.utc)
        finish = start + timedelta(days=1)
        price = Price.objects.create(
            assembly=self.assembly,
            start=start,
            finish=finish,
            display_name="Standard",
            price_type="standard",
            price_value=Decimal("150.00"),
        )
        s = str(price)
        assert self.assembly.display_name in s
        assert "Standard" in s
        assert "standard" in s
        assert "150.00" in s
