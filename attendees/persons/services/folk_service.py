from collections import defaultdict

from django.db.models import OuterRef, Subquery
from django.db.models.functions import Concat

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, Folk, Utility, AttendingMeet


class FolkService:
    @staticmethod
    def families_in_directory(row_limit=26):
        families = []
        index = defaultdict(lambda: {})
        index_list = []
        directory_meet = Meet.objects.get(pk=8)
        member_meet = Meet.objects.get(pk=9)
        attendee_subquery = Attendee.objects.filter(folks=OuterRef('pk'))  # implicitly ordered at FolkAttendee model
        families_in_directory = Folk.objects.annotate(
            householder_name=Concat(
                Subquery(attendee_subquery.values_list('last_name')[:1]),
                Subquery(attendee_subquery.values_list('first_name')[:1]),
            )
        ).filter(
            category=0,  # Family
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
            attendees = family.attendees.filter(deathday=None).exclude(folkattendee__role__title="masked").order_by('folkattendee__display_order')
            parents = attendees.filter(
                folkattendee__role__title__in=['self', 'spouse', 'husband', 'wife']  # no father/mother-in-law
            )
            attrs['household_last_name'] = attendees.first().last_name

            phone1 = parents.first() and parents.first().infos.get('contacts', {}).get('phone1')  # only phone1 published in directory
            phone2 = None
            if phone1:
                attrs['phone1'] = Utility.phone_number_formatter(phone1)
            email1 = parents.first() and parents.first().infos.get('contacts', {}).get('email1')  # only email1 published in directory
            if email1:
                attrs['email1'] = email1

            is_householder_member = AttendingMeet.check_participation_of(attendees.first(), member_meet)
            householder_title = f'{attendees.first().last_name}, {attendees.first().first_name}{"*" if is_householder_member else ""}'
            name2_title = f'{attendees.first().name2()}'
            if len(parents) > 1:
                name2_title += f' {parents[1].name2()}'
                is_parent1_member = AttendingMeet.check_participation_of(parents[1], member_meet)
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
                if family_address.extra:
                    address_line1 += f' {family_address.extra}'
                attrs['address_line1'] = address_line1
                attrs['address_line2'] = address_line2

                index[family_address.locality.name][f'{householder_title} {name2_title}'.strip()] = Utility.phone_number_formatter(phone1 or phone2)

            attendees_attr = []
            for attendee in attendees:
                is_attendee_member = AttendingMeet.check_participation_of(attendee, member_meet)
                attendees_attr.append({
                    'first_name': f'{attendee.first_name}{"*" if is_attendee_member else ""}',
                    'name2': attendee.name2(),
                    'photo_url': attendee.photo and attendee.photo.url,
                    'is_member': AttendingMeet.check_participation_of(attendee, member_meet),
                })
            attrs['attendees'] = attendees_attr

            families.append(attrs)

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
