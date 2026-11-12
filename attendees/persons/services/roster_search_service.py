import re
from datetime import datetime, timezone

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, Q, Value
from django.db.models.functions import Cast, Coalesce, Greatest
from django.http import Http404

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, Attending, AttendingMeet, FolkAttendee


class RosterSearchService:
    @staticmethod
    def search_for_roster(current_user, meet_slug, query):
        """
        Omni search for attendees to be added or checked into a roster.
        - Validates that current_user has an organization and that meet belongs to current_user.organization.
        - If current_user.can_see_all_organizational_meets_attendees() is True, searches across organization.
        - If False, restricts search to attendees sharing a Folk with current_user.attendee.
        - Supports phone search (last 4 digits or formatted), multi-word names, and fuzzy typo matching (via
          pg_trgm TrigramSimilarity) on traditional/simplified Chinese, names and romanization.
        - If meet.infos['kid_search_families_show_grades'] is True:
            - Performs cross-relation search: includes other members sharing a Folk with matched attendees.
            - Includes age, grade_name (mapped via organization.infos['grade_converter']), grade_index, and guardians.
        - Returns contacts dictionary and complete folks array for each candidate.
        - Identifies meet_status ('paused', 'enrolled', 'expired', 'not_enrolled') and can_join boolean.
          PAUSED status CANNOT be auto-joined (can_join=False).
        """
        if not current_user or not current_user.is_authenticated or not getattr(current_user, "organization", None):
            raise PermissionDenied("Authentication and organization are required.")

        if not meet_slug:
            raise ValueError("meet_slug is required.")

        meet = (
            Meet.objects.filter(slug=meet_slug, is_removed=False)
            .select_related("assembly__division__organization")
            .first()
        )
        if not meet:
            raise Http404("Meet not found.")

        meet_org = (
            meet.assembly.division.organization
            if (meet.assembly and meet.assembly.division)
            else None
        )
        if not meet_org or meet_org.id != current_user.organization.id:
            raise PermissionDenied("User does not have access to this meet's organization.")

        q = (query or "").strip()
        if not q:
            return []

        can_see_all = current_user.can_see_all_organizational_meets_attendees()
        user_folk_ids = None

        if can_see_all:
            base_qs = Attendee.objects.filter(
                division__organization=current_user.organization,
                is_removed=False,
            )
        else:
            if not hasattr(current_user, "attendee") or not current_user.attendee:
                return []
            user_folk_ids = list(
                current_user.attendee.folks.filter(is_removed=False).values_list("id", flat=True)
            )
            base_qs = Attendee.objects.filter(
                folks__in=user_folk_ids,
                division__organization=current_user.organization,
                is_removed=False,
            ).distinct()

        # Annotate contacts as string for regex matching on JSON values
        base_qs = base_qs.annotate(contacts_str=Cast("infos__contacts", CharField()))

        # Match query directly against precomputed database fields
        match_q = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(first_name2__icontains=q)
            | Q(last_name2__icontains=q)
            | Q(infos__names__original__icontains=q)
            | Q(infos__names__traditional__icontains=q)
            | Q(infos__names__simplified__icontains=q)
            | Q(infos__names__romanization__icontains=q)
            | Q(infos__names__nick__icontains=q)
            | Q(contacts_str__iregex=r':\s*\"[^\"]*' + re.escape(q))
        )

        # Multi-word matching (e.g. "Daniel Bo" or "Hannah 傅")
        words = [w for w in q.split() if len(w) > 0]
        if len(words) > 1:
            multi_word_q = Q()
            for w in words:
                multi_word_q &= (
                    Q(first_name__icontains=w)
                    | Q(last_name__icontains=w)
                    | Q(first_name2__icontains=w)
                    | Q(last_name2__icontains=w)
                    | Q(infos__names__original__icontains=w)
                    | Q(infos__names__traditional__icontains=w)
                    | Q(infos__names__simplified__icontains=w)
                    | Q(infos__names__romanization__icontains=w)
                    | Q(infos__names__nick__icontains=w)
                )
            match_q |= multi_word_q

        # Phone matching: last 4 digits or full phone number across any phone1, phone2, phone3...
        digits = re.sub(r"\D", "", q)
        if len(digits) >= 4:
            phone_pattern = r':\s*\"[^\"]*' + r'\D*'.join(digits[-10:]) + r'\D*\"'
            match_q |= Q(contacts_str__regex=phone_pattern)

        # Fuzzy matching using pg_trgm TrigramSimilarity against DB precomputed fields if length >= 3
        has_sim = False
        direct_attendees = []
        if len(q) >= 3:
            try:
                sim_expr = Greatest(
                    TrigramSimilarity(Cast("infos__names__original", CharField()), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__traditional", CharField()), Value("")), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__simplified", CharField()), Value("")), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__romanization", CharField()), Value("")), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__nick", CharField()), Value("")), q),
                    TrigramSimilarity("first_name", q),
                    TrigramSimilarity("last_name", q),
                    TrigramSimilarity(Coalesce("first_name2", Value("")), q),
                    TrigramSimilarity(Coalesce("last_name2", Value("")), q),
                )
                direct_qs = (
                    base_qs.annotate(similarity=sim_expr)
                    .filter(match_q | Q(similarity__gte=0.25))
                    .order_by("-similarity", "last_name", "first_name")
                )
                direct_attendees = list(direct_qs[:25])
                has_sim = True
            except Exception:
                has_sim = False

        if not has_sim:
            direct_qs = base_qs.filter(match_q).order_by("last_name", "first_name")
            direct_attendees = list(direct_qs[:25])

        is_kid_meet = bool(meet.infos.get("kid_search_families_show_grades")) if meet.infos else False

        # Build candidate map: attendee_id -> { 'attendee': attendee, 'matched_by': ..., 'relation_source_name': ... }
        candidates_map = {}
        for a in direct_attendees:
            candidates_map[a.id] = {
                "attendee": a,
                "matched_by": "direct",
                "relation_source_name": None,
            }

        # Cross-relation search if kid_search_families_show_grades is True
        if is_kid_meet and direct_attendees:
            direct_ids = [a.id for a in direct_attendees]
            fa_qs = FolkAttendee.objects.filter(
                attendee_id__in=direct_ids,
                is_removed=False,
                folk__is_removed=False,
            ).values("folk_id", "attendee_id")

            folk_to_direct_attendees = {}
            for item in fa_qs:
                folk_to_direct_attendees.setdefault(item["folk_id"], []).append(item["attendee_id"])

            if folk_to_direct_attendees:
                related_fa_qs = FolkAttendee.objects.filter(
                    folk_id__in=folk_to_direct_attendees.keys(),
                    is_removed=False,
                    folk__is_removed=False,
                ).exclude(
                    attendee_id__in=direct_ids
                ).values("attendee_id", "folk_id")

                related_attendee_folk_map = {}
                for item in related_fa_qs:
                    related_attendee_folk_map[item["attendee_id"]] = item["folk_id"]

                if related_attendee_folk_map:
                    rel_attendees_qs = Attendee.objects.filter(
                        id__in=related_attendee_folk_map.keys(),
                        division__organization=current_user.organization,
                        is_removed=False,
                    )
                    if not can_see_all and user_folk_ids:
                        rel_attendees_qs = rel_attendees_qs.filter(folks__in=user_folk_ids).distinct()

                    direct_attendee_lookup = {a.id: a for a in direct_attendees}
                    for rel_attendee in rel_attendees_qs[:25]:
                        if rel_attendee.id not in candidates_map:
                            f_id = related_attendee_folk_map.get(rel_attendee.id)
                            source_ids = folk_to_direct_attendees.get(f_id, [])
                            source_name = None
                            if source_ids and source_ids[0] in direct_attendee_lookup:
                                source_name = direct_attendee_lookup[source_ids[0]].display_label
                            candidates_map[rel_attendee.id] = {
                                "attendee": rel_attendee,
                                "matched_by": "relation",
                                "relation_source_name": source_name,
                            }

        if not candidates_map:
            return []

        all_candidate_ids = list(candidates_map.keys())[:35]
        now_dt = datetime.now(timezone.utc)

        # Batch query AttendingMeets for target meet
        ams = (
            AttendingMeet.objects.filter(
                attending__attendee_id__in=all_candidate_ids,
                meet=meet,
                is_removed=False,
            )
            .select_related("attending", "category")
            .order_by("-finish", "-created")
        )
        ams_by_attendee = {}
        for am in ams:
            ams_by_attendee.setdefault(am.attending.attendee_id, []).append(am)

        # Batch query latest active Attending
        latest_attendings = (
            Attending.objects.filter(
                attendee_id__in=all_candidate_ids,
                is_removed=False,
            )
            .order_by("attendee_id", "-created")
        )
        attending_by_attendee = {}
        for att in latest_attendings:
            if att.attendee_id not in attending_by_attendee:
                attending_by_attendee[att.attendee_id] = att.id

        # Batch query FolkAttendee for all candidates to build folks array
        all_fas = (
            FolkAttendee.objects.filter(
                attendee_id__in=all_candidate_ids,
                is_removed=False,
                folk__is_removed=False,
            )
            .select_related("folk", "folk__category", "role")
            .order_by("display_order", "id")
        )
        fas_by_attendee = {}
        for fa in all_fas:
            fas_by_attendee.setdefault(fa.attendee_id, []).append(fa)

        grade_converter = (
            current_user.organization.infos.get("grade_converter", [])
            if (current_user.organization and isinstance(current_user.organization.infos, dict))
            else []
        )

        results = []
        for cand_id in all_candidate_ids:
            cand_info = candidates_map[cand_id]
            attendee = cand_info["attendee"]

            # AttendingMeet status
            cand_ams = ams_by_attendee.get(attendee.id, [])
            if any(am.category_id == Attendee.PAUSED_CATEGORY for am in cand_ams):
                meet_status = "paused"
                can_join = False
                matched_am = next(am for am in cand_ams if am.category_id == Attendee.PAUSED_CATEGORY)
                am_id = matched_am.id
            elif any(am.finish is None or am.finish >= now_dt for am in cand_ams):
                meet_status = "enrolled"
                can_join = False
                matched_am = next(am for am in cand_ams if am.finish is None or am.finish >= now_dt)
                am_id = matched_am.id
            elif cand_ams:
                meet_status = "expired"
                can_join = True
                am_id = cand_ams[0].id
            else:
                meet_status = "not_enrolled"
                can_join = True
                am_id = None

            # Photo URL
            photo_url = None
            if attendee.photo:
                try:
                    photo_url = attendee.photo.url
                except Exception:
                    pass

            # Contacts dictionary
            contacts = attendee.infos.get("contacts", {}) if isinstance(attendee.infos, dict) else {}

            # Age, grade, and guardians
            if is_kid_meet:
                age = attendee.age()
                grade_idx = (
                    attendee.infos.get("fixed", {}).get("grade")
                    if isinstance(attendee.infos, dict)
                    else None
                )
                grade_name = None
                grade_index = None
                if grade_idx is not None:
                    try:
                        g_int = int(grade_idx)
                        if 0 <= g_int < len(grade_converter):
                            grade_name = grade_converter[g_int]
                        else:
                            grade_name = str(g_int)
                        grade_index = g_int
                    except (ValueError, TypeError):
                        grade_name = str(grade_idx)

                guardians = attendee.parents_notifiers_names
                if not guardians:
                    family_fas = fas_by_attendee.get(attendee.id, [])
                    fam_folk_ids = [fa.folk_id for fa in family_fas if fa.folk.category_id == Attendee.FAMILY_CATEGORY]
                    if fam_folk_ids:
                        fam_members = Attendee.objects.filter(
                            folks__in=fam_folk_ids,
                            division__organization=current_user.organization,
                            is_removed=False,
                        ).exclude(id=attendee.id).distinct()
                        adult_guardians = [m.display_label for m in fam_members if (m.age() is None or m.age() >= 18)]
                        guardians = ", ".join(adult_guardians) if adult_guardians else None
            else:
                age = None
                grade_name = None
                grade_index = None
                guardians = None

            # Full folks array: family folks ordered by created desc (latest first)
            cand_fas = fas_by_attendee.get(attendee.id, [])
            family_fas = [fa for fa in cand_fas if fa.folk and fa.folk.category_id == Attendee.FAMILY_CATEGORY]
            family_fas.sort(
                key=lambda fa: (fa.folk.created if fa.folk and fa.folk.created else datetime.min.replace(tzinfo=timezone.utc)),
                reverse=True,
            )
            non_family_fas = [fa for fa in cand_fas if fa.folk and fa.folk.category_id != Attendee.FAMILY_CATEGORY]
            sorted_cand_fas = family_fas + non_family_fas

            folks_list = [
                {
                    "id": str(fa.folk.id),
                    "name": fa.folk.display_name or "",
                    "category_id": fa.folk.category_id,
                    "category_name": fa.folk.category.display_name if fa.folk.category else "",
                    "role_id": fa.role_id,
                    "role_title": fa.role.title if fa.role else "",
                    "is_emergency_contact": fa.role.emergency_contact if fa.role else False,
                    "display_order": fa.display_order,
                    "created": fa.folk.created.isoformat() if (fa.folk and fa.folk.created) else None,
                    "is_latest_family": bool(family_fas and fa.folk_id == family_fas[0].folk_id),
                }
                for fa in sorted_cand_fas
            ]

            # Primary family folk attendee for default role / relationship (latest created family first)
            fam_fa = family_fas[0] if family_fas else (cand_fas[0] if cand_fas else None)
            fixed_infos = attendee.infos.get("fixed", {}) if isinstance(attendee.infos, dict) else {}

            results.append({
                "id": str(attendee.id),
                "name": attendee.display_label,
                "first_name": attendee.first_name or "",
                "last_name": attendee.last_name or "",
                "first_name2": attendee.first_name2 or "",
                "last_name2": attendee.last_name2 or "",
                "gender": attendee.gender,
                "division_id": attendee.division_id,
                "role_id": fam_fa.role_id if fam_fa else None,
                "role_title": fam_fa.role.title if (fam_fa and fam_fa.role) else None,
                "latest_family_id": str(family_fas[0].folk.id) if family_fas else None,
                "latest_family_name": family_fas[0].folk.display_name if family_fas else None,
                "food_pref": fixed_infos.get("food_pref"),
                "insurer": fixed_infos.get("insurer"),
                "actual_birthday": attendee.actual_birthday.isoformat() if attendee.actual_birthday else None,
                "estimated_birthday": str(attendee.estimated_birthday) if attendee.estimated_birthday else None,
                "photo_url": photo_url,
                "contacts": contacts,
                "age": age,
                "grade_name": grade_name,
                "grade_index": grade_index,
                "guardians": guardians,
                "meet_status": meet_status,
                "can_join": can_join,
                "attendingmeet_id": am_id,
                "attending_id": attending_by_attendee.get(attendee.id),
                "folks": folks_list,
                "matched_by": cand_info["matched_by"],
                "relation_source_name": cand_info["relation_source_name"],
            })

        return results
