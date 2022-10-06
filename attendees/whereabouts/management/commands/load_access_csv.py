import csv, os, pytz, re, sys, json
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from urllib import parse
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from address.models import Locality, State, Address

from attendees.occasions.models import Assembly, Meet, Gathering, Attendance, Team, Character
from attendees.persons.models import Utility, GenderEnum, Folk, Relation, Attendee, FolkAttendee, \
    Registration, Attending, AttendingMeet, Past, Category
from attendees.users.admin import User
from attendees.whereabouts.models import Place, Division


class Command(BaseCommand):
    help = "Update extra content type columns after migrations and content type data seeded, no arguments needed"

    def import_household_people_address(
            self,
            household_csv,
            people_csv,
            address_csv,
            division1_slug,
            division2_slug,
            division3_slug,
            data_assembly_slug,
            member_meet_slug,
            directory_meet_slug,
            baptized_meet_slug,
            roaster_meet1_slug,
            roaster_meet2_slug,
            believer_meet_slug,
            rock_meet_slug,
            foot_meet_slug,
        ):
        """
        Entry function of entire importer, it execute importers in sequence and print out results.
        :param household_csv: an existing file object of household with headers, from MS Access
        :param people_csv: an existing file object of household with headers, from MS Access
        :param address_csv: an existing file object of household with headers, from MS Access
        :param division1_slug: key of division 1  # ch
        :param division2_slug: key of division 2  # en
        :param division3_slug: key of division 3  # kid
        :param data_assembly_slug: key of data_assembly
        :param member_meet_slug: key of member_gathering
        :param directory_meet_slug: key of directory_gathering
        :param baptized_meet_slug: key of baptized_meet_slug
        :param roaster_meet1_slug: key of roaster_meet1_slug
        :param roaster_meet2_slug: key of roaster_meet2_slug
        :param believer_meet_slug: key of believer_meet_slug
        :param rock_meet_slug: key of rock_meet_slug
        :param foot_meet_slug: key of foot_meet_slug
        :return: None, but print out importing status and write to Attendees db (create or update)
        """
        if User.objects.count() < 1:
            raise Exception("\n\nSorry, no user exits, did superuser created?")
        california = State.objects.filter(code='CA').first()
        if not california:
            raise Exception("\n\nSorry, California not imported, did db_seed.json loaded?")

        self.stdout.write("\n\n\nStarting import_household_people_address ...\n\n")
        households = csv.DictReader(household_csv)
        peoples = csv.DictReader(people_csv)
        addresses = csv.DictReader(address_csv)
        division1 = Division.objects.get(slug=division1_slug)
        division2 = Division.objects.get(slug=division2_slug)
        roaster_meet1 = Meet.objects.select_related('major_character').get(slug=roaster_meet1_slug)
        roaster_meet2 = Meet.objects.select_related('major_character').get(slug=roaster_meet2_slug)
        division_converter = {
            division1.id: {
                "meet": roaster_meet2,
                "gathering": Gathering.objects.filter(meet=roaster_meet2).last(),
            },
            division2.id: {  # e
                "meet": roaster_meet1,  # e
                "gathering": Gathering.objects.filter(meet=roaster_meet1).last(),
            },
        }

        try:
            initial_time = datetime.utcnow()
            initial_contact_count = Place.objects.count()
            initial_family_count = Folk.objects.filter(category=Attendee.FAMILY_CATEGORY).count()
            initial_attendee_count = Attendee.objects.count()
            initial_families_count = FolkAttendee.objects.count()
            upserted_address_count = self.import_addresses(addresses, california, division1_slug)
            upserted_household_id_count = self.import_households(households, division1, division2)
            upserted_attendee_count, photo_import_results = self.import_attendees(peoples, rock_meet_slug, foot_meet_slug, division3_slug, data_assembly_slug, member_meet_slug, baptized_meet_slug, division_converter, believer_meet_slug)
            # upserted_address_count, upserted_household_id_count, upserted_attendee_count, photo_import_results = 1, 1, 1, []
            if upserted_address_count and upserted_household_id_count and upserted_attendee_count:
                upserted_relationship_count = self.reprocess_directory_emails_and_family_roles( division3_slug, rock_meet_slug, foot_meet_slug, directory_meet_slug)
                self.stdout.write("\n\nProcessing results of importing/updating Access export csv files:\n")
                self.stdout.write(f'Number of address successfully imported/updated: {upserted_address_count}')
                self.stdout.write(f"Initial contact count: {initial_contact_count}. final contact count: {Place.objects.count()}.\n")

                self.stdout.write(f'Number of households successfully imported/updated: {upserted_household_id_count}')
                self.stdout.write(f'Initial family count: {initial_family_count}. final family count: {Folk.objects.filter(category=Attendee.FAMILY_CATEGORY).count()}', ending="\n\n")

                place_with_family_count = Place.objects.filter(content_type=ContentType.objects.get_for_model(Folk)).count()
                self.stdout.write(f'Number of place(address) successfully associated with family (originally 0): {place_with_family_count}')

                self.stdout.write(f'Number of people successfully imported/updated: {upserted_attendee_count}')
                self.stdout.write(f'Initial attendee count: {initial_attendee_count}. final attendee count: {Attendee.objects.count()}')

                self.stdout.write(f'Number of relationship successfully imported/updated: {upserted_relationship_count}')
                self.stdout.write(f'Initial relationship count: {initial_families_count}. final relationship count: {FolkAttendee.objects.count()}')

                number_of_attendees_with_photo_assigned = len(photo_import_results)
                attendees_missing_photos = list(filter(None.__ne__, photo_import_results))
                self.stdout.write(f"\nPhoto import results: Out of {number_of_attendees_with_photo_assigned} attendees assigned with photos, {len(attendees_missing_photos)} were missing photo files:\n")
                for photo in attendees_missing_photos:
                    self.stdout.write(photo)

                time_taken = (datetime.utcnow() - initial_time).total_seconds()
                self.stdout.write(f'Importing/updating Access CSV is now done, seconds taken: {time_taken}')
                self.stdout.write('Please manually fix the address not in USA!')
            else:
                self.stdout.write('Importing/updating address or household or attendee error, result count does not exist!')
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.stdout.write(f'Cannot proceed import_household_people_address, reason: {e} at line: {exc_tb.tb_lineno}')

    def spell_correcter(self, town_name):
        correcter = {
            'Hayard': 'Hayward',
            'Haywardy': 'Hayward',
            'Neward': 'Newark',
            'Union  City': 'Union City',
        }
        return correcter[town_name] if town_name in correcter else town_name

    # Todo: Add created by notes in every instance in notes/infos
    def import_addresses(self, addresses, california, division1_slug):
        """
        Importer of addresses from MS Access.
        :param addresses: file content of address accessible by headers, from MS Access
        :param california: Californis is the default state
        :return: successfully processed address count, also print out importing status and write to Attendees db (create or update)
        """

        self.stdout.write("\n\nRunning import_addresses:\n")
        successfully_processed_count = 0  # addresses.line_num always advances despite of processing success
        address_content_type = ContentType.objects.get_for_model(Address)  # ContentType.objects.get(model='address')
        organization = Division.objects.get(slug=division1_slug).organization
        for address_dict in addresses:
            try:
                self.stdout.write('.', ending='')
                address_id = Utility.presence(address_dict.get('AddressID'))  # str
                state = Utility.presence(address_dict.get('State'))
                street = Utility.presence(address_dict.get('Street'))
                city = Utility.presence(address_dict.get('City'))
                zip_code = Utility.presence(address_dict.get('Zip'), '')  # Locality.postal_code allow blank but not null

                if address_id and state == california.code:  # Only process US data
                    address = {
                        'type': 'city',
                        'locality': self.spell_correcter(Utility.presence(address_dict.get('City'))),
                        'postal_code': zip_code,
                        'state': california.name,
                        'state_code': california.code,
                        'country': 'USA',
                        'country_code': 'US',
                        'raw': f"{city}, {state} {zip_code}".strip(),
                    }
                    if street:
                        possible_extras = re.findall('((?i)(apt|unit|#| \D{1}\d+).+)$', street)  # Get extra info such as Apt#
                        address_extra = possible_extras[0][0].strip() if possible_extras else ''
                        street_strs = street.replace(address_extra, '').strip().strip(',').split(' ')
                        address['street_number'] = street_strs[0]
                        address['route'] = ' '.join(street_strs[1:])
                        address['extra'] = Utility.presence(address_extra)
                        address['raw'] = f"{street}, {address['raw']}"

                    contact_values = {
                        'address': address,
                        'organization': organization,
                        'infos': {
                            **Utility.default_infos(),
                            'access_address_id': address_id,
                            'access_address_values': address_dict,
                        }
                    }
                    existing_places = Place.objects.filter(infos__access_address_id=address_id)  # multiple households can share an address
                    if existing_places:
                        for place in existing_places:
                            place.infos = contact_values.get('infos')
                            address = place.address
                            address.street_number = contact_values.get('address', {}).get('street_number')
                            address.route = contact_values.get('address', {}).get('route')
                            address.raw = contact_values.get('address', {}).get('raw')
                            potential_new_local = Locality.objects.filter(postal_code=contact_values.get('address', {}).get('postal_code'), name=contact_values.get('address', {}).get('locality')).first()
                            if potential_new_local:
                                address.locality = potential_new_local
                            address.save()
                            place.save()
                    else:
                        Place.objects.update_or_create(
                            infos__access_address_id=address_id,  # str
                            defaults={
                                **contact_values,
                                'content_type': address_content_type,
                                'object_id': str(address_id),  # will update later.  Remember some address are duplicated
                            }
                        )

                else:
                    self.stdout.write(f'Is the address completed or in California? address not good for processing: {address_dict}')
                successfully_processed_count += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.stdout.write(f'While importing/updating address: {address_dict}')
                self.stdout.write(f'An error occurred and cannot proceed import_addresses(), reason: {e} at line: {exc_tb.tb_lineno}.')
        self.stdout.write('done!')
        return successfully_processed_count

    def import_households(self, households, division1, division2):
        """
        Importer of households from MS Access, also update display name and telephone number of Place.
        :param households: file content of households accessible by headers, from MS Access
        :param division1_slug: slug of division 1  # ch
        :param division2_slug: slug of division 2  # en
        :return: successfully processed family count, also print out importing status and write FamilyAddress to Attendees db (create or update)
        """
        default_division = Division.objects.first()
        division_converter = {
            'CH': division1,
            'EN': division2,
        }
        folk_content_type = ContentType.objects.get_for_model(Folk)
        self.stdout.write("\n\nRunning import_households:\n")
        successfully_processed_count = 0  # households.line_num always advances despite of processing success
        pdt = pytz.timezone('America/Los_Angeles')
        family_category = Category.objects.get(pk=Attendee.FAMILY_CATEGORY)
        long_time_ago = pdt.localize(datetime(1800, 1, 1), is_dst=None)
        for index, household in enumerate(households, start=1):
            try:
                self.stdout.write('.', ending='')
                household_id = Utility.presence(household.get('HouseholdID'))
                address_id = Utility.presence(household.get('AddressID'))  # str
                display_name = Utility.presence(household.get('HousholdLN', '') + ' ' + household.get('HousholdFN', '') + ' ' + household.get('SpouseFN', '')) or 'household_id: ' + household_id
                congregation = Utility.presence(household.get('Congregation'))
                print_directory = Utility.is_truthy(Utility.presence(household.get('PrintDir')))

                if household_id:
                    household_values = {
                        'created': long_time_ago + timedelta(index),  # bypass Todo: 20210516 order by attendee's family attendee display_order
                        'display_name': display_name,
                        'division': default_division,
                        'category': family_category,
                        'infos': {
                            'print_directory': print_directory,
                            'access_household_id': household_id,
                            'access_household_values': household,
                            'last_update': Utility.presence(household.get('LastUpdate')),
                            'contacts': {},
                        }
                    }

                    if congregation:
                        division = division_converter.get(congregation)
                        if division:
                            household_values['division'] = division
    
                    folk, folk_created = Folk.objects.update_or_create(
                        infos__access_household_id=household_id,
                        defaults=household_values
                    )

                    if address_id:
                        phone1 = Utility.presence(household.get('HouseholdPhone'))
                        phone2 = Utility.presence(household.get('HouseholdFax'))
                        # old_contact = Place.objects.filter(infos__access_address_id=address_id).first()
                        # address = old_contact.address if old_contact else None
                        saved_place = folk.places.first() or Place.objects.filter(infos__access_address_id=address_id).first()

                        if saved_place:
                            potential_new_place_id = None

                            if saved_place.subject == folk or saved_place.content_type != folk_content_type:
                                potential_new_place_id = saved_place.id
                            address = saved_place.address

                            if address and not address.name:
                                full_address_name = display_name + ' family: ' + address.raw
                                address.name = display_name
                                # address.raw = str(folk.id)  # Todo 20220902 double check if folk id needed
                                address.formatted = full_address_name
                                address.save()

                            Place.objects.update_or_create(
                                id=potential_new_place_id,  # infos__access_address_id=address_id,  # multiple households could share the same address
                                # address=address,
                                defaults={
                                    'address': address,
                                    'display_name':  display_name,
                                    'content_type': folk_content_type,
                                    'object_id': folk.id,
                                    'infos': {
                                        'access_address_id': address_id,  # str
                                        'contacts': {
                                            'phone1': self.add_int_code(phone1),  # Todo: check if repeating run adding extra country code such as +1+1+1-510-123-4567
                                            'phone2': self.add_int_code(phone2),  # Todo: need to remove contacts from Place since it's across organizations
                                        },
                                        'fixed': {}
                                    },
                                }
                            )
                successfully_processed_count += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.stdout.write(f'While importing/updating household: {household}')
                self.stdout.write(f'An error occurred and cannot proceed import_households, reason: {e} at line: {exc_tb.tb_lineno}.')
        self.stdout.write('done!')
        return successfully_processed_count

    def import_attendees(self, peoples, rock_meet_slug, foot_meet_slug, division3_slug, data_assembly_slug, member_meet_slug, baptized_meet_slug, division_converter, believer_meet_slug):
        """
        Importer of each people from MS Access.
        :param peoples: file content of people accessible by headers, from MS Access
        :param division3_slug: key of division 3  # kid
        :param data_assembly_slug: key of data_assembly
        :param member_meet_slug: key of member_meet
        :param baptized_meet_slug: key of baptized_meet_slug
        :param roaster_meet1_slug: key of roaster_meet1_slug e
        :param roaster_meet2_slug: key of roaster_meet2_slug
        :param believer_meet_slug: key of believer_meet_slug
        :param rock_meet: key of rock_meet
        :param foot_meet: key of foot_meet
        :return: successfully processed attendee count, also print out importing status and write Photo&FolkAttendee to Attendees db (create or update)
        """
        gender_converter = {
            'F': GenderEnum.FEMALE,
            'M': GenderEnum.MALE,
        }

        progression_converter = {
            'Christian': 'christian',
            'Member': 'cfcc_member',
            'MemberDate': 'member_since',
            'FirstDate': 'visit_since',
            'BapDate': 'baptized_since',
            'BapLocation': 'baptism_location',
            'Group': 'language_group',
            'Active': 'active',
        }

        family_to_attendee_infos_converter = {
            'AttendenceCount': 'attendance_count',
            'FlyerMailing': 'flyer_mailing',
            'CardMailing': 'card_mailing',
            'UpdateDir': 'update_directory',
            'PrintDir': 'print_directory',
            'LastUpdate': 'household_last_update',
            '海沃之友': 'hayward_friend',
        }

        cr_meet = Meet.objects.get(pk=3)
        cr_converter = {
            'CRS': Team.objects.get(pk=8),
            'CRA': Team.objects.get(pk=9),
            'CRT': Team.objects.get(pk=10),
            'CRB': Team.objects.get(pk=11),
        }

        cml_converter = {
            '2022CMLRlg': Team.objects.get(pk=6),
            '2022CMLRpk': Team.objects.get(pk=15),
            '2022CMLRg1': Team.objects.get(pk=16),
            '2022CMLR23': Team.objects.get(pk=22),
            '2022CMLR45': Team.objects.get(pk=24),
            '2022CMLRps': Team.objects.get(pk=1),
            '2022CMLRu3': Team.objects.get(pk=14),
        }

        self.stdout.write("\n\nRunning import_attendees: \n")
        default_division = Division.objects.first()
        division3 = Division.objects.get(slug=division3_slug)  # kid
        data_assembly = Assembly.objects.get(slug=data_assembly_slug)
        rock_meet = Meet.objects.select_related('major_character').get(slug=rock_meet_slug)
        foot_meet = Meet.objects.select_related('major_character').get(slug=foot_meet_slug)
        visitor_meet = Meet.objects.select_related('major_character').get(pk=0)
        member_meet = Meet.objects.select_related('major_character').get(slug=member_meet_slug)
        member_gathering = Gathering.objects.filter(meet=member_meet).last()
        attendee_content_type = ContentType.objects.get_for_model(Attendee)
        baptized_meet = Meet.objects.select_related('major_character').get(slug=baptized_meet_slug)
        baptized_category = Category.objects.filter(type='status', display_name='baptized').first()
        believer_category = Category.objects.filter(type='status', display_name='receive').first()
        believer_meet = Meet.objects.select_related('major_character').get(slug=believer_meet_slug)
        successfully_processed_count = 0  # Somehow peoples.line_num incorrect, maybe csv file come with extra new lines.
        photo_import_results = []
        for people in peoples:
            try:
                self.stdout.write('.', ending='')
                first_name = Utility.presence(people.get('FirstName'))
                last_name = Utility.presence(people.get('LastName'))
                birth_date = Utility.presence(people.get('BirthDate'))
                name2 = Utility.presence(people.get('ChineseName'))
                household_id = Utility.presence(people.get('HouseholdID'))
                household_role = Utility.presence(people.get('HouseholdRole'))
                nick_name = Utility.presence(people.get('NickName'))
                food_pref = Utility.presence(people.get('FoodPref'))
                photo_release_grant_date = Utility.presence(people.get('PhotoReleaseGrantDate'))
                grade = Utility.presence(people.get('Grade'))
                if household_id and (first_name or last_name):
                    phones = [Utility.presence(people.get('WorkPhone')), Utility.presence(people.get('CellPhone'))]
                    email = Utility.presence(people.get('E-mail'))
                    if email:
                        if '@' not in email:  # some phone number are accidentally in email column
                            phones = [email] + phones
                            email = None
                    phone1, phone2 = self.return_two_phones(phones)

                    contacts = {
                                'email1': email,
                                'email2': None,
                                'phone1': self.add_int_code(phone1),
                                'phone2': self.add_int_code(phone2),
                                }
                    attendee_values = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'first_name2': None,
                        'last_name2': None,
                        'gender': gender_converter.get(Utility.presence(people.get('Sex', '').upper()), GenderEnum.UNSPECIFIED).name,
                        'infos': {
                            **Utility.attendee_infos(),
                            'fixed': {
                                'access_people_household_id': household_id,
                                'access_people_values': people,
                            },
                            'contacts': contacts,
                            'names': {},
                            'progressions': {attendee_header: Utility.boolean_or_datetext_or_original(people.get(access_header)) for (access_header, attendee_header) in progression_converter.items() if Utility.presence(people.get(access_header)) is not None},
                            'emergency_contacts': {}, 'schedulers': {}, 'updating_attendees': {},
                            'created_reason': 'CFCCH member/directory registration from importer',  # the word "importer" can skip signal
                        }
                    }
                    estimated_birthday = False
                    if birth_date:  # Todo 20220206 parse partial date into estimate_birthday, also someone is 11//25/2018
                        try:
                            formatting_birthdate = Utility.boolean_or_datetext_or_original(birth_date)
                            attendee_values['actual_birthday'] = datetime.strptime(formatting_birthdate, '%Y-%m-%d').date()
                        except ValueError as ve:
                            estimated_birthday = True
                            self.stdout.write(f"\nImport_attendees error on BirthDate of people: {people}. Reason: {ve}. This birthday will be skipped. Other columns of this people will still be saved. Continuing. \n")

                    if nick_name:
                        attendee_values['infos']['names']['nick'] = nick_name

                    if food_pref:
                        attendee_values['infos']['fixed']['food_pref'] = food_pref

                    if photo_release_grant_date:
                        attendee_values['infos']['fixed']['photo_release_grant_date'] = '2022-09-01'  # CM current data date

                    if grade:
                        attendee_values['infos']['fixed']['grade'] = grade
                        attendee_values['infos']['fixed']['grade_assess_date'] = '2022-08-31'  # CM current data date

                    if name2:  # assume longest last name is 2 characters
                        break_position = -2 if len(name2) > 2 else -1
                        attendee_values['first_name2'] = name2[break_position:]
                        attendee_values['last_name2'] = name2[:break_position]

                    query_values = {
                        'first_name': attendee_values['first_name'],
                        'last_name': attendee_values['last_name'],
                        'first_name2': attendee_values['first_name2'],
                        'last_name2': attendee_values['last_name2'],
                        'infos__fixed__access_people_household_id': household_id,
                    }

                    attendee, attendee_created = Attendee.objects.update_or_create(
                        **{k: v for (k, v) in query_values.items() if v is not None},
                        defaults={k: v for (k, v) in attendee_values.items() if v is not None}
                    )
                    if estimated_birthday and birth_date:
                        estimated_birthday_text = re.sub('/', '-', birth_date.strip('/').replace('//', '/'))
                        if not re.search('\d{4}', estimated_birthday_text):
                            estimated_birthday_text = '1800-' + estimated_birthday_text
                        estimated_birthday_text = re.sub(r'^(0[1-9]|[1-9]|1[012])[-]((19|20)\d\d)$', r"\2-\1", estimated_birthday_text)  # change 12-2099 to 2099-12
                        try:
                            attendee.estimated_birthday = estimated_birthday_text
                            attendee.save()
                            self.stdout.write(f"466 estimated_birthday of attendee {attendee.display_label} is being saved as {attendee.estimated_birthday}")
                        except ValidationError:
                            self.stdout.write(f"468 estimated_birthday of attendee {attendee.display_label} saved FAIL as {attendee.estimated_birthday}")
                            attendee.estimated_birthday = ''
                    # potential_non_family_folk = attendee.folks.filter(category=Attendee.NON_FAMILY_CATEGORY).first()
                    # non_family_folk, folk_created = Folk.objects.update_or_create(
                    #     id=potential_non_family_folk.id if potential_non_family_folk else None,
                    #     defaults={
                    #         'division': attendee.division,
                    #         'category': non_family_category,
                    #         'display_name': f"{attendee.infos['names']['original']} relationship",
                    #     }
                    # )
                    # FolkAttendee.objects.update_or_create(
                    #     folk=non_family_folk,
                    #     attendee=attendee,
                    #     defaults={
                    #         'folk': non_family_folk,
                    #         'attendee': attendee,
                    #         'role': hidden_role_for_relationship_folk,
                    #     }
                    # )

                    photo_import_results.append(self.update_attendee_photo(attendee, Utility.presence(people.get('Photo'))))
                    self.update_attendee_membership_and_other(rock_meet, foot_meet, cml_converter, cr_meet, cr_converter, baptized_meet, baptized_category, attendee_content_type, attendee, data_assembly, member_meet, member_gathering, believer_meet, believer_category)

                    if household_role:   # filling temporary family roles
                        folk = Folk.objects.filter(infos__access_household_id=household_id).first()
                        if folk:       # there are some missing records in the access data
                            if household_role == 'A(Self)':
                                relation = Relation.objects.get(title='self')
                                display_order = 0
                                attendee.division = folk.division or default_division
                            elif household_role == 'B(Spouse)':
                                relation = Relation.objects.get(
                                    title__in=['spouse', 'husband', 'wife'],
                                    gender=attendee.gender,
                                )  # There are wives mislabelled as 'Male' in Access data
                                display_order = 1
                                attendee.division = folk.division or default_division
                            else:
                                relation = Relation.objects.get(
                                    title__in=['child', 'son', 'daughter'],
                                    gender=attendee.gender,
                                )
                                if attendee.age() and attendee.age() < 11:  # k-5 to kid, should > 10 to EN?
                                    attendee.division = division3
                                display_order = 10

                            some_household_values = {attendee_header: Utility.boolean_or_datetext_or_original(folk.infos.get('access_household_values', {}).get(access_header)) for (access_header, attendee_header) in family_to_attendee_infos_converter.items() if Utility.presence(folk.infos.get('access_household_values', {}).get(access_header)) is not None}
                            # some_household_values['print_directory'] = [str(folk.id)]
                            attendee.infos = {
                                'mobility': 2,
                                'created_reason': attendee.infos.get('created_reason'),
                                'fixed': {**attendee.infos.get('fixed', {}), **some_household_values},
                                'contacts': contacts,
                                'names': attendee.infos.get('names', {}),
                                'emergency_contacts': attendee.infos.get('emergency_contacts', {}),
                                'progressions': attendee.infos.get('progressions', {}),
                                'schedulers': attendee.infos.get('schedulers', {}),
                                'updating_attendees': attendee.infos.get('updating_attendees', {}),
                            }

                            attendee_non_family_folk = attendee.folks.filter(category=Attendee.NON_FAMILY_CATEGORY).first()
                            if attendee_non_family_folk:
                                attendee_non_family_folk.division = attendee.division
                                attendee_non_family_folk.save()
                            else:
                                self.stdout.write("no friend circle!!! for attendee: ", attendee)

                            attendee.save()
                            FolkAttendee.objects.update_or_create(
                                folk=folk,
                                attendee=attendee,
                                defaults={
                                    'display_order': display_order,
                                    'role': relation,
                                    'start': '1800-01-01',
                                }
                            )
                            #
                            # address_id = folk.infos.get('access_household_values', {}).get('AddressID', 'missing')
                            # family_place = Place.objects.filter(infos__access_address_id=address_id).first()
                            # if family_place:
                            #     Place.objects.update_or_create(
                            #         address=family_place.address,
                            #         content_type=attendee_content_type,
                            #         object_id=attendee.id,
                            #         address_extra=family_place.address_extra,
                            #         defaults={
                            #             'address': family_place.address,
                            #             'content_type': attendee_content_type,
                            #             'object_id': attendee.id,
                            #             'display_name': 'main',
                            #             'display_order': 0,
                            #             'address_extra': family_place.address_extra,
                            #             'infos': {
                            #                 'contacts': {},
                            #                 'fixed': {},
                            #             },
                            #         }
                            #     )  # don't add infos__access_address_id so future query will only get one at family level
                        else:
                            self.stdout.write(f"\nBad data, cannot find the household id: {household_id} for people: {people}, Other columns of this people will still be saved. Continuing. \n")

                    self.update_attendee_worship_roster(attendee, data_assembly, visitor_meet, division_converter)
                else:
                    self.stdout.write(f'There is no household_id or first/lastname of the people: {people}')
                successfully_processed_count += 1

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.stdout.write(f"\nWhile importing/updating people: {people}")
                self.stdout.write(f'Cannot save import_attendees, reason: {e} at line: {exc_tb.tb_lineno}.')
        AttendingMeet.objects.filter(meet=member_meet).update(category_id=6)  # Active, direct SQL update won't trigger save()
        self.stdout.write('done!')
        return successfully_processed_count, photo_import_results  # list(filter(None.__ne__, photo_import_results))

    def reprocess_directory_emails_and_family_roles(self, division3_slug, rock_meet_slug, foot_meet_slug, directory_meet_slug):
        """
        Reprocess extra data (email/relationship) from FolkAttendee, also do data correction of Role
        :param data_assembly_slug: key of data_assembly
        :param directory_meet_slug: key of directory_gathering
        :return: successfully processed relation count, also print out importing status and write to Attendees db (create or update)
        """
        self.stdout.write("\n\nRunning reprocess_family_roles: \n")
        husband_role = Relation.objects.get(
            title='husband',
            gender=GenderEnum.MALE.name,
        )

        wife_role = Relation.objects.get(
            title='wife',
            gender=GenderEnum.FEMALE.name,
        )
        cm_assembly = Assembly.objects.get(pk=1)
        directory_meet = Meet.objects.get(slug=directory_meet_slug)
        directory_gathering = Gathering.objects.filter(meet=directory_meet).last()
        # directory_character = directory_meet.major_character
        imported_family_folks = Folk.objects.filter(category=Attendee.FAMILY_CATEGORY, infos__access_household_id__isnull=False).order_by('created')  # excludes seed data
        cm_converter = {
            '2022CMLRpk': Team.objects.get(pk=15),
            '2022CMLRg1': Team.objects.get(pk=16),
            '2022CMLR23': Team.objects.get(pk=22),
            '2022CMLR45': Team.objects.get(pk=24),
            '2022CMLRps': Team.objects.get(pk=1),
            '2022CMLRu3': Team.objects.get(pk=14),
        }
        division3 = Division.objects.get(slug=division3_slug)  # kid
        rock_meet = Meet.objects.select_related('major_character').get(slug=rock_meet_slug)
        foot_meet = Meet.objects.select_related('major_character').get(slug=foot_meet_slug)
        tzname = rock_meet.infos.get('default_time_zone')
        time_zone = pytz.timezone(parse.unquote(tzname))
        import_time = datetime.strptime("2022-09-01T02:00:00Z", "%Y-%m-%dT%H:%M:%SZ").astimezone(time_zone)
        end_time = datetime.strptime("2033-09-01T02:00:00Z", "%Y-%m-%dT%H:%M:%SZ").astimezone(time_zone)
        successfully_processed_count = 0
        for folk in imported_family_folks:
            try:
                self.stdout.write('.', ending='')
                registrant = None
                children = folk.attendees.filter(folkattendee__role__title__in=['child', 'son', 'daughter']).all()
                parents = folk.attendees.filter(folkattendee__role__title__in=['self', 'spouse', 'husband', 'wife']).order_by().all()  # order_by() is critical for values_list('gender').distinct() later
                families_address = folk.places.first()  # families_address = Address.objects.filter(pk=family.addresses.first().id).first()
                potential_primary_phone = folk.infos.get('access_household_values', {}).get('HouseholdPhone')
                if len(parents) > 1:  # family role modification skipped for singles
                    potential_secondary_phone = folk.infos.get('access_household_values', {}).get('HouseholdFax')
                    if len(parents.values_list('gender', flat=True).distinct()) < 2:
                        self.stdout.write(f"\n Parents genders are mislabelled, trying to reassign them: {parents}")

                        if set(['Chloris', 'Yvone']) & set(parents.values_list('first_name', flat=True)):  # these two are special cases in Access data
                            wife, husband = parents.order_by('created')
                        else:
                            husband, wife = parents.order_by('created')

                        husband.gender = GenderEnum.MALE.name
                        husband.save()
                        husband_folkattendee = husband.folkattendee_set.first()
                        husband_folkattendee.role = husband_role
                        # husband_folkattendee.display_order = 100
                        husband_folkattendee.save()

                        wife.gender = GenderEnum.FEMALE.name
                        wife.save()
                        wife_folkattendee = wife.folkattendee_set.first()
                        wife_folkattendee.role = wife_role
                        # wife_folkattendee.display_order = 200
                        wife_folkattendee.save()
                        self.stdout.write(f'After reassigning, now husband is: {husband}. And wife is: {wife}. Continuing.')

                    unspecified_househead = folk.attendees.filter(folkattendee__role__title='self').first()
                    # Todo: even some househeads are alone, there are some cases of bachelor/widow !!
                    if unspecified_househead:
                        househead_role = Relation.objects.get(
                            title__in=['husband', 'wife'],
                            gender=unspecified_househead.gender,
                        )
                        FolkAttendee.objects.update_or_create(
                            folk=folk,
                            attendee=unspecified_househead,
                            defaults={'display_order': 0, 'role': househead_role}
                        )
                        self.save_two_phones(unspecified_househead, potential_primary_phone)

                    husband = folk.attendees.filter(folkattendee__role__title='husband').order_by('created').first()
                    wife = folk.attendees.filter(folkattendee__role__title='wife').order_by('created').first()
                    if not wife:  # widow? (since parents number is 2)
                        wife = folk.attendees.filter(folkattendee__role__title='self').order_by('created').first()
                    if not husband:
                        self.stdout.write(f"618, no husband found, here is potential_primary_phone: {potential_primary_phone}")

                    if husband and wife:  # depend on save by save_two_phones()
                        husband.infos['emergency_contacts'][str(wife.id)] = True
                        wife.infos['emergency_contacts'][str(husband.id)] = True

                    self.save_two_phones(husband, potential_primary_phone or potential_secondary_phone or '+no phone+')
                    self.save_two_phones(wife, potential_secondary_phone or potential_primary_phone or '+no phone+')

                    hushand_email = husband.infos.get('fixed', {}).get('access_people_values', {}).get('E-mail')
                    wife_email = wife.infos.get('fixed', {}).get('access_people_values', {}).get('E-mail')
                    folk.infos['contacts']['email1'] = Utility.presence(hushand_email)
                    folk.infos['contacts']['email2'] = Utility.presence(wife_email)
                    folk.save()
                    registrant = wife
                    # Relationship.objects.update_or_create(
                    #     from_attendee=wife,
                    #     to_attendee=husband,
                    #     relation=husband_role,
                    #     defaults={
                    #         'in_family': folk,
                    #         'emergency_contact': husband_role.emergency_contact,
                    #         'scheduler': husband_role.scheduler,
                    #         # 'finish': Utility.forever(),
                    #         'infos': Utility.relationship_infos(),
                    #         #{
                    #         #    'show_secret': {},
                    #        # },
                    #     }
                    # )
    
                    # Relationship.objects.update_or_create(
                    #     from_attendee=husband,
                    #     to_attendee=wife,
                    #     relation=wife_role,
                    #     defaults={
                    #         'in_family': folk,
                    #         'emergency_contact': wife_role.emergency_contact,
                    #         'scheduler': wife_role.scheduler,
                    #         # 'finish': Utility.forever(),
                    #         'infos': Utility.relationship_infos(),
                    #         #{
                    #         #    'show_secret': {},
                    #         #},
                    #     }
                    # )
                    successfully_processed_count += 2

                else:
                    househead_single = parents.first()
                    if househead_single:  # update gender by family role since some access_family role records are incorrect.
                        original_household_role = househead_single.infos.get('fixed', {}).get('access_people_values', {}).get('HouseholdRole')
                        if original_household_role == 'B(Spouse)':  # 'Chloris', 'Yvone' are parents > 1
                            househead_single.gender = GenderEnum.FEMALE.name
                            househead_single.save()
                            family_attendee = househead_single.folkattendee_set.first()
                            family_attendee.role = wife_role
                            family_attendee.save()

                        self_email = househead_single.infos.get('fixed', {}).get('access_people_values', {}).get('E-mail')
                        folk.infos['contacts']['email1'] = Utility.presence(self_email)
                        folk.save()
                        self.save_two_phones(househead_single, potential_primary_phone)
                        registrant = househead_single
                    else:
                        if Attendee.objects.filter(infos__fixed__access_people_household_id=folk.infos['access_household_id']):
                            self.stdout.write(f"\nSomehow there's no one in families parents or househead_single (orphan?), for folk {folk}. families_address: {families_address}. parents: {parents}. household_id: {folk.infos['access_household_id']}. folk.id: {folk.id}. Continuing to next record.")
                        else:
                            pass  # skipping since there is no such people with the household id in the original access data.

                # siblings = permutations(children, 2)
                # for (from_child, to_child) in siblings:
                #     househead_role = Relation.objects.get(
                #         title__in=['brother', 'sister', 'sibling'],
                #         gender=to_child.gender,
                #     )
                #     Relationship.objects.update_or_create(
                #         from_attendee=from_child,
                #         to_attendee=to_child,
                #         relation=househead_role,
                #         defaults={
                #                     'in_family': folk,
                #                     'emergency_contact': False,
                #                     'scheduler': False,
                #                     # 'finish': Utility.forever(),
                #                     'infos': Utility.relationship_infos(),
                #                     #{
                #                     #    'show_secret': {},
                #                     #},
                #                  }
                #     )
                for child in children:
                    for parent in parents:
                        child.infos['emergency_contacts'][str(parent.id)] = True
    
                        if child.age() and child.age() < 18:
                            child.infos['schedulers'][str(parent.id)] = True

                    people_note = child.infos.get('fixed', {}).get('access_people_values', {}).get('PeopleNote')
                    character_id = child.infos.get('fixed', {}).get('access_people_values', {}).get('CharacterId')
                    if people_note and people_note in cm_converter and not character_id:  # magic word for adding CM attendingmeet
                        # self.stdout.write(f"\nfor child: {child} people_note: {people_note}")
                        cm_registration, cm_registration_created = Registration.objects.update_or_create(
                            assembly=cm_assembly,
                            registrant=registrant,
                            defaults={
                                'registrant': registrant,  # admin/secretary may change for future members.
                                'assembly': cm_assembly,
                                'infos': {
                                    'access_household_id': child.infos.get('fixed', {}).get('access_people_values', {}).get('HouseholdID'),
                                    'created_reason': 'CFCCH member/directory registration from importer',
                                }
                            }
                        )
                        # self.stdout.write(f"for cm_registration: {cm_registration} registrant: {registrant}")
                        data_attending = child.attendings.first()
                        data_attending.registration = cm_registration
                        data_attending.save()
                        # self.stdout.write(f"806 data_attending.registration: {data_attending.registration}")
                        child.division = division3
                        meet = foot_meet if people_note == '2022CMLRu3' else rock_meet
                        AttendingMeet.objects.update_or_create(
                            meet=meet,
                            attending=data_attending,
                            character=meet.major_character,
                            team=cm_converter.get(people_note),
                            defaults={
                                'attending': data_attending,
                                'meet': meet,
                                'character': meet.major_character,
                                'team': cm_converter.get(people_note),
                                'start': import_time,
                                'finish': end_time,
                            },
                        )

                    child.save()
                    successfully_processed_count += 1
                    # self.stdout.write(f"child.division: {child.division}")
                for parent in folk.attendees.filter(folkattendee__role__title__in=['self', 'spouse', 'husband', 'wife']).order_by().all():  # reload to get updated parent gender
                    parent_role = Relation.objects.get(
                        title__in=['father', 'mother', 'parent'],
                        gender=parent.gender,
                    )
                    for child in children:
                        child_role = Relation.objects.get(
                            title__in=['child', 'son', 'daughter'],
                            gender=child.gender,
                        )
                        parent.infos['emergency_contacts'][str(child.id)] = child_role.emergency_contact
                        child.infos['emergency_contacts'][str(parent.id)] = parent_role.emergency_contact
                        if child.age() and child.age() < 18:
                            child.infos['schedulers'][str(parent.id)] = parent_role.scheduler
                        # Relationship.objects.update_or_create(
                        #     from_attendee=parent,
                        #     to_attendee=child,
                        #     relation=child_role,
                        #     defaults={
                        #         'in_family': folk,
                        #         'emergency_contact': child_role.emergency_contact,
                        #         'scheduler': child_role.scheduler,
                        #         # 'finish': Utility.forever(),
                        #         'infos': Utility.relationship_infos(),
                        #         #{
                        #         #    'show_secret': {},
                        #         #},
                        #     }
                        # )
    
                        # Relationship.objects.update_or_create(
                        #     from_attendee=child,
                        #     to_attendee=parent,
                        #     relation=parent_role,
                        #     defaults={
                        #         'in_family': folk,
                        #         'emergency_contact': parent_role.emergency_contact,
                        #         'scheduler': parent_role.scheduler,
                        #         # 'finish': Utility.forever(),
                        #         'infos': Utility.relationship_infos(),
                        #         #{
                        #         #    'show_secret': {},
                        #         #},
                        #     }
                        # )
                        child.save()
                        successfully_processed_count += 2
                    parent.save()
                    successfully_processed_count += 1
                self.update_directory_data(folk, directory_meet, directory_gathering)

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.stdout.write(f"\nWhile importing/updating relationship for folk: {folk} at line: {exc_tb.tb_lineno}.")
                self.stdout.write(f'Cannot save relationship or update_directory_data, reason: {e}')
        self.stdout.write('done!')
        return successfully_processed_count

    def update_attendee_worship_roster(self, attendee, data_assembly, visitor_meet, division_converter):
        pdt = pytz.timezone('America/Los_Angeles')
        access_household_id = attendee.infos.get('fixed', {}).get('access_people_household_id')
        data_registration = Registration.objects.filter(
            assembly=data_assembly,
            registrant=attendee,
        ).first()

        data_attending = Attending.objects.filter(
            attendee=attendee,
            registration=data_registration,
        ).first()

        AttendingMeet.objects.update_or_create(
            meet=visitor_meet,
            attending=data_attending,
            character=visitor_meet.major_character,
            defaults={
                'character': visitor_meet.major_character,
                'category_id': -1,
                'start': visitor_meet.start,
                'finish': visitor_meet.finish,
            },
        )

        if attendee.infos.get('fixed', {}).get('attendance_count') in ['1', 'TRUE', 1] and attendee.division.id in division_converter:
            meet = division_converter.get(attendee.division.id, {}).get('meet')
            gathering = division_converter.get(attendee.division.id, {}).get('gathering')
            AttendingMeet.objects.update_or_create(
                meet=meet,
                attending=data_attending,
                character=meet.major_character,
                defaults={
                    'character': meet.major_character,
                    'category_id': -1,  # This stop auto create Past via post-save signal
                    'start': meet.start,
                    'finish': datetime.now(pdt) + timedelta(365),  # whoever don't attend for a year won't be counted anymore
                },
            )

            if meet.infos.get("gathering_infos", {}).get("generate_attendance"):
                Attendance.objects.update_or_create(
                    gathering=gathering,
                    attending=data_attending,
                    character=meet.major_character,
                    team=None,
                    defaults={
                        'gathering': gathering,
                        'attending': data_attending,
                        'character': meet.major_character,
                        # 'category_id': 6,   # Active
                        'team': None,
                        'start': gathering.start,
                        'finish': gathering.finish,
                        'infos': {
                            'access_household_id': access_household_id,
                            'created_reason': 'CFCCH member/directory registration from importer',
                        },
                    }
                )

    def update_attendee_membership_and_other(self, rock_meet, foot_meet, cml_converter, cr_meet, cr_converter, baptized_meet, baptized_category, attendee_content_type, attendee, data_assembly, member_meet, member_gathering, believer_meet, believer_category):
        access_household_id = attendee.infos.get('fixed', {}).get('access_people_household_id')

        data_attending, data_attending_created = Attending.objects.update_or_create(
            attendee=attendee,
            # registration=data_registration,
            defaults={
                # 'registration': data_registration,
                'attendee': attendee,
                'infos': {
                    'access_household_id': access_household_id,
                    'created_reason': 'CFCCH member/directory attending from importer',  # magic word to stop attendee to attending
                }
            }
        )
        member_date_text = Utility.presence(attendee.infos.get('progressions', {}).get('member_since', '').replace('*', '1'))
        is_member = (True if member_date_text else False) or Utility.boolean_or_datetext_or_original(attendee.infos.get('progressions', {}).get('cfcc_member'))
        bap_date_text = None
        if attendee.infos.get('progressions', {}).get('baptized_since') or attendee.infos.get('progressions', {}).get('baptism_location'):
            bap_date_text = Utility.parsedate_or_now(attendee.infos.get('progressions', {}).get('baptized_since', '').replace('*', '1'), error_context=f' when parsing baptized_since of {attendee.display_label} at line 861')

        is_believer = is_member or bap_date_text or Utility.boolean_or_datetext_or_original(attendee.infos.get('progressions', {}).get('christian'))

        if is_believer or bap_date_text or is_member:

            AttendingMeet.objects.update_or_create(
                meet=believer_meet,
                attending=data_attending,
                character=believer_meet.major_character,
                defaults={
                    'attending': data_attending,
                    'meet': believer_meet,
                    'character': believer_meet.major_character,
                    'category_id': -1,  # This stop auto create Past via post-save signal
                    'start': Utility.now_with_timezone(),
                    'finish': believer_meet.finish,
                },
            )

            defaults = {
                'organization': data_assembly.division.organization,
                'content_type': attendee_content_type,
                'object_id': attendee.id,
                'category': believer_category,
                'display_name': '已信主 Christian',
                "is_removed": False,
            }

            Utility.update_or_create_last(
                Past,
                update=False,
                filters=defaults,
                defaults={**defaults, "infos": {**Utility.relationship_infos(), "comment": "importer"}},  # stop auto-create
            )

        if bap_date_text or is_member:
            member_date_or_now = Utility.parsedate_or_now(member_date_text, error_context=f' when parsing member_since of {attendee.display_label} at line 899')
            bap_date_or_now = Utility.parsedate_or_now(bap_date_text, error_context=f' when parsing baptized_since of {attendee.display_label} at line 899')
            baptized_date_or_now = min(member_date_or_now, bap_date_or_now)
            bap_date_or_unknown = Utility.boolean_or_datetext_or_original(attendee.infos.get('progressions', {}).get('baptized_since', 'unknown'))

            AttendingMeet.objects.update_or_create(
                meet=baptized_meet,
                attending=data_attending,
                character=baptized_meet.major_character,
                defaults={
                    'attending': data_attending,
                    'meet': baptized_meet,
                    'character': baptized_meet.major_character,
                    'category_id': -1,  # This stops auto create Past via post-save signal
                    'start': baptized_date_or_now,
                    'finish': baptized_meet.finish,
                },
            )

            Past.objects.update_or_create(
                organization=data_assembly.division.organization,
                content_type=attendee_content_type,
                object_id=attendee.id,
                category=baptized_category,
                display_name='已受洗 baptized',
                when=None if baptized_date_or_now.date() == datetime.today().date() else baptized_date_or_now,
                infos={
                    **Utility.relationship_infos(),
                    'comment': f'[importer] possible date: {bap_date_or_unknown}',  # importer stops auto creation of AttenddingMeet
                },
            )

        if is_member:

            # member_since_text = Utility.presence(attendee.infos.get('progressions', {}).get('member_since'))
            # member_since_reason = ', member since ' + member_since_text if member_since_text else ''

            member_since_or_now = Utility.parsedate_or_now(attendee.infos.get('progressions', {}).get('member_since'), error_context=f' when parsing member_since of {attendee.display_label} at line 934')
            member_attending_meet_default = {
                'attending': data_attending,
                'meet': member_meet,
                'character': member_meet.major_character,
                'category_id': -1,  # member category has to be converted to active later
                'start': member_since_or_now,
                'finish': member_meet.finish,
            }

            AttendingMeet.objects.update_or_create(
                meet=member_meet,
                attending=data_attending,
                character=member_meet.major_character,
                defaults=member_attending_meet_default,
            )

            Attendance.objects.update_or_create(
                gathering=member_gathering,
                attending=data_attending,
                character=member_meet.major_character,
                team=None,
                defaults={
                    'gathering': member_gathering,
                    'attending': data_attending,
                    'character': member_meet.major_character,
                    'team': None,
                    # 'category_id': 6,  # Active, membership can be inactive temporarily
                    'start': member_attending_meet_default['start'],
                    'finish': member_gathering.finish,
                    'infos': {
                        'access_household_id': access_household_id,
                        'created_reason': 'CFCCH member/directory registration from importer',
                    },
                }
            )

        tzname = cr_meet.infos.get('default_time_zone')
        time_zone = pytz.timezone(parse.unquote(tzname))
        time_format = "%Y-%m-%dT%H:%M:%SZ"
        import_time = datetime.strptime("2022-09-01T02:00:00Z", time_format).astimezone(time_zone)
        end_time = datetime.strptime("2033-09-01T02:00:00Z", time_format).astimezone(time_zone)
        people_note = attendee.infos.get('fixed', {}).get('access_people_values', {}).get('PeopleNote')
        if people_note in cr_converter:
            AttendingMeet.objects.update_or_create(
                meet=cr_meet,
                attending=data_attending,
                character=cr_meet.major_character,
                team=cr_converter.get(people_note),
                defaults={
                    'meet': cr_meet,
                    'attending': data_attending,
                    'character': cr_meet.major_character,
                    'team': cr_converter.get(people_note),
                    'start': import_time,
                    'finish': end_time,
                },
            )

        character_id = attendee.infos.get('fixed', {}).get('access_people_values', {}).get('CharacterId')
        if character_id and people_note in cml_converter:
            meet = foot_meet if people_note == '2022CMLRu3' else rock_meet
            AttendingMeet.objects.update_or_create(
                meet=meet,
                attending=data_attending,
                character=Character.objects.get(pk=character_id),
                team=cml_converter.get(people_note),
                defaults={
                    'attending': data_attending,
                    'meet': meet,
                    'character': Character.objects.get(pk=character_id),
                    'team': cml_converter.get(people_note),
                    'start': import_time,
                    'finish': end_time,
                },
            )

        pasts = attendee.infos.get('fixed', {}).get('access_people_values', {}).get('Past')
        if pasts:
            for history_name, time_string in json.loads(pasts).items():
                Past.objects.update_or_create(
                    organization=data_assembly.division.organization,
                    content_type=attendee_content_type,
                    object_id=attendee.id,
                    category_id=36,  # "Check"
                    display_name=history_name.title().replace('_', ' '),
                    when=datetime.strptime(time_string, time_format).astimezone(time_zone) if time_string else None,
                    infos={
                        **Utility.relationship_infos(),
                        'comment': f'importer',  # importer stops auto creation of AttenddingMeet
                    },
                )

    def update_directory_data(self, folk, directory_meet, directory_gathering):
        """
        update assembly and gathering for directory. using attendees own attending.

        :param folk: each family folk
        :param directory_meet: directory_meet
        :param directory_gathering: directory_gathering
        :return: None, but print out importing status and write to Attendees db (create or update)
        """
        if Utility.boolean_or_datetext_or_original(folk.infos.get('access_household_values', {}).get('PrintDir')):
            access_household_id = folk.infos.get('access_household_id')

            for family_member in folk.attendees.all():
                directory_attending, directory_attending_created = Attending.objects.update_or_create(
                    attendee=family_member,
                    defaults={
                        'attendee': family_member,
                        'infos': {
                            'access_household_id': access_household_id,
                            'created_reason': 'CFCCH member/directory attending from importer',
                        }
                    }
                )

                AttendingMeet.objects.update_or_create(
                    meet=directory_meet,
                    attending=directory_attending,
                    character=directory_meet.major_character,
                    defaults={
                        'meet': directory_meet,
                        'attending': directory_attending,
                        'character': directory_meet.major_character,
                        'category_id': -1,
                        'start': directory_gathering.start,
                        'finish': directory_gathering.finish,
                    }
                )

                Attendance.objects.update_or_create(
                    gathering=directory_gathering,
                    attending=directory_attending,
                    character=directory_meet.major_character,
                    team=None,
                    defaults={
                        'gathering': directory_gathering,
                        'attending': directory_attending,
                        'character': directory_meet.major_character,
                        # 'category_id': 6,  # Active
                        'team': None,
                        'start': directory_gathering.start,
                        'finish': directory_gathering.finish,
                        'infos': {
                            'access_household_id': access_household_id,
                            'created_reason': 'CFCCH member/directory registration from importer',
                        },
                    }
                )

    def update_attendee_photo(self, attendee, photo_names):
        """
        search photo file and update photo for attendee (update/create).
        :param attendee: attendee
        :param photo_names: photo_names from MS Access data
        :return: Failure message, but write to Attendees db (create or update)
        """
        import_photo_success = False

        if photo_names:
            photo_infos={}
            for photo_filename in photo_names.split(';'):
                found_picture_files = glob('**/' + photo_filename, recursive=True)
                found_picture_file_name = found_picture_files[0] if len(found_picture_files) > 0 else None
                if found_picture_file_name:
                    pathlib_file_name = Path(found_picture_file_name)
                    file_modified_time = datetime.fromtimestamp(pathlib_file_name.stat().st_mtime)
                    photo_infos[found_picture_file_name] = file_modified_time
            if bool(photo_infos):
                latest_file_name = max(photo_infos, key=photo_infos.get)
                picture_name = latest_file_name.split('/')[-1]
                image_file = File(file=open(latest_file_name, 'rb'), name=picture_name)

                if attendee.photo:
                    old_file_path = attendee.photo.path
                    attendee.photo.delete()
                    if os.path.isfile(old_file_path):
                        os.remove(old_file_path)
    
                attendee.photo.save(picture_name, image_file, True)
                attendee.save()

                import_photo_success = True
        else:
            import_photo_success = None
        if import_photo_success or import_photo_success is None:
            return None  # import failure message
        else:
            return 'Attendee ' + str(attendee) + ' photo file(s) missing: ' + photo_names + "\n"

    def return_two_phones(self, phones):
        cleaned_phones = list(set([re.sub("[^0-9\+]+", "", p) for p in phones if (p and not p.isspace())]))
        return (cleaned_phones + [None, None])[0:2]

    def save_two_phones(self, attendee, phone):
        if phone:
            phone1, phone2 = self.return_two_phones([self.add_int_code(phone), attendee.infos.get('contacts', {}).get('phone1'), attendee.infos.get('contacts', {}).get('phone2')])
            attendee.infos['contacts'] = {
                'phone1': self.add_int_code(phone1),
                'phone2': self.add_int_code(phone2),
                'email1': attendee.infos.get('contacts', {}).get('email1'),
                'email2': attendee.infos.get('contacts', {}).get('email2'),
            }
            attendee.save()

    def add_int_code(self, phone, default='+1'):
        if phone and not phone.isspace():
            if '+' in phone:
                return phone
            else:
                return default + phone
        else:
            return None

    def add_arguments(self, parser):
        parser.add_argument('household_csv_file')
        parser.add_argument('people_csv_file')
        parser.add_argument('address_csv_file')
        parser.add_argument('division1_slug')
        parser.add_argument('division2_slug')
        parser.add_argument('division3_slug')
        parser.add_argument('data_assembly_slug')
        parser.add_argument('member_meet_slug')
        parser.add_argument('directory_meet_slug')
        parser.add_argument('baptized_meet_slug')
        parser.add_argument('roaster_meet1_slug')
        parser.add_argument('roaster_meet2_slug')
        parser.add_argument('believer_meet_slug')
        parser.add_argument('rock_meet_slug')
        parser.add_argument('foot_meet_slug')

    def handle(self, *args, **options):
        self.stdout.write("Running load_access_csv.py... with arguments: ")
        self.stdout.write(f"Reading household_csv_file: {options.get('household_csv_file')}")
        self.stdout.write(f"Reading people_csv_file: {options.get('people_csv_file')}")
        self.stdout.write(f"Reading address_csv_file: {options.get('address_csv_file')}")
        self.stdout.write(f"Reading division1_slug: {options.get('division1_slug')}")
        self.stdout.write(f"Reading division2_slug: {options.get('division2_slug')}")
        self.stdout.write(f"Reading division3_slug: {options.get('division3_slug')}")
        self.stdout.write(f"Reading data_assembly_slug: {options.get('data_assembly_slug')}")
        self.stdout.write(f"Reading member_meet_slug: {options.get('member_meet_slug')}")
        self.stdout.write(f"Reading directory_meet_slug: {options.get('directory_meet_slug')}")
        self.stdout.write(f"Reading roaster_meet1_slug: {options.get('roaster_meet1_slug')}")
        self.stdout.write(f"Reading roaster_meet2_slug: {options.get('roaster_meet2_slug')}")
        self.stdout.write(f"Reading believer_meet_slug: {options.get('believer_meet_slug')}")
        self.stdout.write(f"Reading rock_meet_slug: {options.get('rock_meet_slug')}")
        self.stdout.write(f"Reading foot_meet_slug: {options.get('foot_meet_slug')}")
        self.stdout.write("running commands: docker-compose -f local.yml run django python manage.py load_access_csv household_csv_file people_csv_file address_csv_file division1_slug division2_slug division3_slug data_assembly_slug member_meet_slug directory_meet_slug roaster_meet1_slug believer_meet_slug")

        if options.get('household_csv_file') and options.get('people_csv_file') and options.get('address_csv_file') and options.get('division1_slug') and options.get('division2_slug'):
            with open(options.get('household_csv_file'), mode='r', encoding='utf-8-sig') as household_csv, open(options.get('people_csv_file'), mode='r', encoding='utf-8-sig') as people_csv, open(options.get('address_csv_file'), mode='r', encoding='utf-8-sig') as address_csv:
                self.import_household_people_address(
                    household_csv,
                    people_csv,
                    address_csv,
                    options.get('division1_slug'),
                    options.get('division2_slug'),
                    options.get('division3_slug'),
                    options.get('data_assembly_slug'),
                    options.get('member_meet_slug'),
                    options.get('directory_meet_slug'),
                    options.get('baptized_meet_slug'),
                    options.get('roaster_meet1_slug'),
                    options.get('roaster_meet2_slug'),
                    options.get('believer_meet_slug'),
                    options.get('rock_meet_slug'),
                    options.get('foot_meet_slug'),
                )
        else:
            raise CommandError("household_csv_file, people_csv_file and address_csv_file are required.")
