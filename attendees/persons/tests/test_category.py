import pytest
from attendees.persons.models import Category

@pytest.mark.django_db
class TestCategory:
    def test_create_category(self):
        category = Category.objects.create(
            type="event",
            display_order=1,
            display_name="Event Category",
            infos={"icon": "event", "style": "highlight"}
        )
        assert category.id is not None
        assert category.type == "event"
        assert category.display_order == 1
        assert category.display_name == "Event Category"
        assert category.infos == {"icon": "event", "style": "highlight"}

    def test_category_str(self):
        category = Category.objects.create(
            type="location",
            display_order=2,
            display_name="Location Category"
        )
        assert str(category) == "location Location Category"

    def test_category_default_values(self):
        category = Category.objects.create(
            display_name="Default Category"
        )
        assert category.type == "generic"
        assert category.display_order == 0
        assert category.infos == {}

    def test_update_category(self):
        category = Category.objects.create(
            display_name="Old Category"
        )
        category.display_name = "Updated Category"
        category.save()

        updated_category = Category.objects.get(id=category.id)
        assert updated_category.display_name == "Updated Category"

    def test_delete_category(self):
        category = Category.objects.create(
            display_name="Temporary Category"
        )
        category_id = category.id
        category.delete()

        with pytest.raises(Category.DoesNotExist):
            Category.objects.get(id=category_id)
