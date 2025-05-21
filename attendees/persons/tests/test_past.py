import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from ..models.past import Past
from ..models import Utility
from ..models import Category
from attendees.whereabouts.models import Organization
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestPastModel:

    @pytest.fixture
    def related_objects(self):
        # Create required related objects
        organization = Organization.objects.create(display_name="Test Org")
        category = Category.objects.create(display_name="Test Category", type="test", display_order=1)
        # Use User as a generic subject
        user = get_user_model().objects.create(username="subjectuser")
        content_type = ContentType.objects.get_for_model(user)
        return {
            "organization": organization,
            "category": category,
            "user": user,
            "content_type": content_type,
        }

    def test_create_past_minimal(self, related_objects):
        past = Past.objects.create(
            content_type=related_objects["content_type"],
            object_id=str(related_objects["user"].id),
            category=related_objects["category"],
            organization=related_objects["organization"],
        )
        assert past.pk is not None
        assert past.display_order == 30000
        assert isinstance(past.infos, dict)

    def test_str_method(self, related_objects):
        past = Past.objects.create(
            content_type=related_objects["content_type"],
            object_id=str(related_objects["user"].id),
            category=related_objects["category"],
            organization=related_objects["organization"],
            display_name="Test Display"
        )
        s = str(past)
        assert "Test Display" in s
        assert str(related_objects["category"].id) in s or related_objects["category"].display_name in s

    def test_missing_required_fields(self, related_objects):
        # Missing category
        with pytest.raises(ValidationError):
            past = Past(
                content_type=related_objects["content_type"],
                object_id=str(related_objects["user"].id),
                organization=related_objects["organization"],
            )
            past.full_clean()
        # Missing organization
        with pytest.raises(ValidationError):
            past = Past(
                content_type=related_objects["content_type"],
                object_id=str(related_objects["user"].id),
                category=related_objects["category"],
            )
            past.full_clean()

    def test_infos_default(self, related_objects):
        past = Past.objects.create(
            content_type=related_objects["content_type"],
            object_id=str(related_objects["user"].id),
            category=related_objects["category"],
            organization=related_objects["organization"],
        )
        assert past.infos == Utility.relationship_infos()

    def test_subject_generic_fk(self, related_objects):
        past = Past.objects.create(
            content_type=related_objects["content_type"],
            object_id=str(related_objects["user"].id),
            category=related_objects["category"],
            organization=related_objects["organization"],
        )
        assert past.subject == related_objects["user"]