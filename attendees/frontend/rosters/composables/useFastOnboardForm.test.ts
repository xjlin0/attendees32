import { describe, it, expect, beforeEach } from 'vitest';
import {
  useFastOnboardForm,
  genLocalId,
  parseCandidateContacts,
  getMaskedPhone,
  getCandidateFamilyId,
  getCandidateFamilyName,
  createDefaultAttendee,
  createDefaultCompanion,
  adoptCandidateIntoFormItem,
} from './useFastOnboardForm';
import { Endpoints } from '../types';

const mockEndpoints: Endpoints = {
  attendancesEndpoint: '/api/attendances/',
  assembliesEndpoint: '/api/assemblies/',
  categoriesEndpoint: '/api/categories/',
  scheduledCategory: 'test',
  meetsEndpointBySlug: '/api/meets/',
  rostersEndpoint: '/api/rosters/',
  attendingmeetsEndpoint: '/api/attendingmeets/',
  attendingsEndpoint: '/api/attendings/',
  charactersEndpoint: '/api/characters/',
  teamsEndpoint: '/api/teams/',
  divisionsEndpoint: '/api/divisions/',
  gatheringsEndpoint: '/api/gatherings/',
  searchAttendeesEndpoint: '/api/search/',
  fastOnboardEndpoint: '/api/fast_onboard/',
  relationsEndpoint: '/api/relations/',
  userCanWrite: true,
};

