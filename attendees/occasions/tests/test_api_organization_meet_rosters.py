import pytest
from datetime import datetime, timedelta, timezone
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.contenttypes.models import ContentType

from attendees.users.tests.factories import UserFactory
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Category, Relation, Attendee, Registration, Attending, AttendingMeet
from attendees.whereabouts.models import Organization, Division
from attendees.occasions.models import Price, Gathering, Character, Team, Meet, Assembly, Attendance
from django.contrib.auth.models import Group

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_objects():
    relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
    organization = Organization.objects.create(display_name="Test Org")
    group = Group.objects.create(name="Test Group")
    division = Division.objects.create(organization=organization, display_name="Test Division", slug="test-division", audience_auth_group=group)
    category = Category.objects.create(id=25, display_name="Test Category", type="test", display_order=1)
    assembly = Assembly.objects.create(display_name="Test Assembly", slug="test-assembly", division=division, category=category)
    
    # We need a site_type, let's use Group for simplicity
    site_type = ContentType.objects.get_for_model(Group)
    meet = Meet.objects.create(display_name="Test Meet", slug="test-meet", assembly=assembly, finish=datetime.now(timezone.utc) + timedelta(days=1), site_type=site_type, site_id=group.id)
    gathering = Gathering.objects.create(display_name="Test Gathering", meet=meet, start=datetime.now(timezone.utc), finish=datetime.now(timezone.utc) + timedelta(hours=2), site_type=site_type, site_id=group.id)
    character = Character.objects.create(display_name="Test Character", assembly=assembly)
    attendee = Attendee.objects.create(first_name="John", last_name="Doe", gender=0, division=division)
    registration = Registration.objects.create(registrant=attendee, assembly=assembly)
    attending = Attending.objects.create(registration=registration, attendee=attendee)
    
    team = Team.objects.create(display_name="Test Team", slug="test-team", meet=meet, site_type=site_type, site_id=group.id)
    attending_meet = AttendingMeet.objects.create(
        attending=attending,
        meet=meet,
        start=datetime.now(timezone.utc),
        finish=datetime.now(timezone.utc) + timedelta(hours=1),
        character=character,
        category=category,
        team=team,
    )
    
    attendance = Attendance.objects.create(
        gathering=gathering,
        attending=attending,
        character=character,
        category=category
    )

    user = UserFactory(organization=organization)
    
    return {
        "user": user,
        "meet": meet,
        "gathering": gathering,
        "attendee": attendee,
        "attending": attending,
        "attendance": attendance,
        "category": category,
    }


@pytest.mark.django_db
def test_organization_meet_rosters_requires_auth(api_client):
    url = reverse("occasions:organization_meet_rosters-list")
    response = api_client.get(url)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_organization_meet_rosters_missing_params(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    response = api_client.get(url)
    assert response.status_code == 400
    assert "error" in response.json()
    assert "meets[], start, and finish are required" in response.json()["error"]


@pytest.mark.django_db
def test_organization_meet_rosters_success(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    
    meet = setup_objects["meet"]
    
    response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "columns" in data
    assert "rows" in data
    assert len(data["columns"]) == 1
    assert data["columns"][0]["id"] == setup_objects["gathering"].id
    
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert row["attendee_name"] == "John Doe"
    assert row["team__display_name"] == "Test Team"
    assert row["total_attendances"] == 1

    gathering_id_str = str(setup_objects["gathering"].id)
    
    # Check that attendances is a list and contains the attendance object
    attendance_record = next((a for a in row["attendances"] if str(a["gathering_id"]) == gathering_id_str), None)
    assert attendance_record is not None
    assert attendance_record["attendance_id"] == setup_objects["attendance"].id
    assert attendance_record["category_id"] == setup_objects["category"].id
    assert attendance_record["category_name"] == "Test Category"


@pytest.mark.django_db
def test_organization_meet_rosters_merges_multiple_attendings(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    meet = setup_objects["meet"]
    attendee = setup_objects["attendee"]
    
    # Create a SECOND attending for the same attendee
    second_attending = Attending.objects.create(attendee=attendee)
    second_am = AttendingMeet.objects.create(
        attending=second_attending,
        meet=meet,
        start=datetime.now(timezone.utc),
        finish=datetime.now(timezone.utc) + timedelta(days=30),
        character=setup_objects["attendance"].character,
        category=setup_objects["category"],
    )
    # Create a second gathering and attendance under the second attending
    second_gathering = Gathering.objects.create(
        display_name="Gathering 2",
        meet=meet,
        start=datetime.now(timezone.utc) + timedelta(days=1),
        finish=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
        site_type=setup_objects["gathering"].site_type,
        site_id=setup_objects["gathering"].site_id,
    )
    second_attendance = Attendance.objects.create(
        gathering=second_gathering,
        attending=second_attending,
        character=setup_objects["attendance"].character,
        category=setup_objects["category"],
    )

    response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # Key check: Even though there are 2 attendings, there should be exactly 1 row for the person!
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert row["attendee_id"] == str(attendee.id)
    assert row["attendee_name"] == "John Doe"
    # Attendances from both attendings are merged!
    assert row["total_attendances"] == 2
    assert len(row["attendances"]) == 2
    assert len(row["attendingmeets"]) == 2


@pytest.mark.django_db
def test_organization_meet_rosters_search(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    meet = setup_objects["meet"]

    # Match by name
    res_match = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "searchValue": "John",
        },
    )
    assert res_match.status_code == 200
    assert len(res_match.json()["rows"]) == 1

    # Non-matching search
    res_no_match = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "searchValue": "NobodyHere",
        },
    )
    assert res_no_match.status_code == 200
    assert len(res_no_match.json()["rows"]) == 0

