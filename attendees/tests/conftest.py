"""Session-wide fixtures for the golden congregation and the e2e suite.

The dataset is expensive to build (350 attendees, thousands of participations,
every signal firing), so it is built once per test session and committed.  Each
test then runs inside pytest-django's per-test transaction, so anything a test
writes is rolled back and the next test sees the pristine congregation again.

``pytest.ini`` passes ``--reuse-db``; the session fixture therefore flushes
first, which keeps a reused database from accumulating a second congregation.
"""

import pytest
from django.core.management import call_command
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from attendees.tests.golden import PERSONA_PASSWORD, PERSONAS, build_golden_dataset


@pytest.fixture(scope="session")
def golden(django_db_setup, django_db_blocker):
    """The whole 350-member church, built once and committed.

    Committed, not rolled back, because rebuilding it costs about a minute and
    every e2e test wants the same congregation.  ``pytest_collection_modifyitems``
    in ``attendees/conftest.py`` runs the e2e suite last so this data never
    reaches the unit tests, and the flush on the way out leaves a reused
    database (``pytest.ini`` passes ``--reuse-db``) as clean as it found it.
    """
    with django_db_blocker.unblock():
        call_command("flush", "--noinput", verbosity=0)
        dataset = build_golden_dataset(load_seed=True)
    yield dataset
    with django_db_blocker.unblock():
        call_command("flush", "--noinput", verbosity=0)


@pytest.fixture
def personas():
    return {persona.username: persona for persona in PERSONAS}


@pytest.fixture
def login(golden, db, client):
    """``login("golden_data_organizer")`` -> a Django test client, signed in."""

    def _login(username):
        assert client.login(username=username, password=PERSONA_PASSWORD), (
            f"could not sign in as {username}"
        )
        client.user = golden.user(username)
        return client

    return _login


@pytest.fixture
def api_login(golden, db):
    """``api_login("golden_member")`` -> a DRF ``APIClient``, session-authenticated.

    A real session login, not ``force_authenticate``: several viewsets are
    wrapped in Django's ``login_required``, which runs before DRF ever
    authenticates and would 302 a force-authenticated client to the login page.
    """

    def _api_login(username):
        api_client = APIClient()
        assert api_client.login(username=username, password=PERSONA_PASSWORD), (
            f"could not sign in as {username}"
        )
        api_client.user = golden.user(username)
        return api_client

    return _api_login


@pytest.fixture
def token_client(golden, db):
    """``token_client("golden_member")`` -> a DRF ``APIClient`` authenticated by
    ``Authorization: Token``, the way a server-to-server client calls the API."""

    def _token_client(username):
        user = golden.user(username)
        token, _ = Token.objects.get_or_create(user=user)
        api_client = APIClient()
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        api_client.user = user
        return api_client

    return _token_client


@pytest.fixture
def anonymous_client(golden, db, client):
    return client
