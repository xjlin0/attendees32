import pytest
from django.contrib.auth.models import Group, Permission
from attendees.users.models.user import User
from attendees.whereabouts.models import Organization

pytestmark = pytest.mark.django_db


def test_user_group_membership():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    group = Group.objects.create(name="TestGroup")
    user = User.objects.create_user(username="groupuser", email="groupuser@example.com", password="pass1234", organization=org)
    user.groups.add(group)
    assert user.groups.filter(name="TestGroup").exists()
    assert group in user.groups.all()


def test_user_group_history_created():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    group = Group.objects.create(name="HistoryGroup")
    user = User.objects.create_user(username="historygroupuser", email="historygroupuser@example.com", password="pass1234", organization=org)
    user.groups.add(group)
    UserGroupsHistory = user.groups.through._meta.apps.get_model('users', 'UserGroupsHistory')
    assert UserGroupsHistory.objects.filter(group=group, user=user).exists()
    user.groups.remove(group)
    # After removal, there should be at least two history records (add and remove)
    history_qs = UserGroupsHistory.objects.filter(group=group, user=user).order_by("id")
    assert history_qs.count() >= 2
    # There should be one 'group.add' and one 'group.remove' event label
    labels = list(history_qs.values_list("pgh_label", flat=True))
    assert "group.add" in labels
    assert "group.remove" in labels
    # The user should no longer be in the group
    assert not user.groups.filter(pk=group.pk).exists()


def test_group_permission_history():
    group = Group.objects.create(name="PermGroup")
    perm = Permission.objects.first()
    group.permissions.add(perm)
    GroupPermissionsHistory = group.permissions.through._meta.apps.get_model('users', 'GroupPermissionsHistory')
    assert GroupPermissionsHistory.objects.filter(group=group, permission=perm).exists()
    group.permissions.remove(perm)
    assert GroupPermissionsHistory.objects.filter(group=group, permission=perm).count() >= 2


def test_user_permissions_history():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    user = User.objects.create_user(username="permuser", email="permuser@example.com", password="pass1234", organization=org)
    perm = Permission.objects.first()
    user.user_permissions.add(perm)
    UserPermissionsHistory = user.user_permissions.through._meta.apps.get_model('users', 'UserPermissionsHistory')
    assert UserPermissionsHistory.objects.filter(user=user, permission=perm, pgh_label="user_permission.add").exists()
    user.user_permissions.remove(perm)
    assert UserPermissionsHistory.objects.filter(user=user, permission=perm, pgh_label="user_permission.remove").exists()

