"""Fixtures shared by the end-to-end suite."""

import importlib
import time

import pytest

#: Modules that did ``from time import sleep`` and so need patching by name.
_SLEEP_IMPORTERS = (
    "attendees.persons.views.page.attendee_update_view",
    "attendees.persons.views.page.attendingmeet_envelopes_list_view",
    "attendees.persons.views.page.attendingmeet_report_list_view",
    "attendees.persons.views.page.datagrid_assembly_all_attendings",
    "attendees.persons.views.page.datagrid_assembly_data_attendings",
    "attendees.persons.views.page.directory_report_list_view",
)


@pytest.fixture(autouse=True)
def no_tarpit(monkeypatch):
    """Skip the two-second penalty the guards impose on a refused request.

    ``RouteGuard``, ``SpyGuard`` and several viewsets sleep for two seconds
    before refusing, to slow down anyone probing the app.  The permission
    matrix below asks for well over a hundred refusals, so the suite would
    spend minutes asleep.  The delay is a rate-limit, not behaviour under test.
    """
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)
    for module_path in _SLEEP_IMPORTERS:
        module = importlib.import_module(module_path)
        monkeypatch.setattr(module, "sleep", lambda *args, **kwargs: None)
