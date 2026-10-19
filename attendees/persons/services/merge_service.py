"""Merging one attendee into another, and undoing it.

The duplicate is soft-deleted and keeps a forwarding address; what it held
moves to the primary. The primary's own details stay, the duplicate's fill
its blanks, and contacts of every kind are kept from both. What moved, and
what all of the primary's details were, is written on the tombstone
(``infos["merge"]``), so ``unmerge`` can put it all back once. Merging B into
C also re-points everything already merged into B, so a chain only exists in
hand-edited data and walking one is a bounded guard. ``preview`` shows what a
merge would do, for the merge screen.
"""

import uuid
from datetime import date, datetime, timezone

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.fields.files import FieldFile
from partial_date import PartialDate

from attendees.occasions.models import Attendance
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    FolkAttendee,
    Note,
    Past,
    Registration,
    Utility,
)
from attendees.whereabouts.models import Place

#: Bounds the walk over hand-edited data; a cycle answers "gone".
MAX_MERGE_HOPS = 5

#: ``Attendee.infos`` sections keyed by other attendees' ids.
REFERENCE_KEYS = ("schedulers", "emergency_contacts")

#: An attendee's own single-value details: these columns, and every key of
#: ``infos["fixed"]`` as ``fixed.<key>``. Contacts are handled by kind below.
COLUMNS = (
    "first_name",
    "last_name",
    "first_name2",
    "last_name2",
    "gender",
    "actual_birthday",
    "estimated_birthday",
    "deathday",
    "photo",
    "division",
)
ATTRIBUTES = {"division": "division_id"}


class MergeRefused(Exception):
    """A merge or unmerge that must not happen, with the reason."""


def _attendee_type():
    return ContentType.objects.get_for_model(Attendee)


def _repoint_or_retire(row, field, target, clash, moved, retired):
    if clash:
        row.is_removed = True
        row.save(update_fields=["is_removed"])
        retired.append(row.pk)
    else:
        setattr(row, field, target)
        row.save(update_fields=[field])
        moved.append(row.pk)


def _plain(value):
    # JSON-safe, so a value can be written on the tombstone and compared.
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, (date, PartialDate)):
        return str(value)
    return value


def _blank(value):
    # An unspecified gender is a blank, not a value to keep.
    return value in (None, "") or str(value).upper().endswith("UNSPECIFIED")


def _kind(key):
    # A contact key is a kind and a number: phone1, email2, wechat1. The form
    # lets people type any key, so the kind is whatever is left without the
    # trailing digits, and case does not count.
    return key.lower().rstrip("0123456789") or key.lower()


def _details(attendee):
    """``{name: value}`` of the attendee's own single-value details, blanks left out."""
    details = {}
    for column in COLUMNS:
        value = _plain(getattr(attendee, ATTRIBUTES.get(column, column)))
        if not _blank(value):
            details[column] = value
    for key, value in (attendee.infos.get("fixed") or {}).items():
        if not _blank(value):
            details[f"fixed.{key}"] = value
    return details


def _contacts(attendee):
    """``{kind: [values]}`` of the attendee's contacts, in key order, blanks left out."""
    contacts = attendee.infos.get("contacts") or {}
    by_kind = {}
    for key in sorted(contacts):
        if not _blank(contacts[key]):
            by_kind.setdefault(_kind(key), []).append(contacts[key])
    return by_kind


def _uuid(value):
    # An id from a URL or a query string: a UUID or nothing, never an error.
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _named(attendee):
    names = attendee.infos.get("names") or {}
    name = names.get("original") or f"{attendee.first_name} {attendee.last_name}".strip()
    return {"id": str(attendee.pk), "name": name, "created": attendee.created.isoformat()}


