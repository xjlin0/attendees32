/**
 * Shared utility functions for Attendees frontend applications.
 * Provides string normalization, contact validation, date parsing,
 * DevExtreme argument filtering, and session storage helpers.
 */

// Storage key mappings used for DevExtreme datagrids
export const datagridStorageKeys = {
  datagridAttendingmeetsListView: 'attendeesAttendingmeetsList',
  datagridAttendingmeetsListViewOpts: 'attendeesAttendingmeetsListOpts',
  attendancesListView: 'attendancesListView',
  attendancesListViewOpts: 'attendancesListViewOpts',
  attendanceStatisticsListView: 'attendanceStatisticsListView',
  attendanceStatisticsListViewOpts: 'attendanceStatisticsListViewOpts',
  personalAttendancesListView: 'personalAttendancesListView',
  personalAttendancesListViewOpts: 'personalAttendancesListViewOpts',
  gatheringsListView: 'attendeesGatheringsList',
  gatheringsListViewOpts: 'attendeesGatheringsListOpts',
  attendeesAttendeesList: 'attendeesAttendeesList',
  attendeeListViewOpts: 'attendeesListOpts',
  rollCallListView: 'rollCallList',
  rollCallListViewOpts: 'rollCallListOpts',
  rostersListView: 'rostersListView',
  rostersListViewOpts: 'rostersListViewOpts',
};

// Global editing state
let _editingEnabled = false;

export const getEditingEnabled = (): boolean => _editingEnabled;
export const setEditingEnabled = (val: boolean): void => {
  _editingEnabled = Boolean(val);
  if (typeof window !== 'undefined' && (window as any).Attendees?.utilities) {
    (window as any).Attendees.utilities.editingEnabled = _editingEnabled;
  }
};

/**
 * Escapes unsafe HTML characters in a string.
 * @param str Input string.
 * @returns Safe HTML escaped string.
 */
export const escapeHtml = (str: string): string => {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, (m) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[m] || m);
};

/**
 * Normalizes phone number into E.164 format (+1XXXXXXXXXX for 10-digit US/Canada numbers).
 * @param val Raw phone number string.
 * @returns Normalized phone string.
 */
export const normalizePhoneNumber = (val: string): string => {
  if (!val || typeof val !== 'string') return '';
  const trimmed = val.trim();
  const digitsOnly = trimmed.replace(/\D/g, '');
  if (digitsOnly.length === 10) {
    return `+1${digitsOnly}`;
  }
  if (digitsOnly.length === 11 && digitsOnly.startsWith('1')) {
    return `+${digitsOnly}`;
  }
  if (trimmed.startsWith('+') && digitsOnly.length >= 7) {
    return `+${digitsOnly}`;
  }
  if (digitsOnly.length >= 10) {
    return `+1${digitsOnly.slice(-10)}`;
  }
  return trimmed;
};

/**
 * Validates that phone number contains at least 10 digits.
 * @param val Phone number string.
 * @returns Boolean valid flag.
 */
export const validateFastInputPhoneNumber = (val: string): boolean => {
  if (!val || typeof val !== 'string') return false;
  const digitsOnly = val.replace(/\D/g, '');
  return digitsOnly.length >= 10;
};

/**
 * Validates that email string is at least 5 chars and contains '@' and '.'.
 * @param val Email string.
 * @returns Boolean valid flag.
 */
export const validateFastInputEmail = (val: string): boolean => {
  if (!val || typeof val !== 'string') return false;
  const trimmed = val.trim();
  return trimmed.length >= 5 && trimmed.includes('.') && trimmed.includes('@');
};

/**
 * Validates contact input according to contact type.
 * @param type Contact type (e.g. 'phone', 'email', 'wechat').
 * @param val Contact value.
 * @returns Boolean valid flag.
 */
export const validateFastInputContact = (type: string, val: string): boolean => {
  if (!val || typeof val !== 'string' || !val.trim()) return false;
  const normalizedType = (type || 'phone').toLowerCase();
  if (normalizedType === 'phone' || normalizedType === 'whatsapp') {
    return validateFastInputPhoneNumber(val);
  } else if (normalizedType === 'email') {
    return validateFastInputEmail(val);
  }
  return val.trim().length >= 2;
};

