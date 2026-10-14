"""Golden test data for attendees32: a 350-member Chinese church, in full.

``fixtures/db_seed.json`` supplies the vocabulary — organization, divisions,
categories, relations, assemblies, meets, characters, teams, menus and auth
groups.  This package supplies the congregation that lives inside it:

* 200 first-generation Chinese immigrants (中文部)
* 100 English-congregation adults (The Crossing)
*  25 youth in the English congregation, grades 6-12
*  25 children in Junior Ministry, nursery through grade 5
*  10 of the Chinese adults who also sit in the English service
* plus a soft-deleted household that must never surface in a live query

Use it from a test::

    def test_something(golden):
        grace = golden.attendee("chen_grace")

or from a shell::

    python manage.py load_golden_data
"""

from .builder import (  # noqa: F401
    GoldenBuilder,
    GoldenDataset,
    PERSONA_PASSWORD,
    PERSONAS,
    Persona,
    build_golden_dataset,
    golden_uuid,
)
from .roster import Roster, build_roster  # noqa: F401

__all__ = [
    "GoldenBuilder",
    "GoldenDataset",
    "PERSONAS",
    "PERSONA_PASSWORD",
    "Persona",
    "Roster",
    "build_golden_dataset",
    "build_roster",
    "golden_uuid",
]