def _merged_contacts(primary, duplicate):
    """``{key: (value, "primary" | "duplicate")}`` the merge writes: per kind,
    the primary's values then the duplicate's new ones, as kind1, kind2, ..."""
    merged = {}
    for who, attendee in (("primary", primary), ("duplicate", duplicate)):
        for kind, values in _contacts(attendee).items():
            held = merged.setdefault(kind, [])
            held += [(value, who) for value in values if value not in [v for v, _ in held]]
    return {
        f"{kind}{number}": entry
        for kind, entries in merged.items()
        for number, entry in enumerate(entries, start=1)
    }


def _set_detail(attendee, name, value):
    section, _, key = name.partition(".")
    if key:
        attendee.infos.setdefault(section, {})[key] = value
    else:
        setattr(attendee, ATTRIBUTES.get(name, name), value)


class AttendeeMergeService:
    @staticmethod
    def primary_of(attendee):
        """The attendee itself, the terminal primary, or ``None`` when the
        trail ends nowhere (primary deleted, or a cycle)."""
        seen = {attendee.pk}
        current = attendee

        for _ in range(MAX_MERGE_HOPS):
            if current.merged_into_id is None:
                return current
            if current.merged_into_id in seen:
                return None
            seen.add(current.merged_into_id)
            # all_objects: tombstones are soft-deleted.
            current = Attendee.all_objects.filter(pk=current.merged_into_id).first()
            if current is None:
                return None

        return None

    @staticmethod
    def resolve(attendee_id):
        """``(attendee, was_merged)`` for an id; ``attendee`` is ``None`` for
        an unknown id or a trail that ends nowhere."""
        held = Attendee.all_objects.filter(pk=attendee_id).first()
        if held is None:
            return None, False
        if held.merged_into_id is None:
            return (None, False) if held.is_removed else (held, False)

        primary = AttendeeMergeService.primary_of(held)
        if primary is None or primary.is_removed:
            return None, True
        return primary, True

    @staticmethod
    @transaction.atomic
    def merge(duplicate, primary, by=None):
        """Merges ``duplicate`` into ``primary`` and returns the primary.

        The primary's own details stay, the duplicate's fill its blanks, and
        contacts of every kind are kept from both. Anything else the merged
        record should carry is an ordinary edit afterwards; ``unmerge`` puts
        the primary's details back as they were either way.

        Refused: into itself, across organizations, into a record that is
        deleted or itself merged away, when the duplicate is already merged,
        or when both have a login. ``by`` names who did it, for the record.
        """
        given = (duplicate, primary)
        duplicate, primary = AttendeeMergeService._locked(duplicate, primary)
        AttendeeMergeService._refuse_unless_mergeable(duplicate, primary)

        was_removed = duplicate.is_removed
        # The primary is saved here, before anything below re-reads its row.
        moved = {
            "details": AttendeeMergeService._merge_details(duplicate, primary),
            "own_references": AttendeeMergeService._merge_own_references(duplicate, primary),
            "attendings": AttendeeMergeService._fold_attendings(duplicate, primary),
            "memberships": AttendeeMergeService._move_memberships(duplicate, primary),
            "pasts": AttendeeMergeService._move_linked(Past, duplicate, primary),
            "notes": AttendeeMergeService._move_linked(Note, duplicate, primary),
            "places": AttendeeMergeService._move_places(duplicate, primary),
            "registrations": AttendeeMergeService._move_registrations(duplicate, primary),
            "user": AttendeeMergeService._move_login(duplicate, primary),
            "references": AttendeeMergeService._rekey_references(duplicate, primary),
            "tombstones": AttendeeMergeService._repoint_tombstones(duplicate, primary),
        }

        duplicate.infos["merge"] = {
            "into": str(primary.pk),
            "at": Utility.now_with_timezone().isoformat(timespec="seconds"),
            "by": by,
            "was_removed": was_removed,
            "moved": moved,
        }
        duplicate.merged_into = primary
        duplicate.is_removed = True
        duplicate.save(update_fields=["infos", "merged_into", "is_removed"])
        AttendeeMergeService._refresh(given, (duplicate, primary))
        return primary

    @staticmethod
    def _refuse_unless_mergeable(duplicate, primary):
        if duplicate.pk == primary.pk:
            raise MergeRefused("An attendee cannot be merged into themselves.")
        if duplicate.division.organization_id != primary.division.organization_id:
            raise MergeRefused(
                "Those two attendees belong to different organizations, so one "
                "cannot absorb the other."
            )
        if primary.merged_into_id is not None:
            raise MergeRefused(
                "That primary has itself been merged away. Merge into whoever "
                "holds the record now."
            )
        if primary.is_removed:
            raise MergeRefused("That primary is deleted.")
        if duplicate.merged_into_id is not None:
            raise MergeRefused("That attendee has already been merged.")
        if duplicate.user_id and primary.user_id:
            raise MergeRefused("Both attendees have a login; remove one first.")

    @staticmethod
    def preview(one, other):
        """What merging two records would do, without doing it.

        The older record is the primary and keeps its id. Returns both records,
        every single-value detail either has with both values, the contacts the
        merge would write and where each came from, and counts of what moves.
        Refused as ``merge`` would be.
        """
        primary, duplicate = sorted((one, other), key=lambda a: (a.created, str(a.pk)))
        AttendeeMergeService._refuse_unless_mergeable(duplicate, primary)
        theirs, mine = _details(primary), _details(duplicate)
        return {
            "primary": _named(primary),
            "duplicate": _named(duplicate),
            "details": {
                name: {"primary": theirs.get(name), "duplicate": mine.get(name)}
                for name in sorted(set(theirs) | set(mine))
            },
            "contacts": {
                key: {"value": value, "from": who}
                for key, (value, who) in _merged_contacts(primary, duplicate).items()
            },
            "moves": AttendeeMergeService._counts(duplicate),
        }

    @staticmethod
    def _counts(duplicate):
        """How many rows of each kind the merge would move from the duplicate."""
        linked = {"content_type": _attendee_type(), "object_id": str(duplicate.pk)}
        return {
            "enrollments": AttendingMeet.objects.filter(
                attending__attendee=duplicate, attending__is_removed=False
            ).count(),
            "attendances": Attendance.objects.filter(
                attending__attendee=duplicate, attending__is_removed=False
            ).count(),
            "memberships": FolkAttendee.objects.filter(attendee=duplicate)
            .exclude(role_id=Attendee.HIDDEN_ROLE)
            .count(),
            "addresses": Place.objects.filter(**linked).count(),
            "notes": Note.objects.filter(**linked).count(),
            "statuses": Past.objects.filter(**linked).count(),
            "registrations": Registration.objects.filter(registrant=duplicate).count(),
        }

    @staticmethod
    def merged_away(attendee_id):
        """The tombstone of a merged-away record, or ``None``."""
        return Attendee.all_objects.filter(
            pk=_uuid(attendee_id), is_removed=True, merged_into__isnull=False
        ).first()

    @staticmethod
    def merged_from(attendee_id):
        """The records merged into this one, newest first: id, name, when, by whom."""
        records = []
        for tombstone in Attendee.all_objects.filter(
            merged_into_id=_uuid(attendee_id), is_removed=True
        ):
            merge = tombstone.infos.get("merge") or {}
            by = Attendee.all_objects.filter(pk=_uuid(merge.get("by"))).first()
            records.append(
                {
                    "id": str(tombstone.pk),
                    "name": _named(tombstone)["name"],
                    "at": datetime.fromisoformat(merge["at"]) if merge.get("at") else None,
                    "by": _named(by)["name"] if by else None,
                }
            )
        return sorted(records, key=lambda record: record["at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    @staticmethod
    @transaction.atomic
    def unmerge(duplicate):
        """Puts back what the merge moved and revives the duplicate, once.

        The primary's own details go back to what they were before the merge,
        edits made since included. Rows the primary gained since stay with it.
        A login that moved and has changed hands since is refused rather than
        guessed.
        """
        given = (duplicate,)
        duplicate = Attendee.all_objects.select_for_update().get(pk=duplicate.pk)
        if duplicate.merged_into_id is None:
            raise MergeRefused("That attendee was not merged.")
        record = duplicate.infos.get("merge")
        if not record:
            raise MergeRefused(
                "There is no record of what the merge moved, so it cannot be undone."
            )
        moved = record["moved"]
        primary = (
            Attendee.all_objects.select_for_update().filter(pk=record["into"]).first()
        )

        if moved["user"] is not None:
            if primary is None or primary.user_id != moved["user"]:
                raise MergeRefused(
                    "The login that moved has changed since; move it back by hand first."
                )
            primary.user = None
            primary.save(update_fields=["user"])
            duplicate.user_id = moved["user"]

        if primary is not None:
            AttendeeMergeService._restore_details(primary, moved.get("details") or {})
            AttendeeMergeService._restore_own_references(primary, moved.get("own_references") or {})
            primary.save()
        AttendeeMergeService._restore_references(duplicate, record)
        Registration.all_objects.filter(pk__in=moved["registrations"]).update(
            registrant=duplicate
        )
        mine = str(duplicate.pk)
        Past.all_objects.filter(pk__in=moved["pasts"]).update(object_id=mine)
        Note.all_objects.filter(pk__in=moved["notes"]).update(object_id=mine)
        Place.all_objects.filter(pk__in=moved["places"]["moved"]).update(object_id=mine)
        Place.all_objects.filter(pk__in=moved["places"]["retired"]).update(is_removed=False)

        memberships = moved["memberships"]
        FolkAttendee.all_objects.filter(pk__in=memberships["moved"]).update(attendee=duplicate)
        FolkAttendee.all_objects.filter(pk__in=memberships["retired"]).update(is_removed=False)

        attendings = moved["attendings"]
        Attending.all_objects.filter(pk__in=attendings["moved"]).update(attendee=duplicate)
        for fold in attendings["folded"]:
            AttendingMeet.all_objects.filter(pk__in=fold["enrollments"]).update(
                attending_id=fold["attending"]
            )
            AttendingMeet.all_objects.filter(pk__in=fold["enrollments_retired"]).update(
                is_removed=False
            )
            Attendance.all_objects.filter(pk__in=fold["attendances"]).update(
                attending_id=fold["attending"]
            )
            Attendance.all_objects.filter(pk__in=fold["attendances_retired"]).update(
                is_removed=False
            )
            Attending.all_objects.filter(pk=fold["attending"]).update(is_removed=False)

        Attendee.all_objects.filter(pk__in=moved["tombstones"]).update(merged_into=duplicate)

        duplicate.infos.pop("merge")
        duplicate.infos.setdefault("unmerged", []).append(
            {**record, "undone_at": Utility.now_with_timezone().isoformat(timespec="seconds")}
        )
        duplicate.merged_into = None
        duplicate.is_removed = record.get("was_removed", False)
        duplicate.save(update_fields=["infos", "merged_into", "is_removed", "user"])
        AttendeeMergeService._refresh(given, (duplicate,))
        return duplicate

    @staticmethod
    def _refresh(given, fresh):
        # The caller's instances were not the locked ones; let them see the result.
        for stale, current in zip(given, fresh):
            if stale is not current:
                stale.refresh_from_db()

    @staticmethod
    def _locked(duplicate, primary):
        # Both rows locked in pk order, so two coworkers merging the same
        # pair in opposite directions queue up instead of making a cycle.
        rows = {
            row.pk: row
            for row in Attendee.all_objects.select_for_update()
            .filter(pk__in=[duplicate.pk, primary.pk])
            .order_by("pk")
        }
        try:
            return rows[duplicate.pk], rows[primary.pk]
        except KeyError:
            raise MergeRefused("That attendee no longer exists.")

    @staticmethod
    def _merge_details(duplicate, primary):
        """Writes the merged record's own details on the primary and returns
        what all of them were, for ``unmerge``.

        A detail keeps the primary's value; the duplicate's fills a blank.
        Contacts are kept from both: per kind, the primary's values then the
        duplicate's new ones, written as kind1, kind2, ...
        """
        before = {
            "columns": {
                column: _plain(getattr(primary, ATTRIBUTES.get(column, column)))
                for column in COLUMNS
            },
            "fixed": dict(primary.infos.get("fixed") or {}),
            "contacts": dict(primary.infos.get("contacts") or {}),
        }

        theirs = _details(primary)
        for name, value in _details(duplicate).items():
            if name not in theirs:
                _set_detail(primary, name, value)

        primary.infos["contacts"] = {
            key: value for key, (value, _) in _merged_contacts(primary, duplicate).items()
        }

        primary.save()
        return before

    @staticmethod
    def _restore_details(primary, before):
        for name, value in before.get("columns", {}).items():
            _set_detail(primary, name, value)
        for section in ("fixed", "contacts"):
            if section in before:
                primary.infos[section] = before[section]

    @staticmethod
    def _merge_own_references(duplicate, primary):
        """The people the duplicate's own schedulers and emergency_contacts
        name are added to the primary's; an entry the primary already has,
        or one naming either record, is left alone."""
        added = {}
        for key in REFERENCE_KEYS:
            ours = duplicate.infos.get(key) or {}
            theirs = primary.infos.setdefault(key, {})
            added[key] = [
                other
                for other in ours
                if other not in theirs and other not in (str(duplicate.pk), str(primary.pk))
            ]
            for other in added[key]:
                theirs[other] = ours[other]
        primary.save(update_fields=["infos"])
        return added

    @staticmethod
    def _restore_own_references(primary, added):
        for key, others in added.items():
            for other in others:
                (primary.infos.get(key) or {}).pop(other, None)

    @staticmethod
    def _fold_attendings(duplicate, primary):
        """An attending the primary lacks (by registration) moves whole; one it
        already has is folded into it, enrollment by enrollment, and retired."""
        record = {"moved": [], "folded": []}
        for attending in Attending.objects.filter(attendee=duplicate):
            target = Attending.objects.filter(
                attendee=primary, registration_id=attending.registration_id
            ).first()
            if target is None:
                attending.attendee = primary
                attending.save(update_fields=["attendee"])
                record["moved"].append(attending.pk)
                continue

            fold = {
                "attending": attending.pk,
                "into": target.pk,
                "enrollments": [],
                "enrollments_retired": [],
                "attendances": [],
                "attendances_retired": [],
            }
            for enrollment in AttendingMeet.objects.filter(attending=attending):
                clash = AttendingMeet.objects.filter(
                    attending=target,
                    meet_id=enrollment.meet_id,
                    character_id=enrollment.character_id,
                    team_id=enrollment.team_id,
                ).exists()
                _repoint_or_retire(
                    enrollment, "attending", target, clash,
                    fold["enrollments"], fold["enrollments_retired"],
                )
            for attendance in Attendance.objects.filter(attending=attending):
                clash = Attendance.objects.filter(
                    attending=target,
                    gathering_id=attendance.gathering_id,
                    character_id=attendance.character_id,
                    team_id=attendance.team_id,
                    start=attendance.start,
                ).exists()
                _repoint_or_retire(
                    attendance, "attending", target, clash,
                    fold["attendances"], fold["attendances_retired"],
                )
            attending.is_removed = True
            attending.save(update_fields=["is_removed"])
            record["folded"].append(fold)
        return record

    @staticmethod
    def _move_memberships(duplicate, primary):
        """Every membership moves, whatever the folk; one in a folk the
        primary is already in is retired and the primary's row stays."""
        record = {"moved": [], "retired": []}
        for membership in FolkAttendee.objects.filter(attendee=duplicate):
            clash = FolkAttendee.objects.filter(
                attendee=primary, folk_id=membership.folk_id
            ).exists()
            if clash:
                membership.is_removed = True
                membership.save(update_fields=["is_removed"])
                record["retired"].append(membership.pk)
            else:
                membership.attendee = primary
                membership.save(update_fields=["attendee"])
                record["moved"].append(membership.pk)
        return record

    @staticmethod
    def _move_linked(model, duplicate, primary):
        ids = [
            str(pk)
            for pk in model.objects.filter(
                content_type=_attendee_type(), object_id=str(duplicate.pk)
            ).values_list("pk", flat=True)
        ]
        model.objects.filter(pk__in=ids).update(object_id=str(primary.pk))
        return ids

    @staticmethod
    def _move_places(duplicate, primary):
        """Moved unless the primary already has that address (unique while live)."""
        record = {"moved": [], "retired": []}
        for place in Place.objects.filter(
            content_type=_attendee_type(), object_id=str(duplicate.pk)
        ):
            clash = place.address_id is not None and Place.objects.filter(
                content_type=_attendee_type(),
                object_id=str(primary.pk),
                organization_id=place.organization_id,
                address_id=place.address_id,
            ).exists()
            if clash:
                place.is_removed = True
                place.save(update_fields=["is_removed"])
                record["retired"].append(str(place.pk))
            else:
                place.object_id = str(primary.pk)
                place.save(update_fields=["object_id"])
                record["moved"].append(str(place.pk))
        return record

    @staticmethod
    def _move_registrations(duplicate, primary):
        ids = [
            str(pk)
            for pk in Registration.objects.filter(registrant=duplicate).values_list(
                "pk", flat=True
            )
        ]
        Registration.objects.filter(pk__in=ids).update(registrant=primary)
        return ids

    @staticmethod
    def _move_login(duplicate, primary):
        if duplicate.user_id is None or primary.user_id is not None:
            return None
        user_id = duplicate.user_id
        duplicate.user = None
        duplicate.save(update_fields=["user"])
        primary.user_id = user_id
        primary.save(update_fields=["user"])
        return user_id

    @staticmethod
    def _rekey_references(duplicate, primary):
        """Other attendees naming the duplicate by id now name the primary;
        an entry the primary already has, or a self-reference, wins."""
        mine, theirs = str(duplicate.pk), str(primary.pk)
        entries = []
        for key in REFERENCE_KEYS:
            holders = Attendee.all_objects.filter(
                division__organization_id=duplicate.division.organization_id,
                **{f"infos__{key}__has_key": mine},
            ).exclude(pk=duplicate.pk)
            for holder in holders:
                section = dict(holder.infos.get(key) or {})
                value = section.pop(mine)
                set_primary = holder.pk != primary.pk and theirs not in section
                if set_primary:
                    section[theirs] = value
                holder.infos[key] = section
                holder.save(update_fields=["infos"])
                entries.append(
                    {"attendee": str(holder.pk), "key": key, "value": value, "set_primary": set_primary}
                )
        return entries

    @staticmethod
    def _restore_references(duplicate, record):
        mine, theirs = str(duplicate.pk), record["into"]
        for entry in record["moved"]["references"]:
            holder = Attendee.all_objects.filter(pk=entry["attendee"]).first()
            if holder is None:
                continue
            section = dict(holder.infos.get(entry["key"]) or {})
            if entry["set_primary"]:
                section.pop(theirs, None)
            section[mine] = entry["value"]
            holder.infos[entry["key"]] = section
            holder.save(update_fields=["infos"])

    @staticmethod
    def _repoint_tombstones(duplicate, primary):
        # Collapse the chain: earlier duplicates point at the primary directly.
        ids = [
            str(pk)
            for pk in Attendee.all_objects.filter(merged_into=duplicate).values_list(
                "pk", flat=True
            )
        ]
        Attendee.all_objects.filter(pk__in=ids).update(merged_into=primary)
        return ids
