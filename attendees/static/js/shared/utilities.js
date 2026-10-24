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
    console.log("attendees/static/js/shared/utilities.js");
    Attendees.utilities.userApiAllowedUrlNames = JSON.parse(document.getElementById('user-api-allowed-url-names').textContent);
    Attendees.utilities.userAttendeeId = $('body').data('user-attendee-id');
  },

  deleteAllDevextremeSettings: () => {
    Object.values(Attendees.utilities.datagridStorageKeys).forEach(key => window.sessionStorage.removeItem(key));
    const alert = document.getElementById('alertId');
    if (alert) {
      alert.classList.remove('d-none');
    }
  },

  merge2dObjects: (newObject, oldObject) => {  // 2d (not 3d) merge obj of obj of from old to new, new values wins if exist
    if (newObject && typeof(newObject) === 'object' && oldObject && typeof(oldObject) === 'object') {
      for ([oldKey, oldValue] of Object.entries(oldObject)){
        if (oldValue && typeof(oldValue) === 'object') {
          newObject[oldKey] = {...oldObject[oldKey], ...(newObject[oldKey] || {})};
        } else if (!(oldKey in newObject)) {
          newObject[oldKey] = oldValue;
        }
      }
    }
  },  // more than JQuery extend

  toggleEditingAndReturnStatus: (event) => {
    if (confirm('Are you sure to toggle editing mode?')){
      Attendees.utilities.editingEnabled = event.currentTarget.checked;
    } else {
      event.preventDefault();  // stop checkbox from being changed.
    }
    return Attendees.utilities.editingEnabled;
  },  // if button clicking bug can't be fixed, considering DevExtreme DxSwitch

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
    }  // https://stackoverflow.com/a/58128921/4257237
    return paramValue;
  },

  toggleDxFormGroups: (animationSpeed="fast") => {
    $(".h6:not(.not-shrinkable) .dx-form-group-caption")
      .each(function () {  // somehow jQuery each cannot use arrow function?
        $(this)
          .prepend(
            $('<div />')
              .css({
                "margin-right": "1rem",
              })
              .dxButton({
                icon: 'collapse',
                hint: 'click to hide/show this section',
                onClick: (e) => {
                  const hidden = e.component.option('icon') === 'expand';
                  const $caption = e.element.closest('.dx-form-group-caption');
                  const $content = $caption.siblings(".dx-form-group-content");
                  $content.toggle(animationSpeed);
                  e.component.option(
                    'icon',
                    hidden ? 'collapse' : 'expand'
                  );
                }
              })
          );
      });
  },  // jQuery toggle() from https://supportcenter.devexpress.com/ticket/details/t525231

  addCheckBoxToDxFormGroups: (checkboxClass='checkbox-instance', checked=true, animationSpeed='fast') => {
    $('.h6.not-shrinkable.leading-checkbox .dx-form-group-caption')
      .each(function () {  // somehow jQuery each cannot use arrow function?
        const $title = $(this);
        $title.prepend(
            $('<div />')
              .dxCheckBox({
                value: checked,
                hint: 'Uncheck to disable this section, check to enable this section',
                elementAttr: {
                  class: checkboxClass,
                },
                onValueChanged: (e) => {
                  const $caption = e.element.closest('.dx-form-group-caption');
                  const $content = $caption.siblings(".dx-form-group-content");
                  $content.toggle(animationSpeed);
                }
              })
          );
        if (!checked) {
          $title.siblings(".dx-form-group-content").hide();
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

      if(keepEmpties || trimmedValue || trimmedValue in Attendees.utilities.basicContacts) {  // Will retain a single empty string as the only one empty key
        acc[key.trim()] = trimmedValue;  // acc[key.trim()] = typeof obj[key] == 'string'? obj[key].trim() : trimObj(obj[key]);
      }
      return acc;
    }, {});
  },  // https://stackoverflow.com/a/33511005/4257237

  convertObjectToFormData: object => Object.keys(object).reduce((formData, key) => {
            formData.append(key, object[key]);
            return formData;   // https://stackoverflow.com/a/62936649/4257237
        }, new FormData()),

  setAjaxLoaderOnDevExtreme: () => {
    $(document).ajaxStop(() => {
      $('div.dx-loadpanel').dxLoadPanel('hide');
    });

    $(document).ajaxStart(() => {
      $('div.dx-loadpanel').dxLoadPanel('show');
    });

  },

  timeRules: {
    Weekly: {weekday: 'long', hour: 'numeric', minute: 'numeric'},
  },  // convert Django Schedule rule name to JS toLocaleString option

  callOnce: (func, within=400, timerId=null) => {
    window.callOnceTimers = window.callOnceTimers || {};
    if (timerId == null)
      timerId = func;
    var timer = window.callOnceTimers[timerId];
    clearTimeout(timer);
    timer = setTimeout(() => func(), within);
    window.callOnceTimers[timerId] = timer;
  },  // https://stackoverflow.com/a/70085772/4257237

  debounce : (delay, fn) => {
    let timer = null;
    return (...arguments) => {
      const context = this,
            args = arguments;

      clearTimeout(timer);
      timer = setTimeout(() => {
        fn.apply(context, args);
      }, delay);
    };
  },

  toggleSelect2All: (event, inputSelector) => {
     const $select2Input = $(event.delegateTarget).find(inputSelector);
     const $checkAllBox = $(event.currentTarget);
     const allOptions = $select2Input.children('option').map((i,e) => e.value).get();
     const options = $checkAllBox.is(':checked') ? allOptions : [];
     $select2Input.val(options).trigger('change');
  },

  testArraysEqualAfterSort : (a, b) => {
    a = Array.isArray(a) ? a.sort() : [];
    b = Array.isArray(b) ? b.sort() : [];
    return a.length > 0 && a.length === b.length && a.every((el, ix) => el === b[ix]);
  }, // https://stackoverflow.com/a/39967517/4257237

  alterCheckBoxAndValidations: (currentTarget, inputSelector) => {
    const $currentTarget = $(currentTarget);

    if ($currentTarget.is('select')) {
      const $checkAllBox = $currentTarget.siblings('div.input-group-append').find(inputSelector);
      const allOptions = $currentTarget.children('option').map((i,e) => e.value).get();
      const chosenOptions = $currentTarget.val() || [];

        if (chosenOptions.length) {
          $currentTarget.removeClass('is-invalid');
        } else {
          $currentTarget.addClass('is-invalid');
        }
      $checkAllBox.prop('checked', Attendees.utilities.testArraysEqualAfterSort(chosenOptions, allOptions));
    }
  },

  clearGridStatesInSessionStorage: (storageKey, keysToBeDeleted=['searchText']) => {
    const state = JSON.parse(window.sessionStorage.getItem(storageKey));
    for (const item in state) {
      if (keysToBeDeleted.includes(item)) delete state[item];
    }
    window.sessionStorage.setItem(storageKey, JSON.stringify(state));
  },  // to remove annoyed search text.  Custom stateStoring interfered with column visibility

  removeElementFromArray: (array, key, value) => {
    const index = array.findIndex(obj => obj[key] === value);
    return array.splice(index, 1);
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
  },  // loop in loop/flatMap because of options grouped by assembly/category

  isAllGroupedTagsSelected: (tagBoxEditor) => {
    if(tagBoxEditor){
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
        case rawNumberText.startsWith('+1') && rawNumberText.length === 12:  // US
          return `${rawNumberText.slice(0, 2)}(${rawNumberText.slice(2, 5)})${rawNumberText.slice(5, 8)}-${rawNumberText.slice(8)}`;
        case rawNumberText.startsWith('+86') && [11, 12, 13].includes(rawNumberText.length):  // China
          if (rawNumberText.length < 13) {
            return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 5)})${rawNumberText.slice(5, 9)}-${rawNumberText.slice(9)}`;
          } else {
            return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 6)})${rawNumberText.slice(6, 10)}-${rawNumberText.slice(10)}`;
          }
        case rawNumberText.startsWith('+886') && [12, 13].includes(rawNumberText.length):  // Taiwan
          if (rawNumberText.length > 12 && rawNumberText[4] === '9') {
            return `${rawNumberText.slice(0, 4)}(${rawNumberText.slice(4, 7)})${rawNumberText.slice(7, 10)}-${rawNumberText.slice(10)}`;
          } else if (rawNumberText.length > 12) {
            return `${rawNumberText.slice(0, 4)}(${rawNumberText.slice(4, 5)})${rawNumberText.slice(5, 9)}-${rawNumberText.slice(9)}`;
          } else {
            return `${rawNumberText.slice(0, 4)}(${rawNumberText.slice(4, 5)})${rawNumberText.slice(5, 8)}-${rawNumberText.slice(8)}`;
          }
        case rawNumberText.startsWith('+852') && rawNumberText.length === 12:  // HK
          return `${rawNumberText.slice(0, 1)}(${rawNumberText.slice(1, 4)})${rawNumberText.slice(4, 8)}-${rawNumberText.slice(8)}`;
        case rawNumberText.startsWith('+65') && rawNumberText.length === 11:   // Singapore skips area code
          return `${rawNumberText.slice(0, 3)}()${rawNumberText.slice(3, 7)}-${rawNumberText.slice(7)}`;
        case rawNumberText.startsWith('+60') && [11, 12, 13].includes(rawNumberText.length):  // Malaysia
          if (rawNumberText.length > 12) {return `${rawNumberText.slice(0, 3)}(${rawNumberText.slice(3, 5)})${rawNumberText.slice(5, 9)}-${rawNumberText.slice(9)}`;}
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
          return rawNumberText;  // currently doesn't support UK numbers
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
    return args
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
};

$(document).ready(() => {
  Attendees.utilities.init();
});
