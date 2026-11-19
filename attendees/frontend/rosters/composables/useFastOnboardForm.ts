import { ref, computed } from 'vue';
import notify from 'devextreme/ui/notify';
import {
  Endpoints,
  ContactItem,
  AttendeeFormItem,
  CompanionFormItem,
  FamilyOption
} from '../types';
import {
  charactersMap,
  WARNING_NOTIFY_TIME,
  SUCCESS_NOTIFY_TIME
} from './useLookups';

let nextLocalId = 1;
/**
 * Generates a unique temporary local ID for Vue template v-for key tracking.
 * @returns Unique string ID with timestamp and sequence counter.
 */
export const genLocalId = (): string => `local_${Date.now()}_${nextLocalId++}`;

/**
 * Parses raw candidate contacts data from backend (JSON string, array, or key-value object)
 * into a standardized list of ContactItem objects.
 * @param contacts Raw contacts payload from candidate search.
 * @returns Array of normalized ContactItem objects.
 */
export const parseCandidateContacts = (contacts: any): ContactItem[] => {
  if (!contacts) return [];
  let cData = contacts;
  if (typeof cData === 'string') {
    try {
      cData = JSON.parse(cData);
    } catch {
      const trimmed = cData.trim();
      if (trimmed.includes('@')) {
        return [{ type: 'email', value: trimmed }];
      } else if (trimmed) {
        return [{ type: 'phone', value: trimmed }];
      }
      return [];
    }
  }
  if (Array.isArray(cData)) {
    return cData.map(c => {
      if (!c) return null;
      if (typeof c === 'string') {
        const trimmed = c.trim();
        return trimmed.includes('@') ? { type: 'email', value: trimmed } : { type: 'phone', value: trimmed };
      }
      return (c.value || c.contact_value) ? {
        type: (c.type || c.contact_type || 'phone').toLowerCase(),
        value: String(c.value || c.contact_value).trim()
      } : null;
    }).filter(Boolean) as ContactItem[];
  }
  if (typeof cData === 'object' && cData !== null) {
    const list: ContactItem[] = [];
    for (const [key, rawVal] of Object.entries(cData)) {
      if (!rawVal) continue;
      const val = String(rawVal).trim();
      if (!val) continue;

      const k = key.toLowerCase();
      let type = 'phone';
      if (k.includes('email') || val.includes('@')) {
        type = 'email';
      } else if (k.includes('wechat')) {
        type = 'wechat';
      } else if (k.includes('whatsapp')) {
        type = 'whatsapp';
      } else if (k.includes('line')) {
        type = 'line';
      } else if (k.includes('phone') || k.includes('tel') || k.includes('cell') || k.includes('mobile')) {
        type = 'phone';
      }
      list.push({ type, value: val });
    }
    const typePriority: Record<string, number> = { phone: 1, whatsapp: 2, email: 3, wechat: 4, line: 5 };
    list.sort((a, b) => (typePriority[a.type] || 99) - (typePriority[b.type] || 99));
    return list;
  }
  return [];
};

/**
 * Returns a masked phone number string to protect privacy (e.g. ***-**89).
 * @param contacts Candidate contacts payload.
 * @returns Masked phone string.
 */
export const getMaskedPhone = (contacts: any): string => {
  if (!contacts) return '';
  const entries = parseCandidateContacts(contacts);
  const phoneEntry = entries.find(e => e.type === 'phone' || e.type === 'whatsapp');
  if (!phoneEntry || !phoneEntry.value) return '';
  const digits = phoneEntry.value.replace(/\D/g, '');
  return digits.length >= 2 ? `***-**${digits.slice(-2)}` : '***';
};

/**
 * Builds a readable subtitle summary string for a candidate search card
 * containing gender, grade, age, masked phone, and guardians.
 * @param cand Candidate object.
 * @returns Readable summary string.
 */
export const getCandidateSubtitle = (cand: any): string => {
  const parts: string[] = [];
  if (cand.gender && cand.gender !== 'unspecified') {
    parts.push(`Gender: ${cand.gender.charAt(0).toUpperCase() + cand.gender.slice(1)}`);
  }
  if (cand.grade_name) parts.push(`Grade: ${cand.grade_name}`);
  if (cand.age !== null && cand.age !== undefined) parts.push(`Age: ${cand.age}`);
  const maskedPhone = getMaskedPhone(cand.contacts);
  if (maskedPhone) parts.push(`Phone: ${maskedPhone}`);
  if (cand.guardians) parts.push(`Guardian: ${cand.guardians}`);
  return parts.join(' | ') || 'No additional info';
};

/**
 * Validates a single contact entry (phone requires >=10 digits, email requires '@' and '.').
 * @param type Contact type (e.g. 'phone', 'email', 'wechat').
 * @param val Contact value string.
 * @param targetName Label name of the target entity for error message.
 * @returns Error message string, or null if validation passes.
 */
