Attendees.utilities = {
  editingEnabled: false,
  userApiAllowedUrlNames: {},
  userAttendeeId: '',
  datagridStorageKeys: {
    datagridAttendingmeetsListView: "attendeesAttendingmeetsList",
    datagridAttendingmeetsListViewOpts: "attendeesAttendingmeetsListOpts",
    attendancesListView: "attendancesListView",
    attendancesListViewOpts: "attendancesListViewOpts",
    personalAttendancesListView: "personalAttendancesListView",
    personalAttendancesListViewOpts: "personalAttendancesListViewOpts",
    gatheringsListView: "attendeesGatheringsList",
    gatheringsListViewOpts: "attendeesGatheringsListOpts",
    attendeesAttendeesList: "attendeesAttendeesList",
    attendeeListViewOpts: "attendeesListOpts",
    rollCallListView: "rollCallList",
    rollCallListViewOpts: "rollCallListOpts",
  },

  init: () => {
    console.log("attendees/static/js/shared/utilities.js");
    Attendees.utilities.userApiAllowedUrlNames = $('body').data('user-api-allowed-url-names');
    Attendees.utilities.userAttendeeId = $('body').data('user-attendee-id');
  },

  deleteAllDevextremeSettings: () => {
    Object.values(Attendees.utilities.datagridStorageKeys).forEach(key => window.sessionStorage.removeItem(key));
    const alert = document.getElementById('alertId');
    if (alert) {
      alert.classList.remove('d-none');
    }
  },

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
      .each(function () {
        $(this)
          .prepend(
            $('<div />')
              .css({
                "margin-right": "1rem",
              })
              .dxButton({
                "icon": "collapse",
                "onClick": (e) => {
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
    $(document).ajaxStop(function(){
      $('div.dx-loadpanel').dxLoadPanel('hide');
    });

    $(document).ajaxStart(function(){
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
    const availableTagSlugs = tagSlugs === undefined ? tagBoxEditor.option('items').flatMap(category => category.items.map(item => item.slug)) : tagSlugs;
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
};

$(document).ready(() => {
  Attendees.utilities.init();
});
