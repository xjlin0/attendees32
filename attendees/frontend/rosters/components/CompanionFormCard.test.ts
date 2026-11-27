import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import CompanionFormCard from './CompanionFormCard.vue';
import { CompanionFormItem } from '../types';

const createMockCompanion = (overrides?: Partial<CompanionFormItem>): CompanionFormItem => ({
  id: 'comp_1',
  attendee_id: null,
  linkedCandidate: null,
  division_id: 'div-1',
  family_id: '',
  relationship: 'rel-parent',
  first_name: 'John',
  last_name: 'Doe',
  first_name2: '',
  last_name2: '',
  gender: 'MALE',
  contacts: [{ type: 'phone', value: '1234567890' }],
  candidateMatches: [],
  removedInAdultMeet: false,
  ...overrides,
});

describe('CompanionFormCard.vue component', () => {
  const defaultProps = {
    companion: createMockCompanion(),
    index: 0,
    companionsCount: 1,
    isKidMeet: true,
    divisionsList: [{ id: 'div-1', display_name: 'Junior' }],
    companionRelationsList: [{ id: 'rel-parent', title: 'Parent' }],
    availableFamilies: [],
    selectedMeetSlug: 'sunday-school',
  };

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [],
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders companion title properly based on index', () => {
    const wrapper = mount(CompanionFormCard, {
      props: defaultProps,
    });
    expect(wrapper.find('.companion-title-text').text()).toBe('Companion 1');
  });

  describe('Candidate matches and link button', () => {
    it('renders candidate pill and active link button when no other family is linked', async () => {
      const cand = {
        id: 'cand-101',
        name: 'David HaMelech',
        latest_family_id: 'fam-1',
        latest_family_name: 'David Family',
      };
      const wrapper = mount(CompanionFormCard, {
        props: {
          ...defaultProps,
          companion: createMockCompanion({
            candidateMatches: [cand],
          }),
          hasOtherLinkedFamily: false,
        },
      });

      const linkBtn = wrapper.find('button.link-candidate-btn');
      expect(linkBtn.exists()).toBe(true);
      expect(linkBtn.attributes('disabled')).toBeUndefined();
      expect(linkBtn.classes()).toContain('btn-danger');
      expect(linkBtn.attributes('title')).toBe('Copy & link to this record');

      await linkBtn.trigger('click');
      expect(wrapper.emitted('adoptCandidate')).toBeTruthy();
      expect(wrapper.emitted('adoptCandidate')![0]).toEqual([cand]);
    });

    it('disables link button with gray styling and warning tooltip when another family is already linked', async () => {
      const cand = {
        id: 'cand-101',
        name: 'David HaMelech',
        latest_family_id: 'fam-1',
        latest_family_name: 'David Family',
      };
      const wrapper = mount(CompanionFormCard, {
        props: {
          ...defaultProps,
          companion: createMockCompanion({
            candidateMatches: [cand],
          }),
          hasOtherLinkedFamily: true,
          linkedFamilyId: 'fam-other',
          linkedFamilyName: 'Refef Family',
        },
      });

      const linkBtn = wrapper.find('button.link-candidate-btn');
      expect(linkBtn.exists()).toBe(true);
      expect(linkBtn.attributes('disabled')).toBeDefined();
      expect(linkBtn.classes()).toContain('btn-secondary');
      expect(linkBtn.attributes('title')).toContain('Cannot link: Only one family can be linked per registration');
      expect(linkBtn.attributes('title')).toContain('Refef Family');

      await linkBtn.trigger('click');
      expect(wrapper.emitted('adoptCandidate')).toBeFalsy();
    });
  });

  describe('Linked candidate badge and unlinking', () => {
    it('displays linked badge and handles unlink click', async () => {
      const wrapper = mount(CompanionFormCard, {
        props: {
          ...defaultProps,
          companion: createMockCompanion({
            attendee_id: 'att-55',
            linkedCandidate: {
              id: 'att-55',
              name: 'John Doe',
              latest_family_name: 'Doe Family',
            },
          }),
        },
      });

      const badge = wrapper.find('.linked-candidate-badge');
      expect(badge.exists()).toBe(true);
      expect(badge.text()).toContain('Linked: John Doe');
      expect(badge.text()).toContain('Doe Family');

      const unlinkBtn = wrapper.find('.unlink-candidate-btn');
      expect(unlinkBtn.exists()).toBe(true);

      await unlinkBtn.trigger('click');
      expect(wrapper.emitted('unlinkCandidate')).toBeTruthy();
    });
  });

  describe('Contact actions', () => {
    it('emits addContact when plus button is clicked', async () => {
      const wrapper = mount(CompanionFormCard, {
        props: defaultProps,
      });

      const addBtn = wrapper.find('.add-contact-btn');
      await addBtn.trigger('click');
      expect(wrapper.emitted('addContact')).toBeTruthy();
      expect(wrapper.emitted('addContact')![0]).toEqual([0]);
    });

    it('emits removeContact when minus button is clicked on secondary contact', async () => {
      const wrapper = mount(CompanionFormCard, {
        props: {
          ...defaultProps,
          companion: createMockCompanion({
            contacts: [
              { type: 'phone', value: '111' },
              { type: 'email', value: 'a@b.com' },
            ],
          }),
        },
      });

      const removeBtns = wrapper.findAll('.remove-contact-btn');
      expect(removeBtns.length).toBe(1);
      await removeBtns[0].trigger('click');
      expect(wrapper.emitted('removeContact')).toBeTruthy();
      expect(wrapper.emitted('removeContact')![0]).toEqual([1]);
    });
  });

  describe('Companion removal', () => {
    it('emits removeCompanion when close button in header is clicked', async () => {
      const wrapper = mount(CompanionFormCard, {
        props: {
          ...defaultProps,
          index: 1,
          companionsCount: 2,
        },
      });

      const removeCompBtn = wrapper.find('.remove-companion-btn');
      expect(removeCompBtn.exists()).toBe(true);
      await removeCompBtn.trigger('click');
      expect(wrapper.emitted('removeCompanion')).toBeTruthy();
      expect(wrapper.emitted('removeCompanion')![0]).toEqual([1]);
    });
  });
});
