from collections import defaultdict
from datetime import datetime, timezone
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Concat

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, Folk, Utility, AttendingMeet


class FolkService:
    @staticmethod
    def families_in_directory(directory_meet_id, member_meet_id, row_limit=26, targeting_attendee_id=None, divisions=[]):
        """
        It generates data for printing/previewing single or participating families in chosen divisions.
        The output includes indexes (families grouped in cities) and families (header and family member contacts).
        An attendee will NOT be unique if it belongs to multiple families.  Folkattendees role of masked won't be shown.

        It has no scope checks, so callers need to limit the scope by passing targeting_attendee_id or divisions.
        Phones/emails will be empty when there's no parents. For kids-only families please assign 'self' role to the first kid to show its phone/email
        """
        families = []
        index = defaultdict(lambda: {})
        index_list = []
        directory_meet = Meet.objects.filter(pk=directory_meet_id).first()
        member_meet = Meet.objects.filter(pk=member_meet_id).first()
        targeting_families = Attendee.objects.get(pk=targeting_attendee_id).folks if targeting_attendee_id else Folk.objects.filter(division__in=divisions).prefetch_related('attendees', 'folkattendee_set')

        if directory_meet:
            attendee_subquery = Attendee.objects.filter(folks=OuterRef('pk'))  # implicitly ordered at FolkAttendee model
            families_in_directory = targeting_families.annotate(
                householder_name=Concat(
                    Subquery(attendee_subquery.values_list('last_name')[:1]),
                    Subquery(attendee_subquery.values_list('first_name')[:1]),
                )
            ).filter(
                category=Attendee.FAMILY_CATEGORY,
                is_removed=False,
                infos__print_directory=True,
                attendees__in=Attendee.objects.filter(
                    attendings__in=directory_meet.attendings.filter(
                        attendingmeet__finish__gte=Utility.now_with_timezone()
                    ),
                    deathday=None,
                    is_removed=False,
                ),
            ).distinct().order_by('householder_name')

            for family in families_in_directory:
                attrs = {}
                attendees = family.attendees.filter(
                    deathday=None,
                    attendings__in=directory_meet.attendings.filter(
                        attendingmeet__finish__gte=Utility.now_with_timezone()
                    ),  # only for attendees join the meet
                ).exclude(
                    folkattendee__role__title="masked",  # for joined attendees not to be shown in certain families
                ).exclude(
                    folkattendee__finish__lte=datetime.now(timezone.utc)
                ).distinct().order_by('folkattendee__display_order')

                if attendees:
                    parents = attendees.filter(
                        folkattendee__role__title__in=['self', 'spouse', 'husband', 'wife', 'father', 'mother', 'parent']  # no father/mother-in-law
                    )
                    attrs['household_last_name'] = attendees.first().last_name

                    if parents:
                        phone1 = parents.first() and parents.first().infos.get('contacts', {}).get('phone1')  # only phone1 published in directory
                        phone2 = None
                        if phone1:
                            attrs['phone1'] = Utility.phone_number_formatter(phone1)
                        email1 = parents.first() and parents.first().infos.get('contacts', {}).get('email1')  # only email1 published in directory
                        if email1:
                            attrs['email1'] = email1

                    is_householder_member = member_meet and AttendingMeet.check_participation_of(attendees.first(), member_meet)
                    householder_title = f'{attendees.first().last_name}, {attendees.first().first_name}{"*" if is_householder_member else ""}'
                    name2_title = f'{attendees.first().name2()}'
                    if len(parents) > 1:
                        name2_title += f' {parents[1].name2()}'
                        is_parent1_member = member_meet and AttendingMeet.check_participation_of(parents[1], member_meet)
                        householder_title += f' & {parents[1].first_name}{"*" if is_parent1_member else ""}'
                        phone2 = parents[1].infos.get('contacts', {}).get('phone1')  # only phone1 published in directory
                        if phone2 and phone1 != phone2:
                            attrs['phone2'] = Utility.phone_number_formatter(phone2)
                        email2 = parents[1].infos.get('contacts', {}).get('email1')  # only email1 published in directory
                        if email2 and email1 != email2:
                            attrs['email2'] = email2
                    attrs['household_title'] = householder_title

                    family_address = family.places.first() and family.places.first().address  # implicitly ordered by display_order of place
                    if family_address:
                        address_line1 = f'{family_address.street_number} {family_address.route}'
                        address_line2 = f'{family_address.locality.name}, {family_address.locality.state.code} {family_address.locality.postal_code}'
                        attrs['address_link'] = f'{address_line1}+{address_line2}'.replace(' ',  '+')
                        if family_address.extra:
                            address_line1 += f' {family_address.extra}'
                        attrs['address_line1'] = address_line1
                        attrs['address_line2'] = address_line2

                        index[family_address.locality.name][f'{householder_title} {name2_title}'.strip()] = Utility.phone_number_formatter(phone1 or phone2)

                    attendees_attr = []
                    for attendee in attendees:
                        is_attendee_member = member_meet and AttendingMeet.check_participation_of(attendee, member_meet)
                        attendees_attr.append({
                            'id': attendee.id,
                            'first_name': f'{attendee.first_name}{"*" if is_attendee_member else ""}',
                            'name2': attendee.name2(),
                            'photo_url': attendee.photo and attendee.photo.url,
                            'is_member': member_meet and AttendingMeet.check_participation_of(attendee, member_meet),
                        })
                    attrs['attendees'] = attendees_attr

                    families.append(attrs)

            if targeting_attendee_id is None:
                for town_name, family_rows in sorted(index.items()):
                    index_list.append({'BREAKER': 'LINE'})
                    if len(index_list) % row_limit < 1:
                        index_list.append({'BREAKER': 'PAGE'})

                    index_list.append({'TOWN_NAME': town_name})
                    if len(index_list) % row_limit < 1:
                        index_list.append({'BREAKER': 'PAGE'})

                    for title, number in sorted(index[town_name].items()):
                        index_list.append({title: number})
                        if len(index_list) % row_limit < 1:
                            index_list.append({'BREAKER': 'PAGE'})

        return index_list, families

    @staticmethod
    def families_in_participations(meet_slug, user_organization, division_slugs):
        """
        Generates printing data for unique attendingmeet of a meet limited by user_organization and divisions, grouped
        by families.  If an Attendee belongs to many families, only 1) lowest display order 2) the last created
        folkattendee will be shown.  Attendees will NOT be shown if the category of the attendingmeet is "paused".
        For cache computation final results intentionally contains empty families so template need to filter them out.
        It does NOT provide attendee counting, as view/template does https://stackoverflow.com/a/34059709/4257237
        """
        families = {}   # {family_pk: {family_name: "AAA", families: {attendee_pk: {first_name: 'XYZ', name2: 'ABC', rank: last_folkattendee_display_order, created_at: last_folkattendee_created_at}}}}
        attendees_cache = {}  # {attendee_pk: {last_family_pk: last_family_pk, rank: last_folkattendee_display_order, created_at: last_folkattendee_created_at}}
        meet = Meet.objects.filter(slug=meet_slug, assembly__division__organization=user_organization).first()
        if meet:
            attendee_subquery = Attendee.objects.filter(folks=OuterRef('pk'))  # implicitly ordered at FolkAttendee model
            families_in_directory = Folk.objects.filter(
                division__organization=user_organization,
            ).prefetch_related('attendees', 'folkattendee_set').annotate(
                householder_last_name=Subquery(attendee_subquery.values_list('last_name')[:1]),
                householder_first_name=Subquery(attendee_subquery.values_list('first_name')[:1]),
            ).filter(
                category=Attendee.FAMILY_CATEGORY,
                is_removed=False,
                attendees__in=Attendee.objects.filter(
                    division__slug__in=division_slugs,
                    attendings__in=meet.attendings.filter(
                        attendingmeet__finish__gte=Utility.now_with_timezone()
                    ),
                    deathday=None,
                    is_removed=False,
                ),
            ).distinct().order_by('householder_last_name', 'householder_first_name')

            for family in families_in_directory:
                attendee_candidates = family.attendees.filter(
                    division__slug__in=division_slugs,
                    deathday=None,
                    attendings__in=meet.attendings.filter(
                        attendingmeet__finish__gte=Utility.now_with_timezone()
                    ),  # only for attendees join the meet
                ).exclude(
                    folkattendee__role__title=Attendee.PAUSED_CATEGORY,  # for joined attendees not to be shown temporarily
                ).exclude(
                    folkattendee__finish__lte=datetime.now(timezone.utc)
                ).distinct().order_by('folkattendee__display_order').values(
                    'id', 'first_name', 'last_name', 'first_name2', 'last_name2', 'folkattendee__display_order', 'created', 'division__infos__acronym'
                )

                family_attrs = {"families": {}, 'family_name': 'no last names!'}

                if attendee_candidates[0]:
                    family_attrs['family_name'] = attendee_candidates[0].get('last_name') or attendee_candidates[0].get('last_name2')

                for attendee in attendee_candidates:
                    attendee_id = attendee.get('id')
                    attendee_last_record = attendees_cache.get(attendee_id)
                    if attendee_last_record:
                        current_rank = attendee.get('folkattendee__display_order')
                        last_rank = attendee_last_record.get('rank')
                        current_created = attendee.get('created')
                        last_created = attendee_last_record.get('created')
                        last_family = attendee_last_record.get('family_id')
                        if current_rank > last_rank or (current_rank == last_rank and current_created < last_created):
                            continue  # unique by 1) lowest display order 2) the last created folkattendee
                        else:  # current one will replace last one
                            del families[last_family]['families'][attendee_id]

                    attendees_cache[attendee_id] = {
                        'rank': attendee.get('folkattendee__display_order'),
                        'created': attendee.get('created'),
                        'family_id': family.id,
                    }

                    family_attrs['families'][attendee_id] = {
                        'division': attendee.get('division__infos__acronym'),
                        'first_name': attendee.get('first_name'),
                        'first_name2': attendee.get('first_name2'),
                        'last_name2': attendee.get('last_name2'),
                    }

                families[family.id] = family_attrs

        return families.values()  # is list() necessary?

    @staticmethod
    def destroy_with_associations(folk, attendee):
        """
        No permission check.
        if family have more than one FamilyAttendees:
            only delete the FamilyAttendees, and reset non-blood Relationships. Places and Family still remained
        if family have only one FamilyAttendees (regardless which FamilyAttendees):
            delete family, places, FamilyAttendees and reset non-blood Relationships

        :param folk: a folk object
        :param attendee: an attendee object, whose name will be removed from family display_name
        :return: None
        """

        if (
            folk.folkattendee_set.count() < 2
            and folk.folkattendee_set.first() == attendee
        ):
            # Relationship.objects.filter(in_family=folk.id, relation__consanguinity=False, is_removed=False).delete()
            # Relationship.objects.filter(in_family=folk.id, relation__consanguinity=True, is_removed=False).update(in_family=None)
            folk.places.filter(is_removed=False).delete()
            folk.folkattendee_set.filter(is_removed=False).delete()
            folk.delete()

        else:
            family_name = folk.display_name
            for attendee_name in attendee.all_names():
                if attendee_name is not None:
                    family_name.replace(attendee_name, "")
            folk.display_name = family_name
            folk.save()
            # Relationship.objects.filter(from_attendee=attendee, in_family=folk.id, relation__consanguinity=False, is_removed=False).delete()
            folk.folkattendee_set.filter(attendee=attendee, is_removed=False).delete()