export const getContactValidationError = (type: string, val: string, targetName = 'Contact'): string | null => {
  if (!(window as any).Attendees?.utilities) return null;
  const normType = (type || 'phone').toLowerCase();
  if (normType === 'phone' || normType === 'whatsapp') {
    if (!(window as any).Attendees.utilities.validateFastInputPhoneNumber(val)) {
      return `${targetName} phone number must contain at least 10 digits.`;
    }
  } else if (normType === 'email') {
    if (!(window as any).Attendees.utilities.validateFastInputEmail(val)) {
      return `${targetName} email must be at least 5 characters and contain '@' and '.'.`;
    }
  } else {
    if (!(window as any).Attendees.utilities.validateFastInputContact(type, val)) {
      return `${targetName} account must be at least 2 characters.`;
    }
  }
  return null;
};

/**
 * Calculates the maximum number of valid calendar days in a given month and year,
 * properly handling leap years for February (defaults to leap year 2000 if year is empty).
 * @param yearStr Year string or number.
 * @param monthStr Month string or number (1-12).
 * @returns Maximum valid days (28, 29, 30, or 31).
 */
export const getMaxDaysInMonth = (yearStr: any, monthStr: any): number => {
  const m = parseInt(String(monthStr ?? ''), 10);
  if (isNaN(m) || m < 1 || m > 12) return 31;
  if (m === 2) {
    const yStr = String(yearStr ?? '').trim();
    const y = parseInt(yStr, 10);
    if (!yStr || isNaN(y)) {
      return 29; // default to leap year (2000) when year is unspecified
    }
    const isLeap = (y % 4 === 0 && y % 100 !== 0) || (y % 400 === 0);
    return isLeap ? 29 : 28;
  }
  if ([4, 6, 9, 11].includes(m)) return 30;
  return 31;
};

/**
 * Creates a fresh attendee form item initialized with default field values.
 * @param meetDivisionId Division ID assigned to current meet, if any.
 * @param divisionsList List of available organizational divisions.
 * @param rawRelationsList List of raw relations.
 * @returns Initialized AttendeeFormItem.
 */
export const createDefaultAttendee = (
  meetDivisionId: string | number | null,
  divisionsList: any[],
  rawRelationsList: any[]
): AttendeeFormItem => {
  const defaultDiv = meetDivisionId
    ? String(meetDivisionId)
    : (divisionsList.length === 1 ? String(divisionsList[0].id) : '');

  const selfRel = rawRelationsList.find(r => (r.title || '').trim().toLowerCase() === 'self');
  const defaultRel = selfRel ? String(selfRel.id) : (rawRelationsList.length > 0 ? String(rawRelationsList[0].id) : 'self');

  return {
    id: genLocalId(),
    attendee_id: null,
    linkedCandidate: null,
    division_id: defaultDiv,
    family_id: '',
    relationship: defaultRel,
    first_name: '',
    last_name: '',
    first_name2: '',
    last_name2: '',
    gender: 'UNSPECIFIED',
    byear: '',
    bmonth: '',
    bday: '',
    contacts: [{ type: 'phone', value: '' }],
    grade: '',
    food_pref: '',
    insurer: '',
    candidateMatches: []
  };
};

/**
 * Creates a fresh companion/guardian form item initialized with default field values.
 * @param divisionsList List of available organizational divisions.
 * @param isKidMeet Whether the current meet is for children.
 * @param familyRelationsList List of family relationships.
 * @returns Initialized CompanionFormItem.
 */
export const createDefaultCompanion = (
  divisionsList: any[],
  isKidMeet: boolean,
  familyRelationsList: any[]
): CompanionFormItem => {
  const defaultDiv = divisionsList.length === 1 ? String(divisionsList[0].id) : '';
  const targetRelTitle = isKidMeet ? 'parent' : 'spouse';
  const matchRel = familyRelationsList.find(r => (r.title || '').trim().toLowerCase() === targetRelTitle);
  const defaultRel = matchRel ? String(matchRel.id) : (familyRelationsList.length > 0 ? String(familyRelationsList[0].id) : 'parent');

  return {
    id: genLocalId(),
    attendee_id: null,
    linkedCandidate: null,
    division_id: defaultDiv,
    family_id: '',
    relationship: defaultRel,
    first_name: '',
    last_name: '',
    first_name2: '',
    last_name2: '',
    gender: 'UNSPECIFIED',
    contacts: [{ type: 'phone', value: '' }],
    candidateMatches: [],
    removedInAdultMeet: false
  };
};

/**
 * Adopts and copies demographic and contact attributes from a search candidate into a form item.
 * @param item Target Attendee or Companion form item.
 * @param cand Matched candidate record from search API.
 * @param isCompanion Whether the target item is a companion.
 * @param relList Relations list used to resolve matching relationship ID.
 */
