import pytest
from datetime import datetime, timedelta, timezone
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.contenttypes.models import ContentType

from attendees.users.tests.factories import UserFactory
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Category, Relation, Attendee, Registration, Attending, AttendingMeet, Folk, FolkAttendee
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

    organization.infos = {"groups_see_all_meets_attendees": [group.name]}
    organization.save()
    user = UserFactory(organization=organization)
    user.groups.add(group)
    
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
    assert "attendances_count" in data["columns"][0]
    
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


@pytest.mark.django_db
def test_organization_meet_rosters_grouping(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    meet = setup_objects["meet"]

    import json
    group_param = json.dumps([{"selector": "team__display_name", "desc": False}])
    response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "group": group_param,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "rows" in data
    assert len(data["rows"]) == 1
    group_item = data["rows"][0]
    assert group_item["key"] == "Test Team"
    assert "items" in group_item
    assert group_item["items"] is None
    assert group_item["count"] == 1

    # In DevExtreme groupPaging, child rows are loaded remotely via filter
    filter_param = json.dumps([["team__display_name", "=", "Test Team"]])
    child_response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "filter": filter_param,
        },
    )
    assert child_response.status_code == 200
    child_data = child_response.json()
    assert len(child_data["rows"]) == 1
    assert child_data["rows"][0]["attendee_name"] == "John Doe"


@pytest.mark.django_db
def test_organization_meet_rosters_contacts_and_search(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    meet = setup_objects["meet"]
    attendee = setup_objects["attendee"]

    attendee.infos = {"contacts": {"phone1": "+15105559999"}}
    attendee.save()

    # Search by phone number
    response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "searchValue": "5559999",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["attendee_name"] == "John Doe"
    assert "+15105559999" in data["rows"][0]["contacts"]


@pytest.mark.django_db
def test_organization_meet_rosters_grouping_respects_display_order(api_client, setup_objects):
    api_client.force_login(setup_objects["user"])
    url = reverse("occasions:organization_meet_rosters-list")
    meet = setup_objects["meet"]
    assembly = meet.assembly
    site_type = setup_objects["meet"].site_type
    site_id = setup_objects["meet"].site_id

    # Create Team A with display_order 200, Team B with display_order 100
    # Team B (display_order=100) should appear before Team A (display_order=200)
    team_a = Team.objects.create(display_name="Alpha Team", display_order=200, slug="alpha-team", meet=meet, site_type=site_type, site_id=site_id)
    team_b = Team.objects.create(display_name="Beta Team", display_order=100, slug="beta-team", meet=meet, site_type=site_type, site_id=site_id)

    # Attendee 1 in Team A
    attendee_a = Attendee.objects.create(first_name="Alice", last_name="A", gender=0, division=assembly.division)
    attending_a = Attending.objects.create(attendee=attendee_a)
    AttendingMeet.objects.create(
        attending=attending_a,
        meet=meet,
        character=setup_objects["attendance"].character,
        category=setup_objects["category"],
        team=team_a,
        start=datetime.now(timezone.utc),
        finish=datetime.now(timezone.utc) + timedelta(days=1),
    )

    # Attendee 2 in Team B
    attendee_b = Attendee.objects.create(first_name="Bob", last_name="B", gender=0, division=assembly.division)
    attending_b = Attending.objects.create(attendee=attendee_b)
    AttendingMeet.objects.create(
        attending=attending_b,
        meet=meet,
        character=setup_objects["attendance"].character,
        category=setup_objects["category"],
        team=team_b,
        start=datetime.now(timezone.utc),
        finish=datetime.now(timezone.utc) + timedelta(days=1),
    )

    import json
    group_param = json.dumps([{"selector": "team__display_name", "desc": False, "isExpanded": True}])
    response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "group": group_param,
        },
    )
    assert response.status_code == 200
    data = response.json()
    group_keys = [g["key"] for g in data["rows"]]
    # Beta Team (display_order 100) must appear before Alpha Team (display_order 200)
    assert group_keys.index("Beta Team") < group_keys.index("Alpha Team")


