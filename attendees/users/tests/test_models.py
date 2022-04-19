import pytest
from django.apps import apps
from attendees.users.models import User

pytestmark = pytest.mark.django_db


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


def test_model_name_less_than_pgtrigger_limit():
    """
    https://django-pgtrigger.readthedocs.io/en/latest/tutorial.html#overview
    if the model name is greater than 47, trigger name will be none.
    """
    for model in apps.get_models(include_auto_created=True):
        assert len(model._meta.object_name) < 48