describe('useFastOnboardForm composable', () => {
  describe('Helper functions', () => {
    it('genLocalId generates unique sequential identifiers', () => {
      const id1 = genLocalId();
      const id2 = genLocalId();
      expect(id1).not.toBe(id2);
      expect(id1.startsWith('local_')).toBe(true);
    });

    it('parseCandidateContacts parses JSON string format', () => {
      const contactsJson = JSON.stringify({ phone: '1234567890', email: 'test@example.com' });
      const parsed = parseCandidateContacts(contactsJson);
      expect(parsed).toHaveLength(2);
      expect(parsed[0].type).toBe('phone');
      expect(parsed[0].value).toBe('1234567890');
      expect(parsed[1].type).toBe('email');
      expect(parsed[1].value).toBe('test@example.com');
    });

    it('parseCandidateContacts parses array format', () => {
      const contactsArray = [
        { type: 'phone', value: '1112223333' },
        'user@example.com',
      ];
      const parsed = parseCandidateContacts(contactsArray);
      expect(parsed).toHaveLength(2);
      expect(parsed[0]).toEqual({ type: 'phone', value: '1112223333' });
      expect(parsed[1]).toEqual({ type: 'email', value: 'user@example.com' });
    });

    it('getMaskedPhone extracts and masks last two digits', () => {
      expect(getMaskedPhone({ phone: '1234567890' })).toBe('***-**90');
      expect(getMaskedPhone(null)).toBe('');
      expect(getMaskedPhone({ email: 'test@test.com' })).toBe('');
    });

    it('getCandidateFamilyId and getCandidateFamilyName resolve latest family correctly', () => {
      const candWithLatest = {
        name: 'David',
        latest_family_id: 20,
        latest_family_name: 'New Family',
        folks: [
          { id: 10, name: 'Old Family', category_id: 0, is_latest_family: false },
          { id: 20, name: 'New Family', category_id: 0, is_latest_family: true },
        ],
      };
      expect(getCandidateFamilyId(candWithLatest)).toBe('20');
      expect(getCandidateFamilyName(candWithLatest)).toBe('New Family');

      const candWithoutLatest = {
        name: 'John',
        folks: [
          { id: 30, name: 'First Family', category_id: 0 },
        ],
      };
      expect(getCandidateFamilyId(candWithoutLatest)).toBe('30');
      expect(getCandidateFamilyName(candWithoutLatest)).toBe('First Family');
    });

    it('adoptCandidateIntoFormItem correctly updates form item state', () => {
      const item: any = {
        attendee_id: null,
        first_name: '',
        last_name: '',
        contacts: [],
      };
      const candidate = {
        id: 'att-123',
        first_name: 'John',
        last_name: 'Doe',
        gender: 'male',
        contacts: { phone: '1234567890' },
        latest_family_id: 55,
      };
      adoptCandidateIntoFormItem(item, candidate, false, []);
      expect(item.attendee_id).toBe('att-123');
      expect(item.first_name).toBe('John');
      expect(item.last_name).toBe('Doe');
      expect(item.gender).toBe('MALE');
      expect(item.contacts).toEqual([{ type: 'phone', value: '1234567890' }]);
      expect(item.family_id).toBe('55');
    });
  });

  describe('Form state and family tracking', () => {
    let form: ReturnType<typeof useFastOnboardForm>;

    beforeEach(() => {
      form = useFastOnboardForm(mockEndpoints);
      form.resetForm('div-1', [{ id: 'div-1', display_name: 'Junior' }], [], [{ id: 'rel-1', title: 'parent' }], true);
    });

    it('initializes with 1 attendee and 1 companion for kid meets', () => {
      expect(form.attendees.value).toHaveLength(1);
      expect(form.companions.value).toHaveLength(1);
      expect(form.linkedFamilyId.value).toBeNull();
      expect(form.linkedFamilyName.value).toBeNull();
    });

    it('tracks linkedFamilyId and linkedFamilyName when companion adopts candidate', () => {
      const cand = {
        id: 'c-1',
        name: 'Parent 1',
        latest_family_id: 99,
        latest_family_name: 'Smith Family',
        folks: [{ id: 99, name: 'Smith Family', category_id: 0, is_latest_family: true }],
      };

      adoptCandidateIntoFormItem(form.companions.value[0], cand, true, []);
      expect(form.linkedFamilyId.value).toBe('99');
      expect(form.linkedFamilyName.value).toBe('Smith Family');

      // Unlink companion
      form.companions.value[0].attendee_id = null;
      form.companions.value[0].linkedCandidate = null;
      expect(form.linkedFamilyId.value).toBeNull();
      expect(form.linkedFamilyName.value).toBeNull();
    });

    it('tracks linkedFamilyId when attendee adopts candidate', () => {
      const cand = {
        id: 'a-1',
        name: 'Kid 1',
        latest_family_id: 88,
        latest_family_name: 'Johnson Family',
        folks: [{ id: 88, name: 'Johnson Family', category_id: 0, is_latest_family: true }],
      };

      adoptCandidateIntoFormItem(form.attendees.value[0], cand, false, []);
      expect(form.linkedFamilyId.value).toBe('88');
      expect(form.linkedFamilyName.value).toBe('Johnson Family');

      // Unlink attendee
      form.attendees.value[0].attendee_id = null;
      form.attendees.value[0].linkedCandidate = null;
      expect(form.linkedFamilyId.value).toBeNull();
    });

    it('allows adding and removing attendees', () => {
      expect(form.attendees.value).toHaveLength(1);
      form.addAttendee('div-1', [], []);
      expect(form.attendees.value).toHaveLength(2);

      // Cannot remove attendee 0
      form.removeAttendee(0);
      expect(form.attendees.value).toHaveLength(2);

      // Can remove attendee 1
      form.removeAttendee(1);
      expect(form.attendees.value).toHaveLength(1);
    });

    it('allows adding and removing companions', () => {
      expect(form.companions.value).toHaveLength(1);
      form.addCompanion([], true, []);
      expect(form.companions.value).toHaveLength(2);

      form.removeCompanion(1);
      expect(form.companions.value).toHaveLength(1);
    });

    it('resets form state cleanly on resetForm', () => {
      form.addAttendee('div-1', [], []);
      form.addCompanion([], true, []);
      expect(form.attendees.value).toHaveLength(2);
      expect(form.companions.value).toHaveLength(2);

      form.resetForm('div-1', [{ id: 'div-1', display_name: 'Junior' }], [], [{ id: 'rel-1', title: 'parent' }], true);
      expect(form.attendees.value).toHaveLength(1);
      expect(form.companions.value).toHaveLength(1);
      expect(form.linkedFamilyId.value).toBeNull();
    });
  });
});