@pytest.mark.django_db
def test_organization_meet_rosters_restricted_user_only_sees_family(api_client, setup_objects):
    meet = setup_objects["meet"]
    division = meet.assembly.division
    organization = division.organization
    category = setup_objects["category"]

    # Restricted user with no see_all permission
    restricted_user = UserFactory(organization=organization)
    assert restricted_user.can_see_all_organizational_meets_attendees() is False

    # Parent attendee linked to user
    parent_attendee = Attendee.objects.create(
        first_name="Parent",
        last_name="Smith",
        gender=0,
        division=division,
        user=restricted_user,
    )
    # Child attendee in the same family
    child_attendee = Attendee.objects.create(
        first_name="Child",
        last_name="Smith",
        gender=0,
        division=division,
    )

    family_folk = Folk.objects.create(
        division=division,
        category=category,
        display_name="Smith Family",
    )
    FolkAttendee.objects.create(
        folk=family_folk,
        attendee=parent_attendee,
        role_id=0,
    )
    FolkAttendee.objects.create(
        folk=family_folk,
        attendee=child_attendee,
        role_id=0,
    )

    # Enroll parent and child into the meet
    attending_parent = Attending.objects.create(attendee=parent_attendee)
    AttendingMeet.objects.create(
        attending=attending_parent,
        meet=meet,
        character=setup_objects["attendance"].character,
        category=category,
        start=datetime.now(timezone.utc),
        finish=datetime.now(timezone.utc) + timedelta(days=1),
    )

    attending_child = Attending.objects.create(attendee=child_attendee)
    AttendingMeet.objects.create(
        attending=attending_child,
        meet=meet,
        character=setup_objects["attendance"].character,
        category=category,
        start=datetime.now(timezone.utc),
        finish=datetime.now(timezone.utc) + timedelta(days=1),
    )

    # setup_objects already has "John Doe" (an unrelated attendee) enrolled in the meet
    url = reverse("occasions:organization_meet_rosters-list")
    api_client.force_login(restricted_user)

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
    assert data["totalCount"] == 2
    row_names = [r["attendee_name"] for r in data["rows"]]
    assert "Parent Smith" in row_names
    assert "Child Smith" in row_names
    assert "John Doe" not in row_names

    # Privileged user sees everyone in the meet (John Doe + Parent Smith + Child Smith)
    api_client.force_login(setup_objects["user"])
    response_admin = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
        },
    )
    assert response_admin.status_code == 200
    data_admin = response_admin.json()
    assert data_admin["totalCount"] == 3
    admin_row_names = [r["attendee_name"] for r in data_admin["rows"]]
    assert "John Doe" in admin_row_names
    assert "Parent Smith" in admin_row_names
    assert "Child Smith" in admin_row_names


@pytest.mark.django_db
def test_organization_meet_rosters_restricted_user_without_attendee_sees_empty(api_client, setup_objects):
    meet = setup_objects["meet"]
    organization = meet.assembly.division.organization

    # Restricted user without attendee profile
    unaffiliated_user = UserFactory(organization=organization)
    assert unaffiliated_user.can_see_all_organizational_meets_attendees() is False
    assert not hasattr(unaffiliated_user, "attendee")

    url = reverse("occasions:organization_meet_rosters-list")
    api_client.force_login(unaffiliated_user)

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
    assert data["totalCount"] == 0
    assert data["rows"] == []


