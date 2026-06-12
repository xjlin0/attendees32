import pytest
from django.contrib.auth.models import Group
from django.db.utils import IntegrityError
from attendees.whereabouts.models import Organization
from attendees.users.models import Menu, MenuAuthGroup

@pytest.mark.django_db
class TestMenuAuthGroup:
    def setup_method(self):
        self.organization = Organization.objects.create(
            display_name="Test Organization",
            slug="test-org"
        )
        self.group = Group.objects.create(name="Test Group")
        self.menu = Menu.objects.create(
            organization=self.organization,
            category="main",
            html_type="a",
            urn="/app/test/",
            url_name="test_view",
            display_name="Test Menu",
            display_order=1,
            infos={"class": "nav-link"}
        )
        self.menu_auth_group = MenuAuthGroup.objects.create(
            auth_group=self.group,
            menu=self.menu,
            read=True,
            write=False
        )

    def test_create_menu_auth_group(self):
        assert self.menu_auth_group.pk is not None
        assert self.menu_auth_group.auth_group == self.group
        assert self.menu_auth_group.menu == self.menu
        assert self.menu_auth_group.read is True
        assert self.menu_auth_group.write is False

    def test_unique_constraint(self):
        # Trying to create another MenuAuthGroup with same group and menu should fail
        with pytest.raises(IntegrityError):
            MenuAuthGroup.objects.create(
                auth_group=self.group,
                menu=self.menu,
                read=True,
                write=True
            )
