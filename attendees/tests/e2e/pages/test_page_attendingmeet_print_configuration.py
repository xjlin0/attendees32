"""The attendingmeet_print_configuration page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendingmeetPrintConfiguration:
    def test_the_participation_configuration_page_names_the_organization(
        self, golden, login
    ):
        client = login("golden_data_organizer")
        response = client.get("/persons/attendingmeet_print_configuration/")
        assert response.status_code == 200
        assert response.context["pdf_url"] == "/persons/attendingmeet_report/"
