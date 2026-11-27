import { ref, reactive } from 'vue';
import { Gathering, MeetInfo } from '../types';

export const MAX_DATE_RANGE_YEARS = 5;
export const WARNING_NOTIFY_TIME = 5000;
export const SUCCESS_NOTIFY_TIME = 3000;
export const SYNC_POLLING_INTERVAL = 15000;

export const gatheringsRegistry = new Map<string, Gathering>();
export const meetsInfoMap = reactive(new Map<string | number, MeetInfo>());
export const meetsMap = reactive(new Map<string | number, MeetInfo>());
export const charactersMap = new Map<string | number, any>();
const meetGatheringsCache = new Map<string, Gathering[]>();

/**
 * Escapes HTML characters in string.
 * @param str Input string or value.
 */
export const escapeHtml = (str: any): string => {
  return (window as any).Attendees?.utilities?.escapeHtml
    ? (window as any).Attendees.utilities.escapeHtml(str)
    : String(str || '');
};

/**
 * Adds years to a date.
 * @param date Base date.
 * @param years Number of years to add.
 */
export const addYears = (date: any, years: number): Date | null => {
  if (!date) return null;
  const d = new Date(date);
  if (isNaN(d.getTime())) return null;
  d.setFullYear(d.getFullYear() + years);
  return d;
};

/**
 * Adds months to a date, clamping overflow days.
 * @param date Base date.
 * @param months Number of months to add.
 */
export const addMonths = (date: any, months: number): Date | null => {
  if (!date) return null;
  const d = new Date(date);
  if (isNaN(d.getTime())) return null;
  const currentDay = d.getDate();
  d.setMonth(d.getMonth() + months);
  if (d.getDate() !== currentDay) {
    d.setDate(0); // If day overflowed, set to last day of target month
  }
  return d;
};

/**
 * Validates whether a value is a valid date.
 * @param date Value to check.
 */
export const isValidDate = (date: any): boolean => {
  if (!date) return false;
  const d = new Date(date);
  return !isNaN(d.getTime());
};

/**
 * Retrieves signature requirement config for a meet ID.
 * @param meetId Meet ID.
 */
export const getMeetSignatureRequiredAt = (meetId: any): any => {
  if (!meetId) return null;
  const m = meetsMap.get(meetId) || meetsMap.get(String(meetId));
  return (m && m.infos) ? m.infos.signature_required_at : null;
};

export let isProgrammaticGradeChange = false;
/**
 * Sets flag indicating programmatic grade change to prevent triggering change handlers.
 * @param val Boolean flag value.
 */
export const setIsProgrammaticGradeChange = (val: boolean) => {
  isProgrammaticGradeChange = val;
};

/**
 * Retrieves user preference for grade column visibility from session storage.
 */
export const getUserGradeVisiblePreference = (): boolean | null => {
  const storageOptsKey = (window as any).Attendees?.utilities?.datagridStorageKeys?.['rostersListViewOpts'];
  if (!storageOptsKey) return null;
  const val = (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'userGradeVisible');
  if (val === true || val === 'true') return true;
  if (val === false || val === 'false') return false;
  return null;
};

/**
 * Persists user preference for grade column visibility into session storage.
 * @param val Boolean or null preference value.
 */
export const setUserGradeVisiblePreference = (val: boolean | null | undefined): void => {
  const storageOptsKey = (window as any).Attendees?.utilities?.datagridStorageKeys?.['rostersListViewOpts'];
  if (!storageOptsKey) return;
  if (val === null || val === undefined) {
    try {
      const storedObject = JSON.parse(window.sessionStorage.getItem(storageOptsKey) || '{}');
      delete storedObject['userGradeVisible'];
      window.sessionStorage.setItem(storageOptsKey, JSON.stringify(storedObject));
    } catch (e) {
      console.error('Error clearing userGradeVisible in sessionStorage:', e);
    }
  } else {
    (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'userGradeVisible', Boolean(val));
  }
};

let meetsLoadingPromise: Promise<void> | null = null;

/**
 * Ensures all organization meets are loaded and mapped by id and slug.
 * @param meetsEndpoint Optional endpoint URL for organization meets.
 * @param requiredSlugs Optional list of meet slugs that must be present in meetsMap.
 */
