import pytest
from attendees.persons.models import Relation, GenderEnum

@pytest.mark.django_db
class TestRelation:
    def test_create_relation(self):
        relation = Relation.objects.create(
            title="Parent",
            gender=GenderEnum.UNSPECIFIED.value,
            reciprocal_ids=[1, 2],
            display_order=1,
            emergency_contact=True,
            scheduler=False,
            relative=True,
            consanguinity=True
        )
        assert relation.id is not None
        assert relation.title == "Parent"
        assert relation.gender == GenderEnum.UNSPECIFIED.value
        assert relation.reciprocal_ids == [1, 2]
        assert relation.display_order == 1
        assert relation.emergency_contact is True
        assert relation.scheduler is False
        assert relation.relative is True
        assert relation.consanguinity is True

    def test_relation_str(self):
        relation = Relation.objects.create(
            title="Sibling",
            gender=GenderEnum.UNSPECIFIED.value
        )
        assert str(relation) == "Sibling"

    def test_relation_default_values(self):
        relation = Relation.objects.create(
            title="Friend",
            gender=GenderEnum.UNSPECIFIED.value
        )
        # assert relation.gender == GenderEnum.UNSPECIFIED.value
        assert relation.reciprocal_ids == []
        assert relation.display_order == 0
        assert relation.emergency_contact is False
        assert relation.scheduler is False
        assert relation.relative is False
        assert relation.consanguinity is False

    def test_update_relation(self):
        relation = Relation.objects.create(
            title="Colleague",
            gender=GenderEnum.UNSPECIFIED.value
        )
        relation.title = "Coworker"
        relation.save()

        updated_relation = Relation.objects.get(id=relation.id)
        assert updated_relation.title == "Coworker"

    def test_delete_relation(self):
        relation = Relation.objects.create(
            title="Temporary Relation",
            gender=GenderEnum.UNSPECIFIED.value
        )
        relation_id = relation.id
        relation.delete()

        with pytest.raises(Relation.DoesNotExist):
            Relation.objects.get(id=relation_id)
