import pytest
from unittest.mock import Mock
from django.contrib.auth.models import Group
from attendees.whereabouts.models import Organization
from attendees.users.models import Menu, MenuAuthGroup, User
from attendees.users.services.menu_service import MenuService

@pytest.mark.django_db
class TestMenuService:
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
            url_name="test_url_name",
            display_name="Test Menu",
            display_order=1,
        )
        self.user = User.objects.create(username="testuser")
        self.user.groups.add(self.group)

        # Mock request
        self.request = Mock()
        self.request.user = self.user
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = "test_url_name"

    def test_is_user_allowed_to_write_true(self):
        # Grant write access
        MenuAuthGroup.objects.create(
            auth_group=self.group,
            menu=self.menu,
            read=True,
            write=True
        )

        assert MenuService.is_user_allowed_to_write(self.request) is True

    def test_is_user_allowed_to_write_false_no_write_permission(self):
        # Grant read-only access
        MenuAuthGroup.objects.create(
            auth_group=self.group,
            menu=self.menu,
            read=True,
            write=False
        )

        assert MenuService.is_user_allowed_to_write(self.request) is False

    def test_is_user_allowed_to_write_false_wrong_url_name(self):
        # Grant write access
        MenuAuthGroup.objects.create(
            auth_group=self.group,
            menu=self.menu,
            read=True,
            write=True
        )

        # Change request url_name to something else
        self.request.resolver_match.url_name = "other_url_name"

        assert MenuService.is_user_allowed_to_write(self.request) is False

    def test_is_user_allowed_to_write_false_menu_removed(self):
        # Grant write access
        MenuAuthGroup.objects.create(
            auth_group=self.group,
            menu=self.menu,
            read=True,
            write=True
        )
        
        # Soft delete the menu
        self.menu.is_removed = True
        self.menu.save()

        assert MenuService.is_user_allowed_to_write(self.request) is False