export const ensureMeetsLoaded = async (meetsEndpoint?: string, requiredSlugs?: string[]): Promise<void> => {
  const hasValidMeet = (slug: string) => {
    const m = meetsMap.get(slug) || meetsMap.get(String(slug));
    const info = meetsInfoMap.get(slug) || meetsInfoMap.get(String(slug));
    return Boolean((m && (m.display_name || m.name)) || (info && typeof info === 'string' && info !== slug));
  };

  if (
    meetsMap.size > 0 &&
    (!requiredSlugs || requiredSlugs.length === 0 || requiredSlugs.every(hasValidMeet))
  ) {
    return;
  }

  if (meetsLoadingPromise) {
    await meetsLoadingPromise;
    if (!requiredSlugs || requiredSlugs.length === 0 || requiredSlugs.every(hasValidMeet)) {
      return;
    }
  }

  meetsLoadingPromise = (async () => {
    const baseUrl = meetsEndpoint || '/occasions/api/organization_meets/';
    const url = `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}take=9999`;
    try {
      const res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      }).then(r => r.json()).catch(() => ({}));
      const rawData = res.data || res.results || (Array.isArray(res) ? res : []);
      const processMeet = (m: any) => {
        if (!m) return;
        const displayName = m.display_name || m.name;
        if (m.id !== undefined && m.id !== null) {
          if (displayName) {
            meetsInfoMap.set(m.id, displayName);
            meetsInfoMap.set(String(m.id), displayName);
          }
          meetsMap.set(m.id, m);
          meetsMap.set(String(m.id), m);
        }
        if (m.slug) {
          const slugStr = String(m.slug);
          if (displayName) {
            meetsInfoMap.set(slugStr, displayName);
            meetsInfoMap.set(m.slug, displayName);
          }
          meetsMap.set(slugStr, m);
          meetsMap.set(m.slug, m);
        }
      };
      rawData.forEach((item: any) => {
        if (item && item.items && Array.isArray(item.items)) {
          item.items.forEach(processMeet);
        } else {
          processMeet(item);
        }
      });
    } catch (e) {
      console.error('Error ensuring meets loaded:', e);
    } finally {
      meetsLoadingPromise = null;
    }
  })();

  await meetsLoadingPromise;
};

/**
 * Checks whether any of the selected meet slugs is configured for kids (has grade).
 * @param selectedSlugs Array of meet slug strings.
 */
export const checkHasKidMeet = (selectedSlugs?: string[]): boolean => {
  const slugs = selectedSlugs || [];
  return slugs.some(slug => {
    const m = meetsMap.get(slug) || meetsMap.get(String(slug));
    const showInfos = m?.show_attendee_infos || (m?.infos && m.infos.show_attendee_infos) || {};
    return Boolean(showInfos['infos-grade'] || showInfos['grade']);
  });
};

/**
 * Resolves whether grade column should be visible, taking user preference into account.
 * @param selectedSlugs Array of meet slug strings.
 */
export const resolveGradeVisible = (selectedSlugs?: string[]): boolean => {
  const userChoice = getUserGradeVisiblePreference();
  if (userChoice !== null && userChoice !== undefined) {
    return userChoice;
  }
  return checkHasKidMeet(selectedSlugs);
};

/**
 * Returns a stable unique column identifier for a gathering object.
 * @param gathering Gathering entity or object.
 */
export const getColumnIdentifier = (gathering: Gathering | any | null): string => {
  return (gathering && gathering.id) ? String(gathering.id) : `future_${gathering ? gathering.meet_id : ''}_${gathering ? gathering.start : ''}`;
};

/**
 * Formats attendance count and enrolled count for header display.
 * @param count Checked in count.
 * @param enrolled Enrolled count.
 */
export const formatAttendanceDisplay = (count: number, enrolled?: number | null): string => {
  if (enrolled !== undefined && enrolled !== null && enrolled > 0) {
    return `${count}/${enrolled}`;
  }
  return String(count);
};

/**
 * Registers or updates a gathering object in gatheringsRegistry.
 * @param gathering Gathering entity to register.
 */
