import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from attendees.users.tests.factories import UserFactory
from attendees.whereabouts.models import Organization

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user_with_org():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    return UserFactory(organization=org)

@pytest.mark.django_db
def test_rosters_list_view_requires_auth(api_client):
    url = reverse("occasions:rosters_list_view")
    response = api_client.get(url)
    assert response.status_code == 302
    assert "login" in response.url

@pytest.mark.django_db
def test_rosters_list_view_success(api_client, user_with_org):
    from attendees.users.models import Menu, MenuAuthGroup
    from django.contrib.auth.models import Group
    
    # Setup authorization for the route
    group = Group.objects.create(name="Test Group")
    user_with_org.groups.add(group)
    menu = Menu.objects.create(
        urn="/occasions/rosters/",
        url_name="rosters_list_view",
        display_name="Rosters",
        display_order=1,
        organization=user_with_org.organization
    )
    MenuAuthGroup.objects.create(
        menu=menu,
        auth_group=group,
        read=True,
        write=True
    )

    api_client.force_login(user_with_org)
    url = reverse("occasions:rosters_list_view")
    response = api_client.get(url)
    assert response.status_code == 200
    
    # Check if the template contains our Vue app div
    content = response.content.decode("utf-8")
    assert 'class="rosters-container"' in content
    assert 'id="app"' in content
    
    # Check context variables (passed via data attributes)
    assert 'data-rosters-endpoint="/occasions/api/organization_meet_rosters/"' in content
