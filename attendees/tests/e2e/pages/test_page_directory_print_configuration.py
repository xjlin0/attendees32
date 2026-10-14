"""The directory_print_configuration page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestDirectoryPrintConfiguration:
    def test_the_directory_configuration_page_lists_divisions(self, golden, login):
        client = login("golden_data_organizer")
        response = client.get("/persons/directory_print_configuration/")
        assert response.status_code == 200
        names = {division["display_name"] for division in response.context["divisions"]}
        assert "中文部" in names and "The Crossing" in names
        assert response.context["organization_direct_meet"] == 8