export const registerGathering = (gathering: Gathering | any | null): Gathering | null => {
  if (!gathering) return null;
  const meetStartKey = (gathering.meet_id && gathering.start) ? `${gathering.meet_id}_${gathering.start}` : '';
  let existing = (meetStartKey && gatheringsRegistry.get(meetStartKey)) || (gathering.id && gatheringsRegistry.get(String(gathering.id))) || null;
  if (!existing) {
    existing = {
      id: gathering.id || null,
      meet_id: gathering.meet_id,
      meet_display_name: gathering.meet_display_name || '',
      start: gathering.start,
      finish: gathering.finish,
      attendances_count: (gathering.attendances_count !== undefined) ? gathering.attendances_count : 0,
      enrolled_count: (gathering.enrolled_count !== undefined) ? gathering.enrolled_count : null,
    };
    if (meetStartKey) gatheringsRegistry.set(meetStartKey, existing);
  } else {
    if (gathering.id && !existing.id) existing.id = gathering.id;
    if (gathering.meet_id && !existing.meet_id) existing.meet_id = gathering.meet_id;
    if (gathering.meet_display_name && !existing.meet_display_name) existing.meet_display_name = gathering.meet_display_name;
    if (gathering.start && !existing.start) existing.start = gathering.start;
    if (gathering.finish && !existing.finish) existing.finish = gathering.finish;
    if (gathering.attendances_count !== undefined) existing.attendances_count = gathering.attendances_count;
    if (gathering.enrolled_count !== undefined) existing.enrolled_count = gathering.enrolled_count;
  }

  if (existing.id) {
    gatheringsRegistry.set(String(existing.id), existing);
  }
  const colId = getColumnIdentifier(existing);
  gatheringsRegistry.set(colId, existing);
  return existing;
};

export let sharedGradeConverter: Array<{ id: number; label: string }> = [];
/**
 * Loads organization grade converter list from DOM element.
 */
export const loadGradeConverter = (): Array<{ id: number; label: string }> => {
  const el = document.getElementById('organization-grade-converter');
  if (el) {
    try {
      const parsed = JSON.parse(el.textContent || '[]') || [];
      sharedGradeConverter = parsed.map((item: any, index: number) => {
        if (typeof item === 'object' && item !== null) return item;
        return { id: index, label: String(item) };
      });
    } catch (e) {
      sharedGradeConverter = [];
    }
  }
  return sharedGradeConverter;
};

export let sharedOrganizationDivisions: any[] = [];
/**
 * Loads organization divisions list from endpoint or DOM element.
 * @param divisionsEndpoint Optional API endpoint URL.
 */
export const loadOrganizationDivisions = async (divisionsEndpoint?: string): Promise<any[]> => {
  if (sharedOrganizationDivisions.length > 0) return sharedOrganizationDivisions;
  const url = (divisionsEndpoint || '/whereabouts/api/user_divisions/') + ((divisionsEndpoint || '').includes('?') ? '&take=999' : '?take=999');
  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    });
    if (res.ok) {
      const json = await res.json();
      const raw = json.data || (Array.isArray(json) ? json : []);
      if (Array.isArray(raw) && raw.length > 0) {
        sharedOrganizationDivisions = raw;
        return sharedOrganizationDivisions;
      }
    }
  } catch (e) {
    console.warn('Could not fetch divisions from API:', e);
  }
  const divisionsEl = document.getElementById('organization-divisions');
  if (divisionsEl) {
    try {
      sharedOrganizationDivisions = JSON.parse(divisionsEl.textContent || '[]') || [];
    } catch (e) {
      sharedOrganizationDivisions = [];
    }
  }
  return sharedOrganizationDivisions;
};

export let sharedFamilyRelations: any[] = [];
export let sharedRawRelations: any[] = [];
/**
 * Loads all organization family and interpersonal relations.
 * @param relationsEndpoint Optional API endpoint URL.
 */
export const loadFamilyRelations = async (relationsEndpoint?: string): Promise<any[]> => {
  if (sharedRawRelations.length > 0) return sharedRawRelations;
  const url = (relationsEndpoint || '/persons/api/all_relations/') + '?category_id=0&take=999';
  try {
    const res = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    });
    if (!res.ok) throw new Error('Failed to fetch relations');
    const json = await res.json();
    const rawList = json.data || (Array.isArray(json) ? json : []);
    const excludedRoles = new Set(['masked', 'hidden']);
    sharedRawRelations = rawList.filter((r: any) => r && r.id > 0 && !excludedRoles.has((r.title || '').trim().toLowerCase()));
    sharedFamilyRelations = sharedRawRelations.filter((r: any) => (r.title || '').trim().toLowerCase() !== 'self');
    return sharedRawRelations;
  } catch (e) {
    console.warn('Could not load relations from API, using fallback:', e);
    sharedRawRelations = [
      { id: 1, title: 'parent' },
      { id: 2, title: 'child' },
      { id: 3, title: 'son' },
      { id: 4, title: 'daughter' },
      { id: 5, title: 'husband' },
      { id: 6, title: 'wife' },
      { id: 14, title: 'spouse' },
      { id: 28, title: 'self' },
    ];
    sharedFamilyRelations = sharedRawRelations.filter((r: any) => r.title.toLowerCase() !== 'self');
    return sharedRawRelations;
  }
};

