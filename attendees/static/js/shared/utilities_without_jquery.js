window.Attendees = window.Attendees || {};

Attendees.utilities = {
  editingEnabled: false,
  userApiAllowedUrlNames: {},
  userAttendeeId: '',
  datagridStorageKeys: {
    datagridAttendingmeetsListView: "attendeesAttendingmeetsList",
    datagridAttendingmeetsListViewOpts: "attendeesAttendingmeetsListOpts",
    attendancesListView: "attendancesListView",
    attendancesListViewOpts: "attendancesListViewOpts",
    attendanceStatisticsListView: "attendanceStatisticsListView",
    attendanceStatisticsListViewOpts: "attendanceStatisticsListViewOpts",
    personalAttendancesListView: "personalAttendancesListView",
    personalAttendancesListViewOpts: "personalAttendancesListViewOpts",
    gatheringsListView: "attendeesGatheringsList",
    gatheringsListViewOpts: "attendeesGatheringsListOpts",
    attendeesAttendeesList: "attendeesAttendeesList",
    attendeeListViewOpts: "attendeesListOpts",
    rollCallListView: "rollCallList",
    rollCallListViewOpts: "rollCallListOpts",
    rostersListView: "rostersListView",
    rostersListViewOpts: "rostersListViewOpts",
  },

  init: () => {
    console.log("attendees/static/js/shared/utilities_without_jquery.js");
    const allowedEl = document.getElementById('user-api-allowed-url-names');
    Attendees.utilities.userApiAllowedUrlNames = allowedEl ? JSON.parse(allowedEl.textContent) : {};
    Attendees.utilities.userAttendeeId = (document.body && document.body.dataset && document.body.dataset.userAttendeeId) || '';
  },

  deleteAllDevextremeSettings: () => {
    Object.values(Attendees.utilities.datagridStorageKeys).forEach(key => window.sessionStorage.removeItem(key));
    const alert = document.getElementById('alertId');
    if (alert) {
      alert.classList.remove('d-none');
    }
  },

  merge2dObjects: (newObject, oldObject) => {
    if (newObject && typeof(newObject) === 'object' && oldObject && typeof(oldObject) === 'object') {
      for (const [oldKey, oldValue] of Object.entries(oldObject)){
        if (oldValue && typeof(oldValue) === 'object') {
          newObject[oldKey] = {...oldObject[oldKey], ...(newObject[oldKey] || {})};
        } else if (!(oldKey in newObject)) {
          newObject[oldKey] = oldValue;
        }
      }
    }
  },

  toggleEditingAndReturnStatus: (event) => {
    if (confirm('Are you sure to toggle editing mode?')){
      Attendees.utilities.editingEnabled = event.currentTarget.checked;
    } else {
      event.preventDefault();
    }
    return Attendees.utilities.editingEnabled;
  },

  isNotEmpty: (value) => {
    if (Array.isArray(value)){
      return value.length > 0;
    } else if (typeof(value) === 'object' ) {
      return value !== null && Object.keys(value).length > 0;
    }
    return ![undefined, null, "", NaN].includes(value);
  },

  extractParamAndReplaceHistory: (paramName) => {
    const searchParams = new URLSearchParams(window.location.search);
    const paramValue = searchParams.get(paramName);
    if (searchParams.has(paramName)) {
      searchParams.delete(paramName);
      if (history.replaceState) {
        const paramsString = searchParams.toString();
        const searchString = paramsString.length > 0 ? '?' + paramsString : '';
        const newUrl = window.location.protocol + '//' + window.location.host + window.location.pathname + searchString + window.location.hash;
        history.replaceState(null, window.document.title, newUrl);
      }
    }
    return paramValue;
  },

  toggleDxFormGroups: (animationSpeed="fast") => {
    document.querySelectorAll(".h6:not(.not-shrinkable) .dx-form-group-caption").forEach(captionEl => {
      const btnDiv = document.createElement('div');
      btnDiv.style.marginRight = "1rem";
      captionEl.prepend(btnDiv);
      new DevExpress.ui.dxButton(btnDiv, {
        icon: 'collapse',
        hint: 'click to hide/show this section',
        onClick: (e) => {
          const hidden = e.component.option('icon') === 'expand';
          const parentGroup = captionEl.closest('.dx-form-group');
          const content = parentGroup ? parentGroup.querySelector(".dx-form-group-content") : null;
          if (content) {
            content.style.display = hidden ? '' : 'none';
          }
          e.component.option('icon', hidden ? 'collapse' : 'expand');
        }
      });
    });
  },

  addCheckBoxToDxFormGroups: (checkboxClass='checkbox-instance', checked=true, animationSpeed='fast') => {
    document.querySelectorAll('.h6.not-shrinkable.leading-checkbox .dx-form-group-caption').forEach(captionEl => {
      const chkDiv = document.createElement('div');
      chkDiv.className = checkboxClass;
      captionEl.prepend(chkDiv);
      new DevExpress.ui.dxCheckBox(chkDiv, {
        value: checked,
        hint: 'Uncheck to disable this section, check to enable this section',
        onValueChanged: (e) => {
          const parentGroup = captionEl.closest('.dx-form-group');
          const content = parentGroup ? parentGroup.querySelector(".dx-form-group-content") : null;
          if (content) {
            content.style.display = e.value ? '' : 'none';
          }
        }
      });
      if (!checked) {
        const parentGroup = captionEl.closest('.dx-form-group');
        const content = parentGroup ? parentGroup.querySelector(".dx-form-group-content") : null;
        if (content) content.style.display = 'none';
      }
    });
  },

  areTwoArraysTheSame: (array1, array2) => {
    if (Array.isArray(array1) && Array.isArray(array2)) {
      return JSON.stringify(array1.sort()) === JSON.stringify(array2.sort());
    }
    return undefined;
  },

  trimBothKeyAndValueButKeepBasicContacts: (obj, keepEmpties=false) => {
    return Object.entries(obj).reduce((acc, curr) => {
      const [key, value] = curr;
      const trimmedValue = value ? value.trim() : null;

      if(keepEmpties || trimmedValue || trimmedValue in Attendees.utilities.basicContacts) {
        acc[key.trim()] = trimmedValue;
      }
      return acc;
    }, {});
  },

  convertObjectToFormData: object => Object.keys(object).reduce((formData, key) => {
    formData.append(key, object[key]);
    return formData;
  }, new FormData()),

  setAjaxLoaderOnDevExtreme: () => {},

  timeRules: {
    Weekly: {weekday: 'long', hour: 'numeric', minute: 'numeric'},
  },

  callOnce: (func, within=400, timerId=null) => {
    window.callOnceTimers = window.callOnceTimers || {};
    if (timerId == null) timerId = func;
    let timer = window.callOnceTimers[timerId];
    clearTimeout(timer);
    timer = setTimeout(() => func(), within);
    window.callOnceTimers[timerId] = timer;
  },

  debounce: (delay, fn) => {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        fn(...args);
      }, delay);
    };
  },

  testArraysEqualAfterSort: (a, b) => {
    a = Array.isArray(a) ? a.sort() : [];
    b = Array.isArray(b) ? b.sort() : [];
    return a.length > 0 && a.length === b.length && a.every((el, ix) => el === b[ix]);
  },

  clearGridStatesInSessionStorage: (storageKey, keysToBeDeleted=['searchText']) => {
    const state = JSON.parse(window.sessionStorage.getItem(storageKey) || '{}');
    for (const item in state) {
      if (keysToBeDeleted.includes(item)) delete state[item];
    }
    window.sessionStorage.setItem(storageKey, JSON.stringify(state));
  },

  removeElementFromArray: (array, key, value) => {
    const index = array.findIndex(obj => obj[key] === value);
    if (index >= 0) return array.splice(index, 1);
    return [];
  },

  getValuesByMatchingKeys: (obj, regex) => {
    if (typeof obj === 'object' && obj !== null) {
      return Object.keys(obj)
        .filter(key => regex.test(key))
        .map(key => obj[key])
        .filter(value => value !== null && value !== undefined && value !== '');
    } else {
      return [];
    }
  },

  genderEnums: () => {
    return [
      {name: 'MALE'},
      {name: 'FEMALE'},
      {name: 'UNSPECIFIED'},
    ];
  },

  basicContacts: {
    phone1: null,
    phone2: null,
    email1: null,
    email2: null,
  },

  selectAllGroupedTags: (tagBoxEditor, tagSlugs) => {
    const availableTagSlugs = tagSlugs === undefined ? tagBoxEditor.option('items').flatMap(category => 'items' in category ? category.items.map(item => item.slug) : category.slug) : tagSlugs;
    tagBoxEditor.option('value', availableTagSlugs);
  },

  isAllGroupedTagsSelected: (tagBoxEditor) => {
    if (tagBoxEditor) {
      const availableTagSlugs = tagBoxEditor.option('items').flatMap(category => category.items.map(item => item.slug));
      return Attendees.utilities.testArraysEqualAfterSort(tagBoxEditor.option('value'), availableTagSlugs);
    } else {
      return null;
    }
  },

  accessItemFromSessionStorage: (storageMasterKey, itemKey, itemValue) => {
    if (storageMasterKey) {
      const storedObject = JSON.parse(window.sessionStorage.getItem(storageMasterKey) || '{}');
      if (itemValue !== undefined) {
        if (itemKey) {
          storedObject[itemKey] = itemValue;
          window.sessionStorage.setItem(storageMasterKey, JSON.stringify(storedObject));
        }
      }
      return storedObject[itemKey];
    }
    return null;
  },

  phoneNumberFormatter: (rawNumberText) => {
    if (rawNumberText) {
      switch (true) {
        case rawNumberText.startsWith('+1') && rawNumberText.length === 12:
          return `${rawNumberText.slice(0, 2)}(${rawNumberText.slice(2, 5)})${rawNumberText.slice(5, 8)}-${rawNumberText.slice(8)}`;
        case rawNumberText.startsWith('+86') && [11, 12, 13].includes(rawNumberText.length):
          if (rawNumberText.length < 13) {
            return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 5)})${rawNumberText.slice(5, 9)}-${rawNumberText.slice(9)}`;
          } else {
            return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 6)})${rawNumberText.slice(6, 10)}-${rawNumberText.slice(10)}`;
          }
        case rawNumberText.startsWith('+886') && [12, 13].includes(rawNumberText.length):
          if (rawNumberText.length > 12 && rawNumberText[4] === '9') {
            return `${rawNumberText.slice(0, 4)}(${rawNumberText.slice(4, 7)})${rawNumberText.slice(7, 10)}-${rawNumberText.slice(10)}`;
          } else if (rawNumberText.length > 12) {
            return `${rawNumberText.slice(0, 4)}(${rawNumberText.slice(4, 5)})${rawNumberText.slice(5, 9)}-${rawNumberText.slice(9)}`;
          } else {
            return `${rawNumberText.slice(0, 4)}(${rawNumberText.slice(4, 5)})${rawNumberText.slice(5, 8)}-${rawNumberText.slice(8)}`;
          }
        case rawNumberText.startsWith('+852') && rawNumberText.length === 12:
          return `${rawNumberText.slice(0, 1)}(${rawNumberText.slice(1, 4)})${rawNumberText.slice(4, 8)}-${rawNumberText.slice(8)}`;
        case rawNumberText.startsWith('+65') && rawNumberText.length === 11:
          return `${rawNumberText.slice(0, 3)}()${rawNumberText.slice(3, 7)}-${rawNumberText.slice(7)}`;
        case rawNumberText.startsWith('+60') && [11, 12, 13].includes(rawNumberText.length):
          if (rawNumberText.length > 12) return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 5)})${rawNumberText.slice(5, 9)}-${rawNumberText.slice(9)}`;
          if (rawNumberText.length < 12) {
            if (rawNumberText.startsWith('+608')) {
              return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 5)})${rawNumberText.slice(5, 8)}-${rawNumberText.slice(8)}`;
            } else {
              return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 4)})${rawNumberText.slice(4, 7)}-${rawNumberText.slice(7)}`;
            }
          }
          if (rawNumberText.startsWith('+601')) {
            return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 5)})${rawNumberText.slice(5, 8)}-${rawNumberText.slice(8)}`;
          } else {
            return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 4)})${rawNumberText.slice(4, 8)}-${rawNumberText.slice(8)}`;
          }
        default:
          return rawNumberText;
      }
    }
    return '';
  },

  filterDevExtremeArgs: (loadOptions={}, args={}, filters=[
    'skip',
    'take',
    'requireTotalCount',
    'requireGroupCount',
    'sort',
    'filter',
    'totalSummary',
    'group',
  ]) => {
    filters.forEach((i) => {
      if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
        args[i] = JSON.stringify(loadOptions[i]);
    });
    return args;
  },

  normalizePhoneNumber: (val) => {
    if (!val || typeof val !== 'string') return val;
    const trimmed = val.trim();
    if (!trimmed) return trimmed;
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
  },

  getDaysInMonth: (year, month) => {
    const m = parseInt(month, 10);
    if (isNaN(m) || m < 1 || m > 12) return 31;
    const y = parseInt(year, 10);
    if (!isNaN(y) && y >= 1000 && y <= 9999) {
      return new Date(y, m, 0).getDate();
    }
    if (m === 2) return 29;
    if ([4, 6, 9, 11].includes(m)) return 30;
    return 31;
  },

  adjustBirthdayDayOptions: (yearVal, monthVal, daySelectEl) => {
    if (!daySelectEl) return;
    const maxDays = Attendees.utilities.getDaysInMonth(yearVal, monthVal);
    const currentVal = daySelectEl.value;

    daySelectEl.innerHTML = '<option value="">Day</option>';
    for (let i = 1; i <= maxDays; i++) {
      const opt = document.createElement('option');
      opt.value = String(i);
      opt.textContent = String(i);
      if (currentVal && String(currentVal) === String(i)) {
        opt.selected = true;
      }
      daySelectEl.appendChild(opt);
    }

    if (currentVal && parseInt(currentVal, 10) > maxDays) {
      daySelectEl.value = '';
    }
  },

  validateFastInputBirthday: (year, month, day) => {
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
  },

  validateFastInputPhoneNumber: (val) => {
    if (!val || typeof val !== 'string') return false;
    const digitsOnly = val.replace(/\D/g, '');
    return digitsOnly.length >= 10;
  },

  validateFastInputEmail: (val) => {
    if (!val || typeof val !== 'string') return false;
    const trimmed = val.trim();
    return trimmed.length >= 5 && trimmed.includes('.') && trimmed.includes('@');
  },

  validateFastInputContact: (type, val) => {
    if (!val || typeof val !== 'string' || !val.trim()) return false;
    const normalizedType = (type || 'phone').toLowerCase();
    if (normalizedType === 'phone' || normalizedType === 'whatsapp') {
      return Attendees.utilities.validateFastInputPhoneNumber(val);
    } else if (normalizedType === 'email') {
      return Attendees.utilities.validateFastInputEmail(val);
    }
    return val.trim().length >= 2;
  },

  escapeHtml: (str) => {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, (m) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[m]);
  },
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    Attendees.utilities.init();
  });
} else {
  Attendees.utilities.init();
}
