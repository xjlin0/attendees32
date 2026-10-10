"""Merging one attendee into another, and undoing it.

The duplicate is soft-deleted and keeps a forwarding address; what it held
moves to the primary. The primary's own details stay unless the primary has
none or ``keep`` names the duplicate's; phones and emails from both are kept.
What moved and what the primary's details were is written on the tombstone
(``infos["merge"]``), so ``unmerge`` can put it all back once. Merging B into
C also re-points everything already merged into B, so a chain only exists in
hand-edited data and walking one is a bounded guard.
"""

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.fields.files import FieldFile
from partial_date import PartialDate

from attendees.occasions.models import Attendance
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Folk,
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

#: An attendee's own single-value details, by the name ``keep`` uses. The
#: keys of ``infos["fixed"]`` are ``fixed.<key>`` and contacts other than
#: phones and emails are ``contacts.<key>``.
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

#: Contacts held as numbered slots: phone1, phone2, ... and email1, email2, ...
SLOTS = {"phones": "phone", "emails": "email"}


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


def _is_slot(key, kind):
    return key.lower().startswith(SLOTS[kind])


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
    for key, value in (attendee.infos.get("contacts") or {}).items():
        if not _blank(value) and not any(_is_slot(key, kind) for kind in SLOTS):
            details[f"contacts.{key}"] = value
    return details


def _slot_values(attendee, kind):
    """The phones (or emails) an attendee holds, in slot order."""
    contacts = attendee.infos.get("contacts") or {}
    return [
        contacts[key]
        for key in sorted(contacts)
        if _is_slot(key, kind) and not _blank(contacts[key])
    ]


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
    def merge(duplicate, primary, by=None, keep=None):
        """Merges ``duplicate`` into ``primary`` and returns the primary.

        ``keep`` is what the merge screen chose: ``{"actual_birthday":
        "duplicate"}`` takes the duplicate's value where both records have
        one, ``{"phones": [...]}`` and ``{"emails": [...]}`` list the ones to
        keep, in slot order. Without it the primary's values stay, the
        duplicate's fill the blanks, and every phone and email is kept.

        Refused: into itself, across organizations, into a record that is
        deleted or itself merged away, when the duplicate is already merged,
        when both have a login, or when ``keep`` names a detail that is not
        there. ``by`` names who did it, for the record.
        """
        given = (duplicate, primary)
        duplicate, primary = AttendeeMergeService._locked(duplicate, primary)

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

        was_removed = duplicate.is_removed
        # The primary is saved here, before anything below re-reads its row.
        moved = {
            "details": AttendeeMergeService._merge_details(duplicate, primary, keep),
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
    @transaction.atomic
    def unmerge(duplicate):
        """Puts back what the merge moved and revives the duplicate, once.

        The primary's own details go back to what they were before the merge.
        Rows the primary gained since the merge stay with it. A login that
        moved and has changed hands since is refused rather than guessed.
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
        Folk.all_objects.filter(pk__in=memberships["folks_retired"]).update(is_removed=False)

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
    def _merge_details(duplicate, primary, keep):
        """Writes the merged record's own details on the primary and returns
        what they were, for ``unmerge``.

        A detail keeps the primary's value; the duplicate's fills a blank, and
        wins where ``keep`` says ``"duplicate"``. Phones and emails are the
        primary's then the duplicate's new ones, or the ones ``keep`` lists,
        laid into phone1, phone2, ... and email1, email2, ...
        """
        keep = dict(keep or {})
        chosen_slots = {kind: keep.pop(kind, None) for kind in SLOTS}
        for kind, chosen in chosen_slots.items():
            if chosen is not None and not isinstance(chosen, list):
                raise MergeRefused(f"keep must list the {kind} to keep.")

        theirs, mine = _details(primary), _details(duplicate)
        for name, who in keep.items():
            if who not in ("primary", "duplicate"):
                raise MergeRefused(f"keep must say primary or duplicate for {name}.")
            if name not in theirs and name not in mine:
                raise MergeRefused(f"Neither record has {name}.")
            if who == "duplicate" and name not in mine:
                raise MergeRefused(f"The duplicate has no {name} to keep.")

        before = {"columns": {}}
        for name, value in mine.items():
            if name in theirs and keep.get(name) != "duplicate":
                continue
            if theirs.get(name) == value:
                continue
            section, _, _ = name.partition(".")
            if section in ("fixed", "contacts"):
                before.setdefault(section, dict(primary.infos.get(section) or {}))
            else:
                before["columns"][name] = _plain(getattr(primary, ATTRIBUTES.get(name, name)))
            _set_detail(primary, name, value)

        for kind, prefix in SLOTS.items():
            held = _slot_values(primary, kind)
            held += [value for value in _slot_values(duplicate, kind) if value not in held]
            chosen = held if chosen_slots[kind] is None else list(dict.fromkeys(chosen_slots[kind]))
            for value in chosen:
                if value not in held:
                    raise MergeRefused(f"Neither record has {value} among its {kind}.")
            if chosen == _slot_values(primary, kind):
                continue
            before.setdefault("contacts", dict(primary.infos.get("contacts") or {}))
            contacts = primary.infos.setdefault("contacts", {})
            for key in [key for key in contacts if _is_slot(key, kind)]:
                del contacts[key]
            for number, value in enumerate(chosen, start=1):
                contacts[f"{prefix}{number}"] = value

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
        """Moved unless the primary is already in that folk. The duplicate's
        own auto-created hidden folk is retired with it when nobody else is in it."""
        record = {"moved": [], "retired": [], "folks_retired": []}
        for membership in FolkAttendee.objects.filter(attendee=duplicate):
            folk = membership.folk
            own_hidden = (
                folk.category_id == Attendee.NON_FAMILY_CATEGORY
                and membership.role_id == Attendee.HIDDEN_ROLE
                and not FolkAttendee.objects.filter(folk=folk).exclude(pk=membership.pk).exists()
            )
            clash = FolkAttendee.objects.filter(attendee=primary, folk=folk).exists()
            if own_hidden or clash:
                membership.is_removed = True
                membership.save(update_fields=["is_removed"])
                record["retired"].append(membership.pk)
                if own_hidden:
                    folk.is_removed = True
                    folk.save(update_fields=["is_removed"])
                    record["folks_retired"].append(str(folk.pk))
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