/**
 * Calculates maximum days in a given year and month.
 * @param year Year number or string.
 * @param month Month number (1-12) or string.
 * @returns Maximum valid days.
 */
export const getDaysInMonth = (year: any, month: any): number => {
  const m = parseInt(month, 10);
  if (isNaN(m) || m < 1 || m > 12) return 31;
  const y = parseInt(year, 10);
  if (!isNaN(y) && y >= 1000 && y <= 9999) {
    return new Date(y, m, 0).getDate();
  }
  if (m === 2) return 29;
  if ([4, 6, 9, 11].includes(m)) return 30;
  return 31;
};

/**
 * Validates birthday components.
 * @param year Birth year.
 * @param month Birth month.
 * @param day Birth day.
 * @returns Validation result with valid boolean and optional message string.
 */
export const validateFastInputBirthday = (
  year: any,
  month: any,
  day: any
): { valid: boolean; message?: string } => {
  const today = new Date();
  const currentYear = today.getFullYear();
  const hasYear = year !== undefined && year !== null && String(year).trim() !== '';
  const hasMonth = month !== undefined && month !== null && String(month).trim() !== '';
  const hasDay = day !== undefined && day !== null && String(day).trim() !== '';

  if (!hasYear && !hasMonth && !hasDay) {
    return { valid: true };
  }

  if (hasDay && !hasMonth) {
    return { valid: false, message: 'Birth month is required when birth day is specified.' };
  }

  let y = 2000;
  if (hasYear) {
    y = parseInt(year, 10);
    if (isNaN(y)) {
      return { valid: false, message: 'Invalid birth year.' };
    }
    if (y > currentYear) {
      return { valid: false, message: `Birth year cannot exceed ${currentYear}.` };
    }
    if (y < 1900) {
      return { valid: false, message: 'Birth year must be 1900 or later.' };
    }
  }

  const m = hasMonth ? parseInt(month, 10) : null;
  const d = hasDay ? parseInt(day, 10) : null;

  if (m !== null) {
    if (isNaN(m) || m < 1 || m > 12) {
      return { valid: false, message: 'Invalid birth month.' };
    }
  }

  if (m !== null && d !== null) {
    if (isNaN(d) || d < 1 || d > 31) {
      return { valid: false, message: 'Invalid birth day.' };
    }
    const bDate = new Date(y, m - 1, d);
    if (bDate.getFullYear() !== y || bDate.getMonth() !== m - 1 || bDate.getDate() !== d) {
      return { valid: false, message: 'Invalid calendar date.' };
    }
    if (hasYear) {
      const endOfToday = new Date();
      endOfToday.setHours(23, 59, 59, 999);
      if (bDate > endOfToday) {
        return { valid: false, message: 'Birthday cannot be in the future.' };
      }
    }
  }

  return { valid: true };
};

/**
 * Accesses or writes an item in sessionStorage under a JSON object key.
 * @param storageKey Key of the stored JSON object in sessionStorage.
 * @param itemKey Key of the property within the object.
 * @param value If provided, updates the property with this value.
 * @returns Current or updated value.
 */
export const accessItemFromSessionStorage = (
  storageKey: string,
  itemKey: string,
  value?: any
): any => {
  if (!storageKey || typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(storageKey);
    const state = raw ? JSON.parse(raw) : {};
    if (value !== undefined) {
      state[itemKey] = value;
      window.sessionStorage.setItem(storageKey, JSON.stringify(state));
      return value;
    }
    return state[itemKey];
  } catch (e) {
    console.warn('SessionStorage access failed:', e);
    return null;
  }
};

/**
 * Clears specified state keys from a stored JSON object in sessionStorage.
 * @param storageKey Key of the stored JSON object in sessionStorage.
 * @param keysToBeDeleted Array of keys to remove.
 */