export const adoptCandidateIntoFormItem = (
  item: any,
  cand: any,
  isCompanion: boolean,
  relList: any[]
): void => {
  item.attendee_id = cand.id;
  item.linkedCandidate = cand;
  item.candidateMatches = [];

  item.first_name = cand.first_name || '';
  item.last_name = cand.last_name || '';
  item.first_name2 = cand.first_name2 || '';
  item.last_name2 = cand.last_name2 || '';

  item.gender = cand.gender ? String(cand.gender).toUpperCase() : 'UNSPECIFIED';
  if (cand.division_id) {
    item.division_id = String(cand.division_id);
  }

  let matchedRel = false;
  if (cand.role_id) {
    const rId = String(cand.role_id);
    if (relList.some(r => String(r.id) === rId)) {
      item.relationship = rId;
      matchedRel = true;
    }
  }
  if (!matchedRel && cand.role_title) {
    const norm = cand.role_title.trim().toLowerCase();
    const opt = relList.find(r => (r.title || r.label || '').trim().toLowerCase() === norm || String(r.id).toLowerCase() === norm);
    if (opt) {
      item.relationship = String(opt.id);
      matchedRel = true;
    }
  }
  if (!matchedRel && Array.isArray(cand.folks)) {
    for (const folk of cand.folks) {
      if (folk.role_id) {
        const rId = String(folk.role_id);
        if (relList.some(r => String(r.id) === rId)) {
          item.relationship = rId;
          matchedRel = true;
          break;
        }
      }
      if (folk.role_title) {
        const norm = folk.role_title.trim().toLowerCase();
        const opt = relList.find(r => (r.title || r.label || '').trim().toLowerCase() === norm || String(r.id).toLowerCase() === norm);
        if (opt) {
          item.relationship = String(opt.id);
          matchedRel = true;
          break;
        }
      }
    }
  }

  if (!isCompanion) {
    item.grade = (cand.grade_index !== null && cand.grade_index !== undefined) ? String(cand.grade_index) : '';
    item.food_pref = cand.food_pref || '';
    item.insurer = cand.insurer || '';
    if (cand.actual_birthday) {
      const parts = cand.actual_birthday.split('-');
      if (parts.length === 3) {
        item.byear = parts[0];
        item.bmonth = String(parseInt(parts[1], 10));
        item.bday = String(parseInt(parts[2], 10));
      } else {
        item.byear = '';
        item.bmonth = '';
        item.bday = '';
      }
    } else {
      item.byear = '';
      item.bmonth = '';
      item.bday = '';
    }
  }

  const candContacts = parseCandidateContacts(cand.contacts);
  if (candContacts.length > 0) {
    item.contacts = candContacts.map(c => ({ type: c.type, value: c.value }));
  } else {
    item.contacts = [{ type: 'phone', value: '' }];
  }

  item.family_id = cand.latest_family_id ? String(cand.latest_family_id) : '';
};

/**
 * Composable for managing fast onboarding form reactive state, card operations, and submission.
 * @param endpoints System REST API endpoints configuration.
 */
