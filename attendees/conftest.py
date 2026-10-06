import pytest

from attendees.users.models import User
from attendees.users.tests.factories import UserFactory

#: Where the end-to-end suite lives, relative to this file.
E2E_DIRECTORY = "tests/e2e"


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user() -> User:
    return UserFactory()


def pytest_collection_modifyitems(items):
    """Run the end-to-end suite last.

    The e2e tests share one committed 350-person congregation, built once per
    session (see ``attendees/tests/conftest.py``) because rebuilding it per
    test would cost a minute each time.  Committed data is visible to every
    other test in the session, and the unit tests create fixtures with
    hard-coded primary keys that would then collide — so the golden data is
    built after every other test has finished, and flushed on the way out.
    """
    e2e, others = [], []
    for item in items:
        (e2e if E2E_DIRECTORY in str(item.fspath).replace("\\", "/") else others).append(
            item
        )
    items[:] = others + e2e