@pytest.mark.django_db
def test_organization_meet_rosters_kid_meet_siblings(api_client, setup_objects):
    meet = setup_objects["meet"]
    division = meet.assembly.division
    division.infos = {"show_attendee_infos": {"infos-grade": True}}
    division.save()

    now = datetime.now(timezone.utc)
    category = setup_objects["category"]
    character = setup_objects["attendance"].character
    meet.major_character = character
    meet.save()

    teacher_char = Character.objects.create(display_name="Teacher Leader", slug="teacher-leader", assembly=meet.assembly)

    # Create 3 kids and 1 parent in the same Family Folk
    family_cat, _ = Category.objects.get_or_create(id=Attendee.FAMILY_CATEGORY, defaults={"display_name": "Family", "type": "folk"})
    family_folk = Folk.objects.create(category=family_cat, division=division, display_name="Family Sibling Test")

    parent = Attendee.objects.create(first_name="Parent", last_name="Sim", gender=1, division=division)
    kid1 = Attendee.objects.create(first_name="KidOne", last_name="Sim", gender=1, division=division)
    kid2 = Attendee.objects.create(first_name="KidTwo", last_name="Sim", gender=2, division=division)
    kid3 = Attendee.objects.create(first_name="KidThree", last_name="Sim", gender=1, division=division)

    # Also create a teacher in the meet who has a family
    teacher = Attendee.objects.create(first_name="Teacher", last_name="Sim", gender=1, division=division)

    kid_rel, _ = Relation.objects.get_or_create(id=3, defaults={"title": "son", "relative": True, "display_order": 25, "gender": GenderEnum.UNSPECIFIED.value})
    kid_rel.relative = True
    kid_rel.save()
    parent_rel, _ = Relation.objects.get_or_create(id=1, defaults={"title": "father", "relative": True, "display_order": 20, "gender": GenderEnum.UNSPECIFIED.value})
    parent_rel.relative = True
    parent_rel.save()

    FolkAttendee.objects.create(folk=family_folk, attendee=parent, role=parent_rel, display_order=1)
    FolkAttendee.objects.create(folk=family_folk, attendee=kid1, role=kid_rel, display_order=10)
    FolkAttendee.objects.create(folk=family_folk, attendee=kid2, role=kid_rel, display_order=11)
    FolkAttendee.objects.create(folk=family_folk, attendee=kid3, role=kid_rel, display_order=12)
    FolkAttendee.objects.create(folk=family_folk, attendee=teacher, role=kid_rel, display_order=13)

    # kid1 and kid2 are enrolled in the meet as students (major_character); kid3 is NOT enrolled
    att1 = Attending.objects.create(attendee=kid1)
    AttendingMeet.objects.create(attending=att1, meet=meet, character=character, category=category, start=now - timedelta(days=1), finish=now + timedelta(days=30))

    att2 = Attending.objects.create(attendee=kid2)
    AttendingMeet.objects.create(attending=att2, meet=meet, character=character, category=category, start=now - timedelta(days=1), finish=now + timedelta(days=30))

    att3 = Attending.objects.create(attendee=kid3)

    # teacher is enrolled in the meet as a teacher/leader (non-major character)
    att_teacher = Attending.objects.create(attendee=teacher)
    AttendingMeet.objects.create(attending=att_teacher, meet=meet, character=teacher_char, category=category, start=now - timedelta(days=1), finish=now + timedelta(days=30))

    url = reverse("occasions:organization_meet_rosters-list")
    api_client.force_login(setup_objects["user"])

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
    rows = {r["attendee_name"]: r for r in data["rows"]}

    assert "KidOne Sim" in rows
    assert "KidTwo Sim" in rows
    assert "Teacher Sim" in rows

    kid1_row = rows["KidOne Sim"]
    assert "siblings" in kid1_row
    assert len(kid1_row["siblings"]) == 3

    # kid2 is attending (green), kid3 is not attending (gray), teacher is attending
    sibling_map = {s["name"]: s["attending"] for s in kid1_row["siblings"]}
    assert sibling_map.get("KidTwo Sim") is True
    assert sibling_map.get("KidThree Sim") is False
    assert sibling_map.get("Teacher Sim") is True
    assert "Parent Sim" not in sibling_map  # Parent has display_order < 10, not sibling

    # Non-student participant (Teacher) must NOT show siblings
    teacher_row = rows["Teacher Sim"]
    assert "siblings" in teacher_row
    assert teacher_row["siblings"] == []


@pytest.mark.django_db
def test_organization_meet_rosters_filter_by_contacts_and_search_by_text(api_client, setup_objects):
    import json
    url = reverse("occasions:organization_meet_rosters-list")
    api_client.force_login(setup_objects["user"])
    meet = setup_objects["meet"]

    # Set contact on John Doe
    john = setup_objects["attendee"]
    john.infos = {
        **(john.infos or {}),
        "contacts": {"phone1": "510-555-1234", "email1": "johndoe@example.com"}
    }
    john.save()

    # 1. DevExtreme searchByText sends a compound OR filter including contacts
    filter_expr = [
        ["attendee_name", "contains", "John Doe"],
        "or",
        ["team__display_name", "contains", "John Doe"],
        "or",
        ["character__display_name", "contains", "John Doe"],
        "or",
        ["contacts", "contains", "John Doe"]
    ]

    response = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "filter": json.dumps(filter_expr),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["totalCount"] == 1
    assert data["rows"][0]["attendee_name"] == "John Doe"

    # 2. Searching directly for a contact info (e.g. phone number)
    phone_filter = [["contacts", "contains", "510-555"]]
    response_phone = api_client.get(
        url,
        {
            "meets[]": meet.slug,
            "start": "2020-01-01T00:00:00Z",
            "finish": "2030-12-31T23:59:59Z",
            "filter": json.dumps(phone_filter),
        },
    )
    assert response_phone.status_code == 200
    assert response_phone.json()["totalCount"] == 1