export function useFastOnboardForm(endpoints: Endpoints) {
  const attendees = ref<AttendeeFormItem[]>([]);
  const companions = ref<CompanionFormItem[]>([]);
  const guardianCollapsed = ref(true);
  const unaccompaniedMinor = ref(false);
  const isSubmitting = ref(false);

  /**
   * Computes available family options across all linked candidates from attendees and companions.
   */
  const availableFamilies = computed<FamilyOption[]>(() => {
    const linkedCandidates: any[] = [];
    attendees.value.forEach(a => {
      if (a.attendee_id && a.linkedCandidate) linkedCandidates.push(a.linkedCandidate);
    });
    companions.value.forEach(c => {
      if (c.attendee_id && c.linkedCandidate) linkedCandidates.push(c.linkedCandidate);
    });

    const familyMap = new Map<string, FamilyOption>();
    linkedCandidates.forEach(cand => {
      if (Array.isArray(cand.folks)) {
        cand.folks.forEach((f: any) => {
          if (f.category_id === 0 && f.id) {
            if (!familyMap.has(String(f.id))) {
              familyMap.set(String(f.id), {
                id: f.id,
                name: f.name || 'Family',
                created: f.created || '',
                members: [cand.name],
                is_latest: Boolean(f.is_latest_family)
              });
            } else {
              const existing = familyMap.get(String(f.id))!;
              if (!existing.members.includes(cand.name)) {
                existing.members.push(cand.name);
              }
              if (f.is_latest_family) existing.is_latest = true;
            }
          }
        });
      }
    });

    const families = Array.from(familyMap.values());
    families.sort((a, b) => {
      if (a.is_latest && !b.is_latest) return -1;
      if (!a.is_latest && b.is_latest) return 1;
      return (b.created || '').localeCompare(a.created || '');
    });
    return families;
  });

  /**
   * Adds an additional Attendee form card.
   */
  const addAttendee = (meetDivisionId: any, divisionsList: any[], rawRelationsList: any[]) => {
    attendees.value.push(createDefaultAttendee(meetDivisionId, divisionsList, rawRelationsList));
  };

  /**
   * Removes an Attendee form card by index (index 0 is protected).
   */
  const removeAttendee = (index: number) => {
    if (index > 0) {
      attendees.value.splice(index, 1);
    }
  };

  /**
   * Appends a new contact row to a specific Attendee.
   */
  const addAttendeeContact = (att: AttendeeFormItem, cIndex: number) => {
    att.contacts.splice(cIndex + 1, 0, { type: 'phone', value: '' });
  };

  /**
   * Removes a contact row from a specific Attendee by index.
   */
  const removeAttendeeContact = (att: AttendeeFormItem, cIndex: number) => {
    if (cIndex > 0) {
      att.contacts.splice(cIndex, 1);
    }
  };

  /**
   * Adds an additional Companion form card.
   */
  const addCompanion = (divisionsList: any[], isKidMeet: boolean, familyRelationsList: any[]) => {
    if (guardianCollapsed.value) {
      guardianCollapsed.value = false;
    }
    if (companions.value[0]?.removedInAdultMeet) {
      companions.value[0].removedInAdultMeet = false;
      return;
    }
    companions.value.push(createDefaultCompanion(divisionsList, isKidMeet, familyRelationsList));
  };

  /**
   * Removes a Companion form card by index.
   */
  const removeCompanion = (index: number) => {
    if (index > 0) {
      companions.value.splice(index, 1);
    }
  };

  /**
   * Handles removal of Companion 1 in adult meets (shifts companion 2 or resets and hides).
   */
  const removeCompanion1 = () => {
    if (companions.value.length > 1) {
      companions.value.shift();
    } else {
      const comp = companions.value[0];
      if (comp) {
        comp.attendee_id = null;
        comp.linkedCandidate = null;
        comp.first_name = '';
        comp.last_name = '';
        comp.first_name2 = '';
        comp.last_name2 = '';
        comp.gender = 'UNSPECIFIED';
        comp.contacts = [{ type: 'phone', value: '' }];
        comp.candidateMatches = [];
        comp.removedInAdultMeet = true;
      }
      guardianCollapsed.value = true;
    }
  };

  /**
   * Appends a new contact row to a specific Companion.
   */
  const addCompanionContact = (comp: CompanionFormItem, ctIdx: number) => {
    comp.contacts.splice(ctIdx + 1, 0, { type: 'phone', value: '' });
  };

  /**
   * Removes a contact row from a specific Companion by index.
   */
  const removeCompanionContact = (comp: CompanionFormItem, ctIdx: number) => {
    if (ctIdx > 0) {
      comp.contacts.splice(ctIdx, 1);
    }
  };

  /**
   * Toggles the collapse state of the Companion / Guardian form section.
   */
  const toggleGuardianSection = (isKidMeet: boolean) => {
    guardianCollapsed.value = !guardianCollapsed.value;
    if (!guardianCollapsed.value && companions.value[0]?.removedInAdultMeet && !isKidMeet) {
      companions.value[0].removedInAdultMeet = false;
    }
  };

  /**
   * Determines whether a companion at the given index should be rendered on screen.
   */
  const isCompanionVisible = (cIdx: number): boolean => {
    if (unaccompaniedMinor.value) return false;
    if (cIdx === 0) {
      if (companions.value[0]?.removedInAdultMeet) return false;
      return true;
    }
    return true;
  };

  /**
   * Resets form items and collapses companion section according to meet type.
   */
  const resetForm = (
    meetDivisionId: any,
    divisionsList: any[],
    rawRelationsList: any[],
    familyRelationsList: any[],
    isKidMeet: boolean
  ) => {
    unaccompaniedMinor.value = false;
    guardianCollapsed.value = !isKidMeet;
    attendees.value = [createDefaultAttendee(meetDivisionId, divisionsList, rawRelationsList)];
    companions.value = [createDefaultCompanion(divisionsList, isKidMeet, familyRelationsList)];
  };

  /**
   * Highlights a form field with validation error classes (.is-invalid, .dx-invalid),
   * scrolls it into view, and focuses it.
   * Automatically clears the invalid styling on the next input/change event.
   */
  const markFieldInvalid = (selector: string | HTMLElement, rootEl?: HTMLElement | null) => {
    let el: HTMLElement | null = null;
    if (typeof selector === 'string') {
      const root = rootEl || document.querySelector('.onboard-view-container') || document;
      el = root.querySelector(selector) as HTMLElement | null;
    } else {
      el = selector;
    }
    if (!el) return;

    el.classList.add('is-invalid', 'dx-invalid');
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    try {
      el.focus();
    } catch (err) {
      // Ignore when element is not focusable
    }

    const clearHandler = () => {
      el?.classList.remove('is-invalid', 'dx-invalid');
      el?.removeEventListener('input', clearHandler);
      el?.removeEventListener('change', clearHandler);
    };
    el.addEventListener('input', clearHandler, { once: true });
    el.addEventListener('change', clearHandler, { once: true });
  };

  /**
   * Highlights all four name fields with validation error classes (.is-invalid, .dx-invalid)
   * when none of them is provided.
   * Clears the invalid styling across all four fields as soon as any of them receives input.
   */
  const markNameFieldsInvalid = (blockSelector: string, isCompanion = false) => {
    const prefix = isCompanion ? '.ob-p-' : '.ob-';
    const fieldSelectors = [
      `${blockSelector} ${prefix}first-name`,
      `${blockSelector} ${prefix}last-name`,
      `${blockSelector} ${prefix}last-name2`,
      `${blockSelector} ${prefix}first-name2`
    ];

    const elements: HTMLElement[] = [];
    fieldSelectors.forEach((sel) => {
      const el = document.querySelector(sel) as HTMLElement | null;
      if (el) {
        el.classList.add('is-invalid', 'dx-invalid');
        elements.push(el);
      }
    });

    if (elements.length > 0) {
      elements[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      try {
        elements[0].focus();
      } catch (err) {
        // Ignore when element is not focusable
      }
    }

    const clearAllNameFields = () => {
      elements.forEach((el) => {
        el.classList.remove('is-invalid', 'dx-invalid');
        el.removeEventListener('input', clearAllNameFields);
        el.removeEventListener('change', clearAllNameFields);
      });
    };

    elements.forEach((el) => {
      el.addEventListener('input', clearAllNameFields, { once: true });
      el.addEventListener('change', clearAllNameFields, { once: true });
    });
  };

  /**
   * Removes validation highlight classes from all elements in the modal.
   */
  const clearAllInvalidFields = () => {
    document.querySelectorAll('.is-invalid, .dx-invalid').forEach((el) => {
      el.classList.remove('is-invalid', 'dx-invalid');
    });
  };

  /**
   * Validates form inputs and executes the POST fast onboarding API request.
   */
  const submitFastOnboard = async (params: {
    currentMeet: any;
    selectedMeetSlug: string;
    selectedGatheringId: string | null;
    isKidMeet: boolean;
    showInsurer: boolean;
    divisionsList: any[];
    onSuccess: (result: any) => Promise<void> | void;
  }): Promise<boolean> => {
    const { currentMeet, selectedMeetSlug, selectedGatheringId, isKidMeet, showInsurer, divisionsList, onSuccess } = params;

    clearAllInvalidFields();

    if (!currentMeet) {
      notify('Please select a valid meet.', 'error', WARNING_NOTIFY_TIME);
      return false;
    }

    if (attendees.value.length === 0) {
      notify('Please provide at least one attendee.', 'warning', WARNING_NOTIFY_TIME);
      return false;
    }

    const isKid = isKidMeet;
    const isUnaccompanied = isKid && unaccompaniedMinor.value;
    const attendeesList: any[] = [];

    for (let aIdx = 0; aIdx < attendees.value.length; aIdx++) {
      const att = attendees.value[aIdx];
      const attNum = aIdx + 1;
      const attLabel = attendees.value.length > 1 ? `Attendee ${attNum}` : 'Attendee';

      if (divisionsList.length > 0 && !att.division_id) {
        notify(`Please select a division for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
        markFieldInvalid(`.attendee-block-${attNum} .ob-division`);
        return false;
      }

      const firstName = String(att.first_name || '').trim();
      const lastName = String(att.last_name || '').trim();
      const firstName2 = String(att.first_name2 || '').trim();
      const lastName2 = String(att.last_name2 || '').trim();
      const gender = (att.gender || 'UNSPECIFIED').toUpperCase();

      const byear = String(att.byear || '').trim();
      const bmonth = String(att.bmonth || '').trim();
      const bday = String(att.bday || '').trim();

      if (!firstName && !lastName && !firstName2 && !lastName2) {
        notify(`At least one name (English or other language) is required for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
        markNameFieldsInvalid(`.attendee-block-${attNum}`, false);
        return false;
      }

      if (isKid) {
        if (!byear || !bmonth || !bday) {
          notify(`Year, Month, and Day of birth are all required for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
          if (!bday) markFieldInvalid(`.attendee-block-${attNum} .ob-bday`);
          if (!bmonth) markFieldInvalid(`.attendee-block-${attNum} .ob-bmonth`);
          if (!byear) markFieldInvalid(`.attendee-block-${attNum} .ob-byear`);
          return false;
        }
      }

      if (byear || bmonth || bday) {
        const bValid = (window as any).Attendees?.utilities?.validateFastInputBirthday
          ? (window as any).Attendees.utilities.validateFastInputBirthday(byear, bmonth, bday)
          : { valid: true };
        if (!bValid.valid) {
          notify(`${attLabel}: ${bValid.message}`, 'warning', WARNING_NOTIFY_TIME);
          if (byear) {
            markFieldInvalid(`.attendee-block-${attNum} .ob-byear`);
          } else if (bmonth) {
            markFieldInvalid(`.attendee-block-${attNum} .ob-bmonth`);
          } else {
            markFieldInvalid(`.attendee-block-${attNum} .ob-bday`);
          }
          return false;
        }
      }

      const processedContacts: ContactItem[] = [];
      for (let cIdx = 0; cIdx < att.contacts.length; cIdx++) {
        const c = att.contacts[cIdx];
        let cVal = String(c.value || '').trim();
        if (cVal) {
          const vErr = getContactValidationError(c.type, cVal, attLabel);
          if (vErr) {
            notify(vErr, 'warning', WARNING_NOTIFY_TIME);
            const contactRows = document.querySelectorAll(`.attendee-block-${attNum} .contact-entry-row`);
            if (contactRows[cIdx]) {
              markFieldInvalid(contactRows[cIdx].querySelector('.ob-contact-value') as HTMLElement);
            }
            return false;
          }
          if ((c.type.toLowerCase() === 'phone' || c.type.toLowerCase() === 'whatsapp') && (window as any).Attendees?.utilities?.normalizePhoneNumber) {
            cVal = (window as any).Attendees.utilities.normalizePhoneNumber(cVal);
            c.value = cVal;
          }
          processedContacts.push({ type: c.type, value: cVal });
        }
      }
      const primaryContact = processedContacts.length > 0 ? processedContacts[0] : null;

      const grade = isKid ? att.grade : '';
      const foodPref = isKid ? String(att.food_pref || '').trim() : '';
      const insurer = (isKid && showInsurer) ? String(att.insurer || '').trim() : '';

      if (isKid) {
        if (grade === '' || grade === undefined || grade === null) {
          notify(`School Grade is required for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
          markFieldInvalid(`.attendee-block-${attNum} .ob-grade`);
          return false;
        }
        if (!foodPref) {
          notify(`Food preference / allergies is required for ${attLabel} (enter "None" if none).`, 'warning', WARNING_NOTIFY_TIME);
          markFieldInvalid(`.attendee-block-${attNum} .ob-food-pref`);
          return false;
        }
      }

      attendeesList.push({
        attendee_id: att.attendee_id || null,
        target_folk_id: (att.family_id && att.family_id !== '__NEW__') ? att.family_id : null,
        create_new_folk: att.family_id === '__NEW__',
        first_name: firstName || null,
        last_name: lastName || null,
        first_name2: firstName2 || null,
        last_name2: lastName2 || null,
        gender: gender,
        division_id: att.division_id ? parseInt(att.division_id, 10) : null,
        relationship: att.relationship ? (parseInt(att.relationship, 10) || att.relationship) : 'self',
        birthday_year: byear ? parseInt(byear, 10) : null,
        birthday_month: bmonth ? parseInt(bmonth, 10) : null,
        birthday_day: bday ? parseInt(bday, 10) : null,
        contact_type: primaryContact ? primaryContact.type : 'phone',
        contact_value: primaryContact ? primaryContact.value : null,
        contacts: processedContacts,
        grade: grade !== '' ? grade : null,
        food_pref: foodPref || null,
        insurer: insurer || null
      });
    }

    const companionsList: any[] = [];
    const activeCompanions = (!guardianCollapsed.value && !isUnaccompanied)
      ? companions.value.filter((_, idx) => isCompanionVisible(idx))
      : [];

    if (isKid) {
      if (!isUnaccompanied) {
        if (guardianCollapsed.value) {
          guardianCollapsed.value = false;
        }
        if (activeCompanions.length === 0) {
          notify('Companion information is required for kids unless "Child arrived alone" is checked.', 'warning', WARNING_NOTIFY_TIME);
          const addCompBtn = document.querySelector('.add-more-companion-btn');
          if (addCompBtn) markFieldInvalid(addCompBtn as HTMLElement);
          return false;
        }
        for (let i = 0; i < activeCompanions.length; i++) {
          const comp = activeCompanions[i];
          const compNum = i + 1;
          const pFirst = String(comp.first_name || '').trim();
          const pLast = String(comp.last_name || '').trim();
          const pFirst2 = String(comp.first_name2 || '').trim();
          const pLast2 = String(comp.last_name2 || '').trim();

          const compContacts: ContactItem[] = [];
          for (let cIdx = 0; cIdx < comp.contacts.length; cIdx++) {
            const c = comp.contacts[cIdx];
            let cv = String(c.value || '').trim();
            if (cv) {
              const cvErr = getContactValidationError(c.type, cv, `Companion ${compNum}`);
              if (cvErr) {
                notify(cvErr, 'warning', WARNING_NOTIFY_TIME);
                const contactRows = document.querySelectorAll(`.companion-block-${compNum} .contact-entry-row`);
                if (contactRows[cIdx]) {
                  markFieldInvalid(contactRows[cIdx].querySelector('.ob-p-contact-value') as HTMLElement);
                }
                return false;
              }
              if ((c.type.toLowerCase() === 'phone' || c.type.toLowerCase() === 'whatsapp') && (window as any).Attendees?.utilities?.normalizePhoneNumber) {
                cv = (window as any).Attendees.utilities.normalizePhoneNumber(cv);
                c.value = cv;
              }
              compContacts.push({ type: c.type, value: cv });
            }
          }

          const hasAnyName = Boolean(pFirst || pLast || pFirst2 || pLast2);
          const primaryCompContact = compContacts.length > 0 ? compContacts[0] : null;

          if (compNum === 1) {
            if (divisionsList.length > 0 && !comp.division_id) {
              notify('Please select a division for Companion 1.', 'warning', WARNING_NOTIFY_TIME);
              markFieldInvalid('.companion-block-1 .ob-p-division');
              return false;
            }
            if (!hasAnyName || compContacts.length === 0) {
              notify('Companion 1 name and contact information are required.', 'warning', WARNING_NOTIFY_TIME);
              if (!hasAnyName) {
                markNameFieldsInvalid('.companion-block-1', true);
              } else {
                markFieldInvalid('.companion-block-1 .ob-p-contact-value');
              }
              return false;
            }
          } else {
            if (!hasAnyName && compContacts.length === 0) {
              notify(`Companion ${compNum} name and contact information are required (or remove it).`, 'warning', WARNING_NOTIFY_TIME);
              markNameFieldsInvalid(`.companion-block-${compNum}`, true);
              return false;
            }
            if (divisionsList.length > 0 && !comp.division_id) {
              notify(`Please select a division for Companion ${compNum}.`, 'warning', WARNING_NOTIFY_TIME);
              markFieldInvalid(`.companion-block-${compNum} .ob-p-division`);
              return false;
            }
            if (!hasAnyName || compContacts.length === 0) {
              notify(`Companion ${compNum} name and contact information are required.`, 'warning', WARNING_NOTIFY_TIME);
              if (!hasAnyName) {
                markNameFieldsInvalid(`.companion-block-${compNum}`, true);
              } else {
                markFieldInvalid(`.companion-block-${compNum} .ob-p-contact-value`);
              }
              return false;
            }
          }

          companionsList.push({
            attendee_id: comp.attendee_id || null,
            target_folk_id: (comp.family_id && comp.family_id !== '__NEW__') ? comp.family_id : null,
            create_new_folk: comp.family_id === '__NEW__',
            first_name: pFirst || null,
            last_name: pLast || null,
            first_name2: pFirst2 || null,
            last_name2: pLast2 || null,
            gender: comp.gender || 'UNSPECIFIED',
            division_id: comp.division_id ? parseInt(comp.division_id, 10) : null,
            relationship: comp.relationship ? (parseInt(comp.relationship, 10) || comp.relationship) : 'parent',
            contact_type: primaryCompContact ? primaryCompContact.type : 'phone',
            contact_value: primaryCompContact ? primaryCompContact.value : null,
            phone: primaryCompContact && primaryCompContact.type === 'phone' ? primaryCompContact.value : null,
            email: primaryCompContact && primaryCompContact.type === 'email' ? primaryCompContact.value : null,
            contacts: compContacts
          });
        }
      }
    } else {
      if (activeCompanions.length > 0) {
        for (let i = 0; i < activeCompanions.length; i++) {
          const comp = activeCompanions[i];
          const compNum = i + 1;
          const pFirst = String(comp.first_name || '').trim();
          const pLast = String(comp.last_name || '').trim();
          const pFirst2 = String(comp.first_name2 || '').trim();
          const pLast2 = String(comp.last_name2 || '').trim();

          const compContacts: ContactItem[] = [];
          for (let cIdx = 0; cIdx < comp.contacts.length; cIdx++) {
            const c = comp.contacts[cIdx];
            let cv = String(c.value || '').trim();
            if (cv) {
              const cvErr = getContactValidationError(c.type, cv, `Companion ${compNum}`);
              if (cvErr) {
                notify(cvErr, 'warning', WARNING_NOTIFY_TIME);
                const contactRows = document.querySelectorAll(`.companion-block-${compNum} .contact-entry-row`);
                if (contactRows[cIdx]) {
                  markFieldInvalid(contactRows[cIdx].querySelector('.ob-p-contact-value') as HTMLElement);
                }
                return false;
              }
              if ((c.type.toLowerCase() === 'phone' || c.type.toLowerCase() === 'whatsapp') && (window as any).Attendees?.utilities?.normalizePhoneNumber) {
                cv = (window as any).Attendees.utilities.normalizePhoneNumber(cv);
                c.value = cv;
              }
              compContacts.push({ type: c.type, value: cv });
            }
          }

          const hasAnyName = Boolean(pFirst || pLast || pFirst2 || pLast2);
          const hasAnyContact = compContacts.length > 0;
          const primaryCompContact = compContacts.length > 0 ? compContacts[0] : null;

          if (activeCompanions.length === 1 && !hasAnyName && !hasAnyContact) {
            continue;
          }

          if (!hasAnyName) {
            notify(`Companion ${compNum} name is required (or remove it).`, 'warning', WARNING_NOTIFY_TIME);
            markNameFieldsInvalid(`.companion-block-${compNum}`, true);
            return false;
          }
          if (divisionsList.length > 0 && !comp.division_id) {
            notify(`Please select a division for Companion ${compNum}.`, 'warning', WARNING_NOTIFY_TIME);
            markFieldInvalid(`.companion-block-${compNum} .ob-p-division`);
            return false;
          }

          companionsList.push({
            attendee_id: comp.attendee_id || null,
            target_folk_id: (comp.family_id && comp.family_id !== '__NEW__') ? comp.family_id : null,
            create_new_folk: comp.family_id === '__NEW__',
            first_name: pFirst || null,
            last_name: pLast || null,
            first_name2: pFirst2 || null,
            last_name2: pLast2 || null,
            gender: comp.gender || 'UNSPECIFIED',
            division_id: comp.division_id ? parseInt(comp.division_id, 10) : null,
            relationship: comp.relationship ? (parseInt(comp.relationship, 10) || comp.relationship) : 'spouse',
            contact_type: primaryCompContact ? primaryCompContact.type : 'phone',
            contact_value: primaryCompContact ? primaryCompContact.value : null,
            phone: primaryCompContact && primaryCompContact.type === 'phone' ? primaryCompContact.value : null,
            email: primaryCompContact && primaryCompContact.type === 'email' ? primaryCompContact.value : null,
            contacts: compContacts
          });
        }
      }
    }

    const allFamVals = [
      ...attendees.value.map(a => a.family_id),
      ...companions.value.map(c => c.family_id)
    ].filter(Boolean);

    let targetFolkId: string | null = null;
    let createNewFolk = false;
    if (allFamVals.some(v => v === '__NEW__')) {
      createNewFolk = true;
    }
    const chosenFolkId = allFamVals.find(v => v && v !== '__NEW__');
    if (chosenFolkId) {
      targetFolkId = chosenFolkId;
    }

    const payload = {
      meet_slug: currentMeet.slug,
      gathering_id: selectedGatheringId || null,
      unaccompanied: isUnaccompanied,
      attendees_data: attendeesList,
      companions: companionsList,
      target_folk_id: targetFolkId,
      create_new_folk: createNewFolk
    };

    isSubmitting.value = true;
    if ((window as any).Attendees?.utilities) {
      (window as any).Attendees.utilities.editingEnabled = true;
    }

    try {
      const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value;
      const response = await fetch(endpoints.fastOnboard, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData.detail
          || errData.error
          || (typeof errData === 'object' && Object.values(errData).flat().join(' ').trim())
          || response.statusText
          || `Registration failed (HTTP ${response.status})`;
        throw new Error(errMsg);
      }

      const result = await response.json();
      await onSuccess(result);
      return true;
    } catch (err: any) {
      notify(err.message, 'error', WARNING_NOTIFY_TIME);
      return false;
    } finally {
      isSubmitting.value = false;
      if ((window as any).Attendees?.utilities) {
        (window as any).Attendees.utilities.editingEnabled = false;
      }
    }
  };

  return {
    attendees,
    companions,
    guardianCollapsed,
    unaccompaniedMinor,
    isSubmitting,
    availableFamilies,
    addAttendee,
    removeAttendee,
    addAttendeeContact,
    removeAttendeeContact,
    addCompanion,
    removeCompanion,
    removeCompanion1,
    addCompanionContact,
    removeCompanionContact,
    toggleGuardianSection,
    isCompanionVisible,
    resetForm,
    submitFastOnboard
  };
}