export const clearGridStatesInSessionStorage = (
  storageKey: string,
  keysToBeDeleted = ['searchText']
): void => {
  if (!storageKey || typeof window === 'undefined') return;
  try {
    const raw = window.sessionStorage.getItem(storageKey);
    const state = raw ? JSON.parse(raw) : {};
    for (const key of keysToBeDeleted) {
      delete state[key];
    }
    window.sessionStorage.setItem(storageKey, JSON.stringify(state));
  } catch (e) {
    console.warn('SessionStorage clear failed:', e);
  }
};

/**
 * Checks if a value is not empty (null, undefined, empty string, or empty array/object).
 * @param value Target value.
 * @returns Boolean flag.
 */
export const isNotEmpty = (value: any): boolean => {
  if (Array.isArray(value)) {
    return value.length > 0;
  } else if (typeof value === 'object') {
    return value !== null && Object.keys(value).length > 0;
  }
  return ![undefined, null, '', NaN].includes(value);
};

/**
 * Tests if two arrays are equal after sorting.
 * @param a First array.
 * @param b Second array.
 * @returns Boolean flag.
 */
export const testArraysEqualAfterSort = (a: any[], b: any[]): boolean => {
  const arrA = Array.isArray(a) ? [...a].sort() : [];
  const arrB = Array.isArray(b) ? [...b].sort() : [];
  return (
    arrA.length > 0 &&
    arrA.length === arrB.length &&
    arrA.every((el, ix) => el === arrB[ix])
  );
};

/**
 * Creates a debounced function wrapper.
 * @param delay Milliseconds to delay.
 * @param fn Callback function.
 * @returns Debounced wrapper.
 */
export const debounce = (delay: number, fn: (...args: any[]) => void): ((...args: any[]) => void) => {
  let timer: any = null;
  return (...args: any[]) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn(...args);
    }, delay);
  };
};

/**
 * Filters and sanitizes DevExtreme DataGrid load arguments for REST API queries.
 * @param loadOptions DevExtreme DataSource load options.
 * @param customArgs Optional custom query parameter dictionary.
 * @returns Sanitized query params dictionary.
 */
export const filterDevExtremeArgs = (loadOptions: any, customArgs: Record<string, any> = {}): Record<string, any> => {
  const result: Record<string, any> = { ...customArgs };
  if (!loadOptions) return result;

  const validKeys = [
    'skip',
    'take',
    'requireTotalCount',
    'requireGroupCount',
    'sort',
    'filter',
    'totalSummary',
    'group',
    'groupSummary',
  ];

  for (const key of validKeys) {
    if (key in loadOptions && isNotEmpty(loadOptions[key])) {
      result[key] = JSON.stringify(loadOptions[key]);
    }
  }

  return result;
};

// Global Attendees.utilities compatibility object for backward compatibility
if (typeof window !== 'undefined') {
  (window as any).Attendees = (window as any).Attendees || {};
  (window as any).Attendees.utilities = {
    get editingEnabled() {
      return _editingEnabled;
    },
    set editingEnabled(val: boolean) {
      _editingEnabled = Boolean(val);
    },
    datagridStorageKeys,
    escapeHtml,
    normalizePhoneNumber,
    validateFastInputPhoneNumber,
    validateFastInputEmail,
    validateFastInputContact,
    validateFastInputBirthday,
    getDaysInMonth,
    accessItemFromSessionStorage,
    clearGridStatesInSessionStorage,
    isNotEmpty,
    testArraysEqualAfterSort,
    debounce,
    filterDevExtremeArgs,
    deleteAllDevextremeSettings: () => {
      Object.values(datagridStorageKeys).forEach((key) => window.sessionStorage.removeItem(key));
      const alertEl = document.getElementById('alertId');
      if (alertEl) {
        alertEl.classList.remove('d-none');
      }
    },
    init: () => {
      const allowedEl = document.getElementById('user-api-allowed-url-names');
      if ((window as any).Attendees?.utilities) {
        (window as any).Attendees.utilities.userApiAllowedUrlNames = allowedEl
          ? JSON.parse(allowedEl.textContent || '{}')
          : {};
        (window as any).Attendees.utilities.userAttendeeId =
          (document.body && document.body.dataset && document.body.dataset.userAttendeeId) || '';
      }
    },
  };
}
