import re
from datetime import date, datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.http import Http404
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied, ValidationError

from attendees.occasions.models import Attendance, Character, Gathering, Meet
from attendees.whereabouts.models import Division
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Category,
    Folk,
    FolkAttendee,
    GenderEnum,
    Relation,
    Utility,
)


class FastOnboardService:
    """
    Service responsible for the fast onboarding pipeline:
    validates incoming payload, upserts attendees & companions,
    links family/non-family relations, and enrolls/records attendance.
    """

    @staticmethod
    def normalize_phone_number(val):
        return Utility.normalize_phone_number(val)

    @classmethod
    def _extract_contacts(cls, att_data):
        contacts = {}
        raw_contacts = att_data.get("contacts")
        if isinstance(raw_contacts, list):
            type_counts = {}
            for c in raw_contacts:
                ct = (c.get("type") or "phone").strip().lower()
                cv = (c.get("value") or "").strip()
                if cv:
                    if ct in ("phone", "whatsapp"):
                        cv = cls.normalize_phone_number(cv)
                    type_counts[ct] = type_counts.get(ct, 0) + 1
                    c_idx = type_counts[ct]
                    contacts[f"{ct}{c_idx}"] = cv
        elif isinstance(raw_contacts, dict):
            contacts = {
                (k if re.search(r'\d$', k) else f"{k}1"): (
                    cls.normalize_phone_number(v) if k.startswith("phone") or k.startswith("whatsapp") else v
                )
                for k, v in raw_contacts.items() if v
            }

        contact_type = (att_data.get("contact_type") or "phone").strip().lower()
        contact_value = (att_data.get("contact_value") or "").strip()
        if contact_value and not contacts:
            if contact_type in ("phone", "whatsapp"):
                contact_value = cls.normalize_phone_number(contact_value)
            key = contact_type if re.search(r'\d$', contact_type) else f"{contact_type}1"
            contacts[key] = contact_value
        elif att_data.get("phone") and not any(k.startswith("phone") for k in contacts):
            ph = cls.normalize_phone_number(att_data.get("phone").strip())
            contacts["phone1"] = ph
        if att_data.get("email") and not any(k.startswith("email") for k in contacts):
            em = att_data.get("email").strip()
            contacts["email1"] = em

        return contacts

    @classmethod
    def _validate_and_normalize_attendees(cls, attendees_data, is_kid_meet, show_insurer, current_year, now_date, current_user, meet):
        validated_attendees = []

        for idx, att_data in enumerate(attendees_data):
            att_label = f"Attendee {idx + 1}" if len(attendees_data) > 1 else "Attendee"
            first_name = (att_data.get("first_name") or "").strip() or None
            last_name = (att_data.get("last_name") or "").strip() or None
            first_name2 = (att_data.get("first_name2") or "").strip() or None
            last_name2 = (att_data.get("last_name2") or "").strip() or None

            if not (first_name or last_name or first_name2 or last_name2):
                raise ValidationError({"name": f"{att_label} name (English or other language) is required."})

            gender = att_data.get("gender") or GenderEnum.UNSPECIFIED.value

            byear = att_data.get("birthday_year")
            bmonth = att_data.get("birthday_month")
            bday = att_data.get("birthday_day")
            try:
                byear = int(byear) if byear is not None and str(byear).strip() != "" else None
                bmonth = int(bmonth) if bmonth is not None and str(bmonth).strip() != "" else None
                bday = int(bday) if bday is not None and str(bday).strip() != "" else None
            except (ValueError, TypeError):
                raise ValidationError({"birthday": f"{att_label} birthday year, month, and day must be valid numbers."})

            if byear is not None:
                if byear > current_year:
                    raise ValidationError({"birthday": f"Birth year cannot exceed {current_year}."})
                if byear < 1900:
                    raise ValidationError({"birthday": "Birth year must be 1900 or later."})

            actual_birthday = None
            estimated_birthday = None

            if is_kid_meet:
                if not (byear and bmonth and bday):
                    raise ValidationError({"birthday": "Year, Month, and Day of birth are required for kids."})
                try:
                    actual_birthday = date(byear, bmonth, bday)
                except ValueError as e:
                    raise ValidationError({"birthday": f"Invalid birthday date: {e}"})

                if actual_birthday > now_date:
                    raise ValidationError({"birthday": "Birthday cannot be in the future."})

                grade = att_data.get("grade")
                if grade is None or str(grade).strip() == "":
                    raise ValidationError({"grade": "School grade is required for kids."})

                food_pref = (att_data.get("food_pref") or "").strip()
                if not food_pref:
                    raise ValidationError({"food_pref": "Food preference / allergies is required for kids (enter 'None' if none)."})

                insurer = (att_data.get("insurer") or "").strip() if show_insurer else None
            else:
                if byear and bmonth and bday:
                    try:
                        actual_birthday = date(byear, bmonth, bday)
                    except ValueError as e:
                        raise ValidationError({"birthday": f"Invalid birthday date: {e}"})
                    if actual_birthday > now_date:
                        raise ValidationError({"birthday": "Birthday cannot be in the future."})
                elif bmonth and bday and not byear:
                    try:
                        date(1800, bmonth, bday)
                    except ValueError as e:
                        raise ValidationError({"birthday": f"Invalid birthday date: {e}"})
                    estimated_birthday = f"1800-{bmonth:02d}-{bday:02d}"
                elif byear and bmonth:
                    if not (1 <= bmonth <= 12):
                        raise ValidationError({"birthday": "Invalid birth month: must be between 1 and 12."})
                    estimated_birthday = f"{byear:04d}-{bmonth:02d}"
                elif byear:
                    estimated_birthday = f"{byear:04d}"
                elif bday and not bmonth:
                    raise ValidationError({"birthday": "Birth month is required when birth day is specified."})

                grade = att_data.get("grade")
                food_pref = (att_data.get("food_pref") or "").strip() or None
                insurer = (att_data.get("insurer") or "").strip() if show_insurer else None

            fixed = {}
            if grade is not None and str(grade).strip() != "":
                try:
                    fixed["grade"] = int(grade)
                except (ValueError, TypeError):
                    fixed["grade"] = grade
            if food_pref:
                fixed["food_pref"] = food_pref
            if insurer:
                fixed["insurer"] = insurer

            contacts = cls._extract_contacts(att_data)

            infos = {"fixed": fixed}
            if contacts:
                infos["contacts"] = contacts

            division_id = att_data.get("division_id") or att_data.get("division")
            att_div = None
            if division_id:
                att_div = Division.objects.filter(pk=division_id, organization=current_user.organization).first()
            if not att_div:
                att_div = meet.assembly.division

            validated_attendees.append({
                "attendee_id": att_data.get("attendee_id") or att_data.get("id"),
                "first_name": first_name,
                "last_name": last_name,
                "first_name2": first_name2,
                "last_name2": last_name2,
                "gender": gender,
                "division": att_div,
                "actual_birthday": actual_birthday,
                "estimated_birthday": estimated_birthday,
                "infos": infos,
            })

        return validated_attendees

    @classmethod
    def _validate_companions(cls, companions, is_kid_meet, unaccompanied):
        if unaccompanied:
            return "⚠Missing companion info"

        if companions:
            for idx, c in enumerate(companions):
                c_first = (c.get("first_name") or "").strip() or None
                c_last = (c.get("last_name") or "").strip() or None
                c_first2 = (c.get("first_name2") or "").strip() or None
                c_last2 = (c.get("last_name2") or "").strip() or None
                if not (c_first or c_last or c_first2 or c_last2):
                    raise ValidationError({"companions": f"Companion {idx + 1} name is required."})

                c_phone = (c.get("phone") or "").strip()
                c_contact_val = (c.get("contact_value") or "").strip()
                c_contacts_list = c.get("contacts") or []
                has_contact = bool(c_phone or c_contact_val or c_contacts_list)
                if is_kid_meet and not has_contact:
                    raise ValidationError({"companions": f"Companion {idx + 1} contact number or account is required."})
        elif is_kid_meet:
            raise ValidationError({"unaccompanied": "Companion information is required unless 'Child arrived alone' is checked."})

        return None

    @classmethod
    def _upsert_attendee(cls, att_id, first_name, last_name, first_name2, last_name2, gender, division, infos, actual_birthday=None, estimated_birthday=None, current_user=None):
        attendee = None
        if att_id:
            attendee = Attendee.objects.filter(pk=att_id, division__organization=current_user.organization).first()
        if attendee:
            if first_name:
                attendee.first_name = first_name
            if last_name:
                attendee.last_name = last_name
            if first_name2:
                attendee.first_name2 = first_name2
            if last_name2:
                attendee.last_name2 = last_name2
            if gender and gender != GenderEnum.UNSPECIFIED.value:
                attendee.gender = gender
            if division:
                attendee.division = division
            if actual_birthday:
                attendee.actual_birthday = actual_birthday
            if estimated_birthday:
                attendee.estimated_birthday = estimated_birthday
            attendee.infos = Utility.deep_merge_attendee_infos(
                attendee.infos,
                infos,
                getattr(current_user, "attendee_uuid", None),
            )
            attendee.save()
        else:
            attendee = Attendee.objects.create(
                first_name=first_name,
                last_name=last_name,
                first_name2=first_name2,
                last_name2=last_name2,
                gender=gender,
                division=division,
                actual_birthday=actual_birthday,
                estimated_birthday=estimated_birthday,
                infos=infos,
            )
        return attendee

    @classmethod
    def _link_kid_meet_folks(cls, created_attendees, created_companions, target_folk_id, create_new_folk):
        family_folk = None
        if not create_new_folk:
            if target_folk_id:
                family_folk = Folk.objects.filter(
                    pk=target_folk_id,
                    category=Attendee.FAMILY_CATEGORY,
                    is_removed=False,
                ).first()
            if not family_folk:
                all_people = list(created_attendees) + [c[0] for c in created_companions]
                family_folk = (
                    Folk.objects.filter(
                        folkattendee__attendee__in=all_people,
                        category=Attendee.FAMILY_CATEGORY,
                        is_removed=False,
                    )
                    .distinct()
                    .order_by("-created")
                    .first()
                )

        for c_idx, (comp_attendee, c_data) in enumerate(created_companions):
            c_rel = c_data.get("relationship") or c_data.get("relation_id")
            comp_role = None
            if c_rel:
                if str(c_rel).isdigit():
                    comp_role = Relation.objects.filter(pk=int(c_rel), is_removed=False).first()
                else:
                    comp_role = Relation.objects.filter(title__iexact=str(c_rel).strip(), is_removed=False).first()

            if not comp_role:
                norm_cg = str(comp_attendee.gender).strip().lower()
                if norm_cg == "male":
                    comp_role = Relation.objects.filter(title__iexact="father", is_removed=False).first()
                elif norm_cg == "female":
                    comp_role = Relation.objects.filter(title__iexact="mother", is_removed=False).first()
                if not comp_role:
                    comp_role = (
                        Relation.objects.filter(title__iexact="parent", is_removed=False).first()
                        or Relation.objects.filter(emergency_contact=True).first()
                        or Relation.objects.filter(id=1).first()
                        or Relation.objects.first()
                    )

            recip_role = None
            if comp_role and comp_role.reciprocal_ids:
                recips = list(Relation.objects.filter(pk__in=comp_role.reciprocal_ids, is_removed=False))
                if comp_role.title and comp_role.title.lower() in ("guardian", "caregiver"):
                    recip_role = next((r for r in recips if r.title.lower() in ("ward", "care receiver")), None)
                else:
                    recip_role = next((r for r in recips if r.title.lower() == "child"), None)
                if not recip_role and recips:
                    recip_role = recips[0]

            if not recip_role and comp_role and comp_role.title and comp_role.title.lower() in ("guardian", "caregiver"):
                recip_role = Relation.objects.filter(title__iexact="ward").first()

            if not recip_role:
                recip_role = (
                    Relation.objects.filter(title__iexact="child").first()
                    or Relation.objects.filter(id=2).first()
                    or Relation.objects.first()
                )

            is_family = bool(comp_role and comp_role.relative)

            if is_family:
                if not family_folk:
                    family_cat, _ = Category.objects.get_or_create(
                        id=Attendee.FAMILY_CATEGORY,
                        defaults={"display_name": "Family", "type": "folk"},
                    )
                    primary_kid = created_attendees[0]
                    family_name = (
                        comp_attendee.last_name or comp_attendee.last_name2
                        or primary_kid.last_name or primary_kid.first_name
                    )
                    family_folk = Folk.objects.create(
                        category=family_cat,
                        division=comp_attendee.division,
                        display_name=f"{family_name} family",
                    )

                comp_fa_defaults = {"role": comp_role, "display_order": c_idx + 1}
                existing_comp_fa = FolkAttendee.objects.filter(folk=family_folk, attendee=comp_attendee, is_removed=False).first()
                if existing_comp_fa:
                    comp_fa_defaults["display_order"] = existing_comp_fa.display_order
                    if not comp_role:
                        comp_fa_defaults["role"] = existing_comp_fa.role

                FolkAttendee.objects.update_or_create(
                    folk=family_folk,
                    attendee=comp_attendee,
                    defaults=comp_fa_defaults,
                )

                existing_child_max = FolkAttendee.objects.filter(
                    folk=family_folk,
                    display_order__gte=11,
                    is_removed=False,
                ).aggregate(models.Max('display_order'))['display_order__max'] or 10

                for k_idx, kid in enumerate(created_attendees):
                    if comp_role and comp_role.title and comp_role.title.lower() in ("guardian", "caregiver"):
                        kid_role = recip_role
                    else:
                        norm_kid_gender = str(kid.gender).strip().lower()
                        if norm_kid_gender == "male":
                            kid_role = (
                                Relation.objects.filter(title__iexact="son", is_removed=False).first()
                                or recip_role
                            )
                        elif norm_kid_gender == "female":
                            kid_role = (
                                Relation.objects.filter(title__iexact="daughter", is_removed=False).first()
                                or recip_role
                            )
                        else:
                            kid_role = recip_role

                    kid_fa_defaults = {
                        "role": kid_role,
                        "display_order": existing_child_max + 1 + k_idx,
                    }
                    existing_kid_fa = FolkAttendee.objects.filter(folk=family_folk, attendee=kid, is_removed=False).first()
                    if existing_kid_fa:
                        kid_fa_defaults["display_order"] = existing_kid_fa.display_order

                    if kid.actual_birthday:
                        kid_fa_defaults["start"] = kid.actual_birthday

                    FolkAttendee.objects.update_or_create(
                        folk=family_folk,
                        attendee=kid,
                        defaults=kid_fa_defaults,
                    )
            else:
                for k_idx, kid in enumerate(created_attendees):
                    kid_other_folk = kid.folks.filter(category=Attendee.NON_FAMILY_CATEGORY).first()
                    if not kid_other_folk:
                        kid_name_str = (kid.infos.get("names", {}).get("original") or kid.display_label).strip()
                        non_family_cat, _ = Category.objects.get_or_create(
                            id=Attendee.NON_FAMILY_CATEGORY,
                            defaults={"display_name": "Other", "type": "folk"},
                        )
                        kid_other_folk = Folk.objects.create(
                            category=non_family_cat,
                            division=kid.division,
                            display_name=f"{kid_name_str} other",
                        )
                        FolkAttendee.objects.create(
                            folk=kid_other_folk,
                            attendee=kid,
                            role_id=Attendee.HIDDEN_ROLE,
                            display_order=0,
                        )

                    FolkAttendee.objects.update_or_create(
                        folk=kid_other_folk,
                        attendee=comp_attendee,
                        defaults={"role": comp_role, "display_order": c_idx + 1},
                    )

                    kid_fa_defaults = {
                        "role": recip_role,
                        "display_order": 11 + k_idx,
                    }
                    if kid.actual_birthday:
                        kid_fa_defaults["start"] = kid.actual_birthday

                    comp_other_folk = comp_attendee.folks.filter(category=Attendee.NON_FAMILY_CATEGORY).first()
                    if comp_other_folk:
                        FolkAttendee.objects.update_or_create(
                            folk=comp_other_folk,
                            attendee=kid,
                            defaults=kid_fa_defaults,
                        )

            # Set emergency contacts
            if comp_role and (comp_role.emergency_contact or (comp_role.title and comp_role.title.lower() in ("parent", "father", "mother", "guardian", "caregiver"))):
                for kid in created_attendees:
                    kid.infos.setdefault("emergency_contacts", {})[str(comp_attendee.id)] = True
                    comp_attendee.infos.setdefault("emergency_contacts", {})[str(kid.id)] = getattr(recip_role, "emergency_contact", False)
                    kid.save(update_fields=["infos"])
                comp_attendee.save(update_fields=["infos"])

        return family_folk

    @classmethod
    def _link_adult_meet_folks(cls, created_attendees, created_companions, target_folk_id, create_new_folk):
        all_family_members = list(created_attendees) + [c[0] for c in created_companions]
        primary_adult = created_attendees[0]
        first_comp = created_companions[0][0] if created_companions else None
        family_name = (
            (first_comp.last_name or first_comp.last_name2)
            if first_comp and (first_comp.last_name or first_comp.last_name2)
            else (primary_adult.last_name or primary_adult.last_name2 or primary_adult.first_name)
        )
        family_cat, _ = Category.objects.get_or_create(
            id=Attendee.FAMILY_CATEGORY,
            defaults={"display_name": "Family", "type": "folk"},
        )
        family_folk = None
        if not create_new_folk:
            if target_folk_id:
                family_folk = Folk.objects.filter(
                    pk=target_folk_id,
                    category=Attendee.FAMILY_CATEGORY,
                    is_removed=False,
                ).first()
            if not family_folk:
                family_folk = (
                    Folk.objects.filter(
                        folkattendee__attendee__in=all_family_members,
                        category=Attendee.FAMILY_CATEGORY,
                        is_removed=False,
                    )
                    .distinct()
                    .order_by("-created")
                    .first()
                )
        if not family_folk:
            family_folk = Folk.objects.create(
                category=family_cat,
                division=primary_adult.division,
                display_name=f"{family_name} family",
            )

        husband_role = (
            Relation.objects.filter(title__iexact="husband", is_removed=False).first()
            or Relation.objects.filter(id=5).first()
        )
        wife_role = (
            Relation.objects.filter(title__iexact="wife", is_removed=False).first()
            or Relation.objects.filter(id=6).first()
        )
        spouse_role = (
            Relation.objects.filter(title__iexact="spouse", is_removed=False).first()
            or Relation.objects.filter(id=14).first()
            or Relation.objects.first()
        )
        son_role = (
            Relation.objects.filter(title__iexact="son", is_removed=False).first()
            or Relation.objects.filter(id=3).first()
        )
        daughter_role = (
            Relation.objects.filter(title__iexact="daughter", is_removed=False).first()
            or Relation.objects.filter(id=4).first()
        )
        child_role = (
            Relation.objects.filter(title__iexact="child", is_removed=False).first()
            or Relation.objects.filter(id=27).first()
            or son_role
        )

        existing_fas = list(FolkAttendee.objects.filter(folk=family_folk, is_removed=False).select_related("role"))
        existing_roles = {fa.attendee_id: fa.role for fa in existing_fas}
        existing_orders = {fa.attendee_id: fa.display_order for fa in existing_fas}
        has_husband = any(fa.role == husband_role or fa.display_order == 1 for fa in existing_fas if fa.attendee not in all_family_members)
        has_wife = any(fa.role == wife_role or fa.display_order == 2 for fa in existing_fas if fa.attendee not in all_family_members)
        existing_child_orders = [fa.display_order for fa in existing_fas if fa.display_order >= 11 and fa.attendee not in all_family_members]
        child_count = (max(existing_child_orders) - 10) if existing_child_orders else 0

        for m_idx, member in enumerate(all_family_members):
            if member.id in existing_roles:
                m_role = existing_roles[member.id]
                m_order = existing_orders[member.id]
            else:
                m_gender = str(member.gender or "").strip().lower()
                if m_idx >= 2:
                    if m_gender == "male":
                        m_role = son_role
                    elif m_gender == "female":
                        m_role = daughter_role
                    else:
                        m_role = child_role
                    m_order = 11 + child_count
                    child_count += 1
                else:
                    if m_gender == "male":
                        if not has_husband:
                            m_role = husband_role
                            m_order = 1
                            has_husband = True
                        else:
                            m_role = son_role
                            m_order = 11 + child_count
                            child_count += 1
                    elif m_gender == "female":
                        if not has_wife:
                            m_role = wife_role
                            m_order = 2
                            has_wife = True
                        else:
                            m_role = daughter_role
                            m_order = 11 + child_count
                            child_count += 1
                    else:
                        if not has_husband:
                            m_role = husband_role or spouse_role
                            m_order = 1
                            has_husband = True
                        elif not has_wife:
                            m_role = wife_role or spouse_role
                            m_order = 2
                            has_wife = True
                        else:
                            m_role = child_role
                            m_order = 11 + child_count
                            child_count += 1

            m_defaults = {
                "role": m_role,
                "display_order": m_order,
            }
            if member.actual_birthday:
                m_defaults["start"] = member.actual_birthday

            FolkAttendee.objects.update_or_create(
                folk=family_folk,
                attendee=member,
                defaults=m_defaults,
            )

        for att in created_attendees:
            for comp_att, _ in created_companions:
                att.infos.setdefault("emergency_contacts", {})[str(comp_att.id)] = True
                comp_att.infos.setdefault("emergency_contacts", {})[str(att.id)] = True
                comp_att.save(update_fields=["infos"])
            att.save(update_fields=["infos"])

        return family_folk

    @classmethod
    def _resolve_gathering(cls, meet, gathering_id):
        gathering = None
        if gathering_id:
            if str(gathering_id).isdigit():
                gathering = Gathering.objects.filter(pk=int(gathering_id), meet=meet, is_removed=False).first()
            elif str(gathering_id).startswith("start_"):
                occ_iso = str(gathering_id).replace("start_", "")
                occ_dt = parse_datetime(occ_iso)
                if occ_dt:
                    gathering = Gathering.objects.filter(meet=meet, start=occ_dt, is_removed=False).first()
                    if not gathering:
                        site_type = meet.site_type or (ContentType.objects.get_for_model(meet.assembly) if getattr(meet, 'assembly', None) else None) or ContentType.objects.get_for_model(Meet)
                        site_id = str(meet.site_id) if meet.site_id else (str(meet.assembly.id) if getattr(meet, 'assembly', None) else str(meet.id))
                        gathering = Gathering.objects.create(
                            meet=meet,
                            display_name=f"{meet.display_name} {occ_dt.strftime('%Y-%m-%d %H:%M')}",
                            start=occ_dt,
                            finish=occ_dt + timedelta(hours=2),
                            site_type=site_type,
                            site_id=site_id,
                        )

        if not gathering:
            now = Utility.now_with_timezone()
            gathering = (
                Gathering.objects.filter(
                    meet=meet,
                    start__lte=now,
                    finish__gte=now,
                    is_removed=False,
                ).first()
                or Gathering.objects.filter(
                    meet=meet,
                    start__gte=now - timedelta(hours=2),
                    is_removed=False,
                ).order_by("start").first()
                or Gathering.objects.filter(
                    meet=meet,
                    is_removed=False,
                ).order_by("-start").first()
            )

        if not gathering:
            now = Utility.now_with_timezone()
            site_type = meet.site_type or (ContentType.objects.get_for_model(meet.assembly) if getattr(meet, 'assembly', None) else None) or ContentType.objects.get_for_model(Meet)
            site_id = str(meet.site_id) if meet.site_id else (str(meet.assembly.id) if getattr(meet, 'assembly', None) else str(meet.id))
            gathering = Gathering.objects.create(
                meet=meet,
                display_name=f"{meet.display_name} {now.strftime('%Y-%m-%d')}",
                start=now,
                finish=now + timedelta(hours=2),
                site_type=site_type,
                site_id=site_id,
            )

        return gathering

    @classmethod
    def _enroll_and_record_attendance(cls, created_attendees, meet, gathering, special_check_in):
        scheduled_cat = (
            Category.objects.filter(id=Attendee.SCHEDULED_CATEGORY).first()
            or Category.objects.filter(id=1).first()
        )
        major_char = meet.major_character or Character.objects.filter(assembly=meet.assembly).first()
        attended_cat = (
            Category.objects.filter(id=Attendee.ATTENDED_CATEGORY).first()
            or Category.objects.filter(type="attendance", display_name__iexact="attended").first()
            or Category.objects.filter(type="attendance").exclude(id=1).first()
        )

        created_attendees_info = []
        for att in created_attendees:
            attending = att.attendings.first()
            if not attending:
                attending = Attending.objects.create(
                    attendee=att,
                    category="auto-created",
                    infos={"created_reason": "fast onboarding"},
                )

            am_infos = {"created_reason": "fast onboarding"}
            if special_check_in:
                am_infos["special"] = {"check_in": special_check_in}

            attendingmeet = AttendingMeet.objects.filter(
                attending=attending,
                meet=meet,
                is_removed=False,
            ).first()
            if not attendingmeet:
                attendingmeet = AttendingMeet.objects.create(
                    attending=attending,
                    meet=meet,
                    character=major_char,
                    category=scheduled_cat,
                    finish=Utility.now_with_timezone() + timedelta(weeks=meet.infos.get('default_attendingmeet_in_weeks', 99999)),
                    infos=am_infos,
                )
            elif special_check_in:
                attendingmeet.infos.setdefault("special", {})["check_in"] = special_check_in
                attendingmeet.save(update_fields=["infos"])

            attendance = None
            if gathering:
                attendance = Attendance.objects.filter(
                    gathering=gathering,
                    attending=attending,
                    is_removed=False,
                ).first()
                if not attendance:
                    attendance = Attendance.objects.create(
                        gathering=gathering,
                        attending=attending,
                        character=attendingmeet.character or major_char,
                        category=attended_cat or Category.objects.get(pk=Attendee.ATTENDED_CATEGORY),
                        start=Utility.now_with_timezone(),
                    )
                elif attendance.category != attended_cat and attended_cat:
                    attendance.category = attended_cat
                    attendance.save(update_fields=["category"])

            created_attendees_info.append({
                "attendee_id": att.id,
                "attendee_name": att.display_label,
                "first_name": att.first_name,
                "last_name": att.last_name,
                "first_name2": att.first_name2,
                "last_name2": att.last_name2,
                "gender": att.gender,
                "actual_birthday": str(att.actual_birthday) if att.actual_birthday else None,
                "estimated_birthday": str(att.estimated_birthday) if att.estimated_birthday else None,
                "attending_id": attending.id,
                "attendingmeet_id": attendingmeet.id,
                "attendance_id": attendance.id if attendance else None,
            })

        return created_attendees_info

    @classmethod
    def fast_onboard(
        cls,
        current_user,
        meet_slug,
        attendees_data=None,
        companions=None,
        unaccompanied=False,
        gathering_id=None,
        kid_data=None,
        parent_data=None,
        target_folk_id=None,
        create_new_folk=False,
    ):
        """
        Fast onboard one or more attendees (and optional companions) into a meet.
        """
        if not current_user or not current_user.is_authenticated or not getattr(current_user, "organization", None):
            raise PermissionDenied("Authentication and organization are required.")

        if not meet_slug:
            raise ValidationError({"meet_slug": "meet_slug is required."})

        # Backward compatibility for kid_data and parent_data
        if attendees_data is None and kid_data is not None:
            attendees_data = kid_data

        if isinstance(attendees_data, dict):
            attendees_data = [attendees_data]
        elif not isinstance(attendees_data, list):
            attendees_data = []

        if not attendees_data:
            raise ValidationError({"attendees_data": "attendees_data list is required."})

        companions_raw = companions
        if not companions_raw and parent_data:
            companions_raw = [parent_data] if isinstance(parent_data, dict) else parent_data
        companions = companions_raw if isinstance(companions_raw, list) else []

        meet = (
            Meet.objects.filter(slug=meet_slug, is_removed=False)
            .select_related("assembly__division__organization", "major_character")
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

        show_attendee_infos = (
            meet.assembly.division.infos.get("show_attendee_infos", {})
            if (meet.assembly and meet.assembly.division and meet.assembly.division.infos)
            else {}
        )
        is_kid_meet = bool(show_attendee_infos.get("infos-grade") or show_attendee_infos.get("grade"))
        show_insurer = bool(show_attendee_infos.get("infos-insurer") or show_attendee_infos.get("insurer"))

        # 1. Validate attendees & companions
        now_date = date.today()
        current_year = now_date.year

        validated_attendees = cls._validate_and_normalize_attendees(
            attendees_data=attendees_data,
            is_kid_meet=is_kid_meet,
            show_insurer=show_insurer,
            current_year=current_year,
            now_date=now_date,
            current_user=current_user,
            meet=meet,
        )

        special_check_in = cls._validate_companions(
            companions=companions,
            is_kid_meet=is_kid_meet,
            unaccompanied=unaccompanied,
        )

        # 2. Atomic database operations
        with transaction.atomic():
            division = meet.assembly.division

            # Upsert attendees
            created_attendees = []
            for item in validated_attendees:
                att = cls._upsert_attendee(
                    att_id=item.get("attendee_id"),
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    first_name2=item["first_name2"],
                    last_name2=item["last_name2"],
                    gender=item["gender"],
                    division=item["division"],
                    infos=item["infos"],
                    actual_birthday=item["actual_birthday"],
                    estimated_birthday=item["estimated_birthday"],
                    current_user=current_user,
                )
                created_attendees.append(att)

            # Upsert companions
            created_companions = []
            if not unaccompanied and companions:
                for c_data in companions:
                    c_first = (c_data.get("first_name") or "").strip() or None
                    c_last = (c_data.get("last_name") or "").strip() or None
                    c_first2 = (c_data.get("first_name2") or "").strip() or None
                    c_last2 = (c_data.get("last_name2") or "").strip() or None
                    c_gender = c_data.get("gender") or GenderEnum.UNSPECIFIED.value
                    c_contacts = cls._extract_contacts(c_data)

                    c_division_id = c_data.get("division_id") or c_data.get("division")
                    c_division = None
                    if c_division_id:
                        c_division = Division.objects.filter(pk=c_division_id, organization=current_user.organization).first()
                    if not c_division:
                        c_division = division

                    c_id = c_data.get("attendee_id") or c_data.get("id")
                    companion_attendee = cls._upsert_attendee(
                        att_id=c_id,
                        first_name=c_first,
                        last_name=c_last,
                        first_name2=c_first2,
                        last_name2=c_last2,
                        gender=c_gender,
                        division=c_division,
                        infos={"contacts": c_contacts} if c_contacts else {},
                        current_user=current_user,
                    )
                    created_companions.append((companion_attendee, c_data))

            # Link folks and relations
            family_folk = None
            if not unaccompanied and (created_companions or len(created_attendees) > 1):
                if is_kid_meet:
                    family_folk = cls._link_kid_meet_folks(
                        created_attendees=created_attendees,
                        created_companions=created_companions,
                        target_folk_id=target_folk_id,
                        create_new_folk=create_new_folk,
                    )
                else:
                    family_folk = cls._link_adult_meet_folks(
                        created_attendees=created_attendees,
                        created_companions=created_companions,
                        target_folk_id=target_folk_id,
                        create_new_folk=create_new_folk,
                    )

            # Resolve gathering
            gathering = cls._resolve_gathering(meet=meet, gathering_id=gathering_id)

            # Enroll and record attendance
            created_attendees_info = cls._enroll_and_record_attendance(
                created_attendees=created_attendees,
                meet=meet,
                gathering=gathering,
                special_check_in=special_check_in,
            )

            primary = created_attendees_info[0]
            comp_objs = [c[0] for c in created_companions]
            return {
                "attendee_id": primary["attendee_id"],
                "attendee_name": primary["attendee_name"],
                "first_name": primary["first_name"],
                "last_name": primary["last_name"],
                "first_name2": primary["first_name2"],
                "last_name2": primary["last_name2"],
                "gender": primary["gender"],
                "actual_birthday": primary["actual_birthday"],
                "estimated_birthday": primary["estimated_birthday"],
                "attending_id": primary["attending_id"],
                "attendingmeet_id": primary["attendingmeet_id"],
                "attendance_id": primary["attendance_id"],
                "gathering_id": gathering.id if gathering else None,
                "warning": special_check_in,
                "parent_id": comp_objs[0].id if comp_objs else None,
                "companion_ids": [c.id for c in comp_objs],
                "is_kid_meet": is_kid_meet,
                "family_folk_id": str(family_folk.id) if family_folk else None,
                "family_folk_name": family_folk.display_name if family_folk else None,
                "attendees": created_attendees_info,
                "attendee_ids": [info["attendee_id"] for info in created_attendees_info],
            }