/**
 * Loads gatherings for a specified meet from cache, registry, or API.
 * @param meetSlug Optional meet slug string.
 * @param meetId Optional meet ID number or string.
 * @param gatheringsEndpoint Optional API endpoint URL.
 */
export const loadMeetGatherings = async (meetSlug?: string, meetId?: number | string, gatheringsEndpoint?: string): Promise<Gathering[]> => {
  if (!meetSlug && !meetId) return [];
  if (!meetId && meetSlug) {
    const m = meetsMap.get(meetSlug) || meetsMap.get(String(meetSlug));
    if (m && m.id) meetId = m.id;
  }
  const cacheKey = String(meetSlug || meetId);
  if (meetGatheringsCache.has(cacheKey) && (meetGatheringsCache.get(cacheKey)?.length || 0) > 0) {
    return meetGatheringsCache.get(cacheKey) || [];
  }

  const seen = new Set<string>();
  const result: Gathering[] = [];
  /**
   * Internal helper to register unique gathering in result.
   */
  const addG = (g: Gathering) => {
    if (!g) return;
    const idKey = g.id ? String(g.id) : (g.start ? `start_${g.start}` : null);
    if (idKey && !seen.has(idKey)) {
      seen.add(idKey);
      result.push(g);
    }
  };

  // 1. Gatherings from registry
  for (const g of gatheringsRegistry.values()) {
    if (g && ((meetId && String(g.meet_id) === String(meetId)) || (meetSlug && String((g as any).meet_slug) === String(meetSlug)))) {
      addG(g);
    }
  }

  // 2. Fetch from gatherings API for this meet if not found
  if (result.length === 0 && meetSlug) {
    const url = (gatheringsEndpoint || '/occasions/api/organization_team_gatherings/') + `?meets[]=${encodeURIComponent(meetSlug)}&take=999`;
    try {
      const res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      });
      if (res.ok) {
        const json = await res.json();
        const items = json.data || (Array.isArray(json) ? json : []);
        items.forEach((item: any) => {
          addG({
            id: item.id,
            meet_id: meetId || item.meet_id,
            meet_display_name: item.meet_display_name || '',
            start: item.start,
            finish: item.finish,
          });
        });
      }
    } catch (e) {
      console.warn('Could not fetch gatherings for meet from API:', e);
    }
  }

  result.sort((a, b) => new Date(a.start || 0).getTime() - new Date(b.start || 0).getTime());

  if (result.length === 0) {
    const nowIso = new Date().toISOString();
    result.push({
      id: null,
      meet_id: meetId,
      meet_display_name: `Today (${new Date().toLocaleDateString()})`,
      start: nowIso,
      finish: undefined,
    });
  }

  meetGatheringsCache.set(cacheKey, result);
  return result;
};

/**
 * Vue Composable providing shared lookup state and fetching utilities.
 */
export function useLookups() {
  const gradeConverter = ref<Array<{ id: number; label: string }>>(sharedGradeConverter);
  const organizationDivisions = ref<any[]>(sharedOrganizationDivisions);
  const allFamilyRelations = ref<any[]>(sharedFamilyRelations);
  const allRawRelations = ref<any[]>(sharedRawRelations);

  return {
    gradeConverter,
    organizationDivisions,
    allFamilyRelations,
    allRawRelations,
    loadGradeConverter: () => {
      gradeConverter.value = loadGradeConverter();
      return gradeConverter.value;
    },
    loadOrganizationDivisions: async (endpoint?: string) => {
      organizationDivisions.value = await loadOrganizationDivisions(endpoint);
      return organizationDivisions.value;
    },
    loadFamilyRelations: async (endpoint?: string) => {
      allRawRelations.value = await loadFamilyRelations(endpoint);
      allFamilyRelations.value = sharedFamilyRelations;
      return allRawRelations.value;
    },
    loadMeetGatherings,
    registerGathering,
    getColumnIdentifier,
  };
}
