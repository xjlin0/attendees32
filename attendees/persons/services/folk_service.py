from collections import defaultdict
from datetime import datetime, timezone
from django.contrib.postgres.aggregates.general import  ArrayAgg
from django.db.models import Max, OuterRef, Q, Subquery

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
            attendee_subquery = Attendee.objects.filter(
                attendings__attendingmeet__is_removed=False,
                attendings__attendingmeet__meet=directory_meet,
                attendings__attendingmeet__finish__gte=Utility.now_with_timezone(),
                folks=OuterRef('pk'),
                deathday=None,
                is_removed=False,
            ).order_by('folkattendee__display_order')

            families_in_directory = targeting_families.annotate(
                householder_last_name=Subquery(attendee_subquery.values_list('last_name')[:1]),
                householder_first_name=Subquery(attendee_subquery.values_list('first_name')[:1]),
                householder_first_name2=Subquery(attendee_subquery.values_list('first_name2')[:1]),
            ).filter(
                category=Attendee.FAMILY_CATEGORY,
                is_removed=False,
                infos__print_directory=True,
                attendees__in=Attendee.objects.filter(
                    attendings__in=directory_meet.attendings.filter(
                        attendingmeet__is_removed=False,
                        attendingmeet__finish__gte=Utility.now_with_timezone()
                    ),
                    deathday=None,
                    is_removed=False,
                ),
            ).distinct().order_by('householder_last_name', 'householder_first_name', 'householder_first_name2')

            for family in families_in_directory:
                attrs = {}
                attendees = family.attendees.filter(
                    deathday=None,
                    attendings__in=directory_meet.attendings.filter(
                        attendingmeet__is_removed=False,
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
                for i, (town_name, family_rows) in enumerate(sorted(index.items())):
                    if i > 0:  # No line breaks before the first town
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
    def families_in_participations(meet_slug, user_organization, show_paused, division_slugs):
        """
        Returns a list of not-paused unique attendingmeet of a meet limited by user_organization and divisions, grouped
        by families for print. If an Attendee belongs to many families, only 1) lowest display order 2) the last created
        folkattendee will be shown.  Attendees will NOT be shown if the category of the attendingmeet is "paused".
        For cache computation final results may contain empty families so template need to filter them out. It does
        NOT provide attendee counting, as view/template does css-counter or https://stackoverflow.com/a/34059709/4257237
        """
        families = {}   # {family_pk: {family_name: "AAA", families: {attendee_pk: {first_name: 'XYZ', name2: 'ABC', rank: last_folkattendee_display_order, created_at: last_folkattendee_created_at}}}}
        attendees_cache = {}  # {attendee_pk: {last_family_pk: last_family_pk, rank: last_folkattendee_display_order, created_at: last_folkattendee_created_at}}
        meet = Meet.objects.filter(slug=meet_slug, assembly__division__organization=user_organization).first()
        if meet:
            original_meets_attendings = meet.attendings.filter(
                                        attendingmeet__is_removed=False,
                                        attendingmeet__finish__gte=Utility.now_with_timezone(),
                                    )
            meets_attendings = original_meets_attendings if show_paused else original_meets_attendings.exclude(
                                        attendingmeet__category=Attendee.PAUSED_CATEGORY,
                                    )
            original_attendee_subquery = Attendee.objects.filter(
                attendings__attendingmeet__is_removed=False,
                attendings__attendingmeet__meet=meet,
                attendings__attendingmeet__finish__gte=Utility.now_with_timezone(),
                folks=OuterRef('pk'),
                deathday=None,
                is_removed=False,
            ).order_by('folkattendee__display_order')

            attendee_subquery = original_attendee_subquery if show_paused else original_attendee_subquery.exclude(
                attendings__attendingmeet__category=Attendee.PAUSED_CATEGORY,
            )

            families_in_directory = Folk.objects.filter(
                division__organization=user_organization,
            ).prefetch_related('folkattendee_set', 'attendees').annotate(
                householder_last_name=Subquery(attendee_subquery.values_list('last_name')[:1]),
                householder_first_name=Subquery(attendee_subquery.values_list('first_name')[:1]),
                householder_first_name2=Subquery(attendee_subquery.values_list('first_name2')[:1]),
            ).filter(
                category=Attendee.FAMILY_CATEGORY,
                is_removed=False,
                attendees__in=Attendee.objects.filter(
                    division__slug__in=division_slugs,
                    attendings__in=meets_attendings,
                    deathday=None,
                    is_removed=False,
                ),
            ).distinct().order_by('householder_last_name', 'householder_first_name', 'householder_first_name2')

            for family in families_in_directory:
                candidates_qs = family.attendees.select_related('division', 'attendings', 'folkattendee_set').filter(
                    division__slug__in=division_slugs,
                    deathday=None,
                    attendings__in=meets_attendings,
                ).exclude(
                    folkattendee__finish__lte=datetime.now(timezone.utc)
                )

                attendee_candidates = candidates_qs.distinct().order_by('folkattendee__display_order').values(
                    'id', 'first_name', 'last_name', 'first_name2', 'last_name2', 'folkattendee__display_order', 'created', 'division__infos__acronym'
                ).annotate(
                    attendingmeet_id=Max('attendings__attendingmeet__id', filter=Q(attendings__attendingmeet__meet=meet)),
                    attendingmeet_category=Max('attendings__attendingmeet__category', filter=Q(attendings__attendingmeet__meet=meet)),
                    attendingmeet_note=ArrayAgg('attendings__attendingmeet__infos__note',
                                                 filter=(Q(attendings__attendingmeet__meet=meet) & Q(attendings__attendingmeet__infos__note__isnull=False)),
                                                 distinct=True),
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
                            if len(families[last_family]['families']) < 1:
                                del families[last_family]
                            elif str(attendee_id) == families[last_family].get('first_attendee_id'):
                                first_attendee = next(iter(families[last_family]['families'].items()))[1]
                                families[last_family]['first_attendee_id'] = str(first_attendee.get('id', ''))

                    attendees_cache[attendee_id] = {
                        'rank': attendee.get('folkattendee__display_order'),
                        'created': attendee.get('created'),
                        'family_id': family.id,
                    }

                    family_attrs['families'][attendee_id] = {
                        'id': attendee.get('id'),
                        'first_name': attendee.get('first_name'),
                        'first_name2': attendee.get('first_name2'),
                        'last_name2': attendee.get('last_name2'),
                        'division': attendee.get('division__infos__acronym'),
                        'attendingmeet_id': attendee.get('attendingmeet_id'),
                        'attendingmeet_category': attendee.get('attendingmeet_category'),
                        'attendingmeet_note': ''.join(attendee.get('attendingmeet_note')),
                        'paused': attendee.get('attendingmeet_category') == Attendee.PAUSED_CATEGORY,
                    }

                if len(family_attrs['families']) > 0:
                    first_attendee = next(iter(family_attrs['families'].items()))[1]
                    family_attrs['first_attendee_id'] = str(first_attendee.get('id', ''))
                    families[family.id] = family_attrs

        return families.values()

    @staticmethod
    def folk_addresses_in_participations(meet_slug, user_organization, show_paused, division_slugs):
        """

        Because attendee may be in multiple families and envelopes only needs the lowest display order ones, iteration
        of attendee is required.
        It's mostly copy from families_in_participations.
        """
        families = {}   # {family_pk: {family_name: "AAA", families: {attendee_pk: {first_name: 'XYZ', name2: 'ABC', rank: last_folkattendee_display_order, created_at: last_folkattendee_created_at}}}}
        attendees_cache = {}  # {attendee_pk: {last_family_pk: last_family_pk, rank: last_folkattendee_display_order, created_at: last_folkattendee_created_at}}
        meet = Meet.objects.filter(slug=meet_slug, assembly__division__organization=user_organization).first()
        if meet:
            original_meets_attendings = meet.attendings.filter(
                                        attendingmeet__is_removed=False,
                                        attendingmeet__finish__gte=Utility.now_with_timezone(),
                                    )
            meets_attendings = original_meets_attendings if show_paused else original_meets_attendings.exclude(
                                        attendingmeet__category=Attendee.PAUSED_CATEGORY,
                                    )
            original_attendee_subquery = Attendee.objects.filter(
                attendings__attendingmeet__is_removed=False,
                attendings__attendingmeet__meet=meet,
                attendings__attendingmeet__finish__gte=Utility.now_with_timezone(),
                folks=OuterRef('pk'),
                is_removed=False,
                deathday=None,
            ).order_by('folkattendee__display_order')

            attendee_subquery = original_attendee_subquery if show_paused else original_attendee_subquery.exclude(
                attendings__attendingmeet__category=Attendee.PAUSED_CATEGORY,
            )

            families_in_directory = Folk.objects.filter(
                division__organization=user_organization,
            ).prefetch_related('folkattendee_set', 'attendees', 'places').annotate(
                householder_last_name=Subquery(attendee_subquery.values_list('last_name')[:1]),
                householder_first_name=Subquery(attendee_subquery.values_list('first_name')[:1]),
                householder_first_name2=Subquery(attendee_subquery.values_list('first_name2')[:1]),
            ).filter(
                category=Attendee.FAMILY_CATEGORY,
                is_removed=False,
                attendees__in=Attendee.objects.filter(
                    division__slug__in=division_slugs,
                    attendings__in=meets_attendings,
                    deathday=None,
                    is_removed=False,
                ),
            ).distinct().order_by('householder_last_name', 'householder_first_name', 'householder_first_name2')

            for family in families_in_directory:
                candidates_qs = family.attendees.select_related('division', 'attendings', 'folkattendee_set').filter(
                    division__slug__in=division_slugs,
                    deathday=None,
                    attendings__in=meets_attendings,
                ).exclude(
                    folkattendee__finish__lte=datetime.now(timezone.utc)
                )

                attendee_candidates = candidates_qs.distinct().order_by('folkattendee__display_order').values(
                    'id', 'first_name', 'last_name', 'first_name2', 'last_name2', 'folkattendee__display_order', 'created',
                ).annotate(
                    attendingmeet_category=Max('attendings__attendingmeet__category', filter=Q(attendings__attendingmeet__meet=meet)),
                )

                family_attrs = {'families': {}}

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
                            families_count = len(families[last_family]['families'])
                            if families_count < 1:
                                del families[last_family]
                            else:
                                families_iter = iter(families[last_family]['families'].items())
                                home_head = next(families_iter)[1]
                                families[last_family]['recipient_attendee_id'] = str(home_head.get('id', ''))
                                families[last_family]['recipient_paused'] = home_head.get('paused')
                                families[last_family]['recipient_name'] = FolkService.get_recipient(home_head, None if families_count < 2 else next(families_iter)[1])

                    attendees_cache[attendee_id] = {
                        'rank': attendee.get('folkattendee__display_order'),
                        'created': attendee.get('created'),
                        'family_id': family.id,
                    }

                    family_attrs['families'][attendee_id] = {
                        'id': attendee.get('id'),
                        'first_name': attendee.get('first_name') or '',
                        'first_name2': attendee.get('first_name2') or '',
                        'last_name': attendee.get('last_name') or '',
                        'last_name2': attendee.get('last_name2') or '',
                        'paused': attendee.get('attendingmeet_category') == Attendee.PAUSED_CATEGORY,
                    }

                if len(family_attrs['families']) > 0:
                    families_iter = iter(family_attrs['families'].items())
                    home_head = next(families_iter)[1]

                    family_attrs['recipient_name'] = FolkService.get_recipient(home_head, None)
                    family_attrs['recipient_attendee_id'] = str(home_head.get('id', ''))
                    family_attrs['recipient_paused'] = home_head.get('paused')
                    folk_place = family.places.first()

                    if len(family_attrs['families']) > 1:
                        family_attrs['recipient_name'] = FolkService.get_recipient(home_head, next(families_iter)[1])
                    if folk_place:
                        address = family.places.first().address
                        if address:
                            family_attrs['address_line1'] = f"{address.street_number} {address.route} {address.extra or ''}".strip()
                            family_attrs['address_line2'] = f"{address.locality.name}, {address.locality.state.code} {address.locality.postal_code or ''}".strip()

                    families[family.id] = family_attrs

        return families.values()

    @staticmethod
    def get_recipient(home_head, spouse):
        home_head_name2 = f"{home_head.get('last_name2', '')}{home_head.get('first_name2', '')}".strip()
        if spouse:
            spouse_name2 = f"{spouse.get('last_name2', '')}{spouse.get('first_name2', '')}".strip()
            both_name = f"{' & '.join([i for i in [home_head.get('first_name', ''), spouse.get('first_name', '')] if i != ''])} {home_head.get('last_name', '')}"
            both_name2 = f"{home_head_name2} {spouse_name2}".strip()
            return f"{both_name} {both_name2}".strip()
        else:
            home_head_name = f"{home_head.get('first_name', '')} {home_head.get('last_name', '')}".strip()
            return f"{home_head_name} {home_head_name2}".strip()

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
