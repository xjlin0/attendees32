Attendees.datagridUpdate = {
  attendeeMainDxForm: null,  // will be assigned later, may not needed if use native form.submit()?
  attendeeMainDxFormDefault: {
    infos: {
      names: {},
      fixed: {mobility: 2},
      progressions: {},
      contacts: {},
      emergency_contacts: {},
      schedulers: {},
      updating_attendees: {}
    }
  },
  attendeeAttrs: null,  // will be assigned later
  attendeeId: '',  // the attendee is being edited, since it maybe admin/parent editing another attendee
  attendeeAjaxUrl: null,
  attendeePhotoFileUploader: null,
  relationshipDatagrid: null,
  attendingMeetDatagrid: null,
  attendingPopupDxForm: null,  // for getting formData
  attendingPopupDxFormData: {},  // for storing formData
  // attendingPopupDxFormCharacterSelect: null,
  attendingPopup: null,  // for show/hide popup
  attendingsData: {},
  attendingDefaults: {
    category: 'primary',
  },
  attendingmeetDefaults: {
    // assembly: parseInt(document.querySelector('div.datagrid-attendee-update').dataset.currentAssemblyId),
    category: 'primary',
    start: new Date().toISOString(),
    finish: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString(), // 1 years from now
  },
  // addressId: '', // for sending address data by AJAX
  divisionShowAttendeeInfos: {},
  placePopup: null, // for show/hide popup
  placePopupDxForm: null,  // for getting formData
  placePopupDxFormData: {},  // for storing formData
  placeDefaults: {
    address: {
      type: 'street',
    },
    display_order: 0,
    display_name: 'main',
    // content_type: parseInt(document.querySelector('div.datagrid-attendee-update').dataset.attendeeContenttypeId),
  },
  duplicatesForNewAttendeeDatagrid: null,
  families: [],
  familyAttendeeDatagrid: null,
  familyAttrPopupDxForm: null,
  familyAttrPopupDxFormData: {},
  familyAttrPopup: null,
  familyAttrDefaults: {
    display_order: 0,
    attendees: [document.querySelector('input[name="attendee-id"]').value],
    division: 0,       // will be assigned later
    display_name: '',  // will be assigned later
  },
  meetCharacters: null,
  divisionIdNames: null,

  init: () => {
    console.log('/static/js/persons/attendee_update_view.js');
    Attendees.datagridUpdate.displayNotifierFromSearchParam('success');
    Attendees.datagridUpdate.initAttendeeForm();
  },

  initListeners: () => {
    $("div.nav-buttons").on('click', 'input#custom-control-edit-checkbox', e => Attendees.datagridUpdate.toggleEditing(Attendees.utilities.toggleEditingAndReturnStatus(e)));
    $("div.form-container").on('click', 'button.attending-button', e => Attendees.datagridUpdate.initAttendingPopupDxForm(e));
    $("div.form-container").on('click', 'button.place-button', e => Attendees.datagridUpdate.initPlacePopupDxForm(e));
    $("div.form-container").on('click', 'button.family-button', e => Attendees.datagridUpdate.initFamilyAttrPopupDxForm(e));
    Attendees.datagridUpdate.attachContactAddButton();

    $(window).keydown((event) => {
      if (event.keyCode === 13) {
        DevExpress.ui.notify(
          {
            message: 'Click the "Save Attendee" button to save data',
            position: {
              my: 'center',
              at: 'center',
              of: window,
            },
          }, 'warning', 1000);
        event.preventDefault();
        return false;
      } // prevent user to submit form by hitting enter
    });
    // add listeners for Family, counselling, etc.
  },

  toggleEditing: (enabled) => {
    const newAttendeeDxDropDownButton = Attendees.datagridUpdate.attendeeMainDxForm.getEditor('add_new_attendee');
    $('div.attendee-form-submits').dxButton('instance').option('disabled', !enabled);
    $('div.attendee-form-dead').dxButton('instance').option('disabled', !enabled);
    $('div.attendee-form-delete').dxButton('instance').option('disabled', !enabled);
    $('span.attendee-form-submits').dxButton('instance').option('disabled', !enabled);
    $('button.attending-button-new, button.family-button-new, button.place-button-new, input.form-check-input').prop('disabled', !enabled);
    Attendees.datagridUpdate.attendeeMainDxForm.option('readOnly', !enabled);
    Attendees.datagridUpdate.phone1.option('readOnly', !enabled);
    Attendees.datagridUpdate.phone2.option('readOnly', !enabled);
    Attendees.datagridUpdate.attendeePhotoFileUploader.option('disabled', !enabled);

    if (enabled) {
      Attendees.datagridUpdate.familyAttendeeDatagrid.clearGrouping();
      Attendees.datagridUpdate.relationshipDatagrid && Attendees.datagridUpdate.relationshipDatagrid.clearGrouping();
      if (Attendees.datagridUpdate.families.length > 0) {
        newAttendeeDxDropDownButton.option('disabled', false);
      }
    } else {
      newAttendeeDxDropDownButton.option('disabled', true);
      Attendees.datagridUpdate.familyAttendeeDatagrid.columnOption('folk.id', 'groupIndex', 0);
      Attendees.datagridUpdate.relationshipDatagrid && Attendees.datagridUpdate.relationshipDatagrid.columnOption('folk.id', 'groupIndex', 0);
    }

    const cellEditingArgs = {
      mode: 'cell',
      allowUpdating: enabled,
      allowAdding: enabled,
      allowDeleting: enabled,
      texts: {
        confirmDeleteMessage: 'Are you sure to delete it? Instead, setting the "finish" date is usually enough!',
      },
    };
    Attendees.datagridUpdate.familyAttendeeDatagrid.option('editing', cellEditingArgs);
    Attendees.datagridUpdate.relationshipDatagrid && Attendees.datagridUpdate.relationshipDatagrid.option('editing', cellEditingArgs);
    Attendees.datagridUpdate.educationDatagrid && Attendees.datagridUpdate.educationDatagrid.option('editing', cellEditingArgs);
    Attendees.datagridUpdate.statusDatagrid && Attendees.datagridUpdate.statusDatagrid.option('editing', cellEditingArgs);
    Attendees.datagridUpdate.noteDatagrid && Attendees.datagridUpdate.noteDatagrid.option('editing', {...cellEditingArgs, ...Attendees.datagridUpdate.noteEditingArgs});
    Attendees.datagridUpdate.attendingMeetDatagrid && Attendees.datagridUpdate.attendingMeetDatagrid.option('editing', {...cellEditingArgs, ...Attendees.datagridUpdate.attendingMeetEditingArgs});
  },

  displayNotifierFromSearchParam: (successParamName) => {
    const successParamValue = Attendees.utilities.extractParamAndReplaceHistory(successParamName);
    if (successParamValue) {
      DevExpress.ui.notify(
        {
          message: successParamValue,
          position: {
            my: 'center',
            at: 'center',
            of: window,
          },
        }, 'success', 2500);
    }
  },


  ///////////////////////  Main Attendee DxForm and Submit ///////////////////////


  initAttendeeForm: () => {
    Attendees.datagridUpdate.attendeeAttrs = document.querySelector('div.datagrid-attendee-update');
    Attendees.datagridUpdate.processDivisions();
    Attendees.datagridUpdate.divisionIdNames = Attendees.datagridUpdate.divisions.reduce((obj, item) => ({...obj, [item.id]: item.display_name}) ,{});
    Attendees.datagridUpdate.attendeeUrn = Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeUrn;
    Attendees.datagridUpdate.attendeeId = document.querySelector('input[name="attendee-id"]').value;
    // Attendees.datagridUpdate.placeDefaults.object_id = Attendees.datagridUpdate.attendeeId;
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
        'X-Target-Attendee-Id': Attendees.datagridUpdate.attendeeId,
      }
    });

    if (Attendees.datagridUpdate.attendeeId === 'new') {
      const urlParams = new URLSearchParams(window.location.search);
      Attendees.datagridUpdate.familyAttrDefaults.id = urlParams.get('familyId');
      Attendees.datagridUpdate.familyAttrDefaults.name = urlParams.get('familyName');
      Attendees.datagridUpdate.familyAttrDefaults.joinMeet = urlParams.get('joinMeet');
      Attendees.datagridUpdate.familyAttrDefaults.joinGathering = urlParams.get('joinGathering');
      const titleWithFamilyName = Attendees.datagridUpdate.familyAttrDefaults.name ? Attendees.datagridUpdate.familyAttrDefaults.name + ' family': '';

      Attendees.datagridUpdate.attendeeAjaxUrl = Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeEndpoint;
      $('h3.page-title').text(`New person ${titleWithFamilyName}: more data can be entered after save`);
      window.top.document.title = `New person ${titleWithFamilyName}`;
      Attendees.utilities.editingEnabled = true;
      Attendees.datagridUpdate.attendeeFormConfigs = Attendees.datagridUpdate.getAttendeeFormConfigs();
      Attendees.datagridUpdate.attendeeMainDxForm = $("div.datagrid-attendee-update").dxForm(Attendees.datagridUpdate.attendeeFormConfigs).dxForm('instance');
      Attendees.datagridUpdate.attendeeFormConfigs.formData = Attendees.datagridUpdate.attendeeMainDxFormDefault;
      Attendees.datagridUpdate.populateBasicInfoBlock({});
    } else {
      Attendees.datagridUpdate.attendeeAjaxUrl = Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeEndpoint + Attendees.datagridUpdate.attendeeId + '/';
      $.ajax({
        url: Attendees.datagridUpdate.attendeeAjaxUrl,
        success: (response) => {
          Attendees.datagridUpdate.attendeeFormConfigs = Attendees.datagridUpdate.getAttendeeFormConfigs();
          Attendees.datagridUpdate.attendeeFormConfigs.formData = response ? response : Attendees.datagridUpdate.attendeeMainDxFormDefault;
          $('h3.page-title').text('Details of ' + Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original);
          window.top.document.title = Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original;
          Attendees.datagridUpdate.attendeeMainDxForm = $("div.datagrid-attendee-update").dxForm(Attendees.datagridUpdate.attendeeFormConfigs).dxForm('instance');
          Attendees.datagridUpdate.populateBasicInfoBlock();
          Attendees.datagridUpdate.initListeners();
          Attendees.datagridUpdate.familyAttrDefaults.division = response.division;
          Attendees.datagridUpdate.familyAttrDefaults.display_name = response.infos.names.original + ' family';
          Attendees.datagridUpdate.patchNewAttendeeDropDown(null);
        },
        error: (response) => {
          console.log('Failed to fetch data in Attendees.datagridUpdate.initAttendeeForm(), error: ', response);
        },
      });
    }
  },

  processDivisions: () => {
    Attendees.datagridUpdate.divisions = JSON.parse(Attendees.datagridUpdate.attendeeAttrs.dataset.divisions);
    Attendees.datagridUpdate.divisionShowAttendeeInfos = Object.entries(Attendees.datagridUpdate.divisions).reduce((acc, curr) => {
      const [key, value] = curr;
      acc[value.id] = value.infos.show_attendee_infos || {};
      return acc;
    }, {});
  },

  patchNewAttendeeDropDown: (newFamily) => {
    const newAttendeeDxDropDownButton = Attendees.datagridUpdate.attendeeMainDxForm.getEditor('add_new_attendee');
    const $newAttendeeLinkWithoutFamily = $('a.add-new-attendee');
    if (newFamily) {
      Attendees.datagridUpdate.families.push(newFamily);
    } else {
      Attendees.datagridUpdate.families = Attendees.datagridUpdate.attendeeFormConfigs.formData.folkattendee_set.map(familyattendee => familyattendee.folk);
    }
    if (Attendees.datagridUpdate.families.length > 0) {
      newAttendeeDxDropDownButton.option('dataSource', Attendees.datagridUpdate.families);
      newAttendeeDxDropDownButton.option('hint', 'Select a family to add a new member');
      Attendees.datagridUpdate.families.forEach(family => {
        const $newAttendeeLinkWithFamily = $newAttendeeLinkWithoutFamily.clone();
        $newAttendeeLinkWithFamily.attr('href', `new?familyId=${family.id}&familyName=for%20${family.display_name}`);
        $newAttendeeLinkWithFamily.attr('title', `Add a new member to ${family.display_name} ${family.category === 0 ? 'family' : ''}`);
        $newAttendeeLinkWithFamily.text(`+New member to ${family.display_name}  ${family.category === 0 ? 'family' : ''}`);
        $newAttendeeLinkWithFamily.attr('target', '_blank');
        $newAttendeeLinkWithFamily.insertBefore($newAttendeeLinkWithoutFamily);
      });
    }
  },

  attachContactAddButton: () => {
    $('<span>', {class: 'extra-contacts float-end'})
      .dxButton({
        disabled: !Attendees.utilities.editingEnabled,
        elementAttr: {
          class: 'attendee-form-submits',  // for toggling editing mode
        },
        text: 'Add more contacts',
        icon: 'email',  // or 'fas fa-comment-dots'
        stylingMode: 'outlined',
        type: 'success',
        height: '1.4rem',
        hint: 'add more different contacts such as more phones/emails',
        onClick: () => {
          Attendees.datagridUpdate.contactPopup = $('div.popup-more-contacts').dxPopup(Attendees.datagridUpdate.contactPopupDxFormConfig).dxPopup('instance');
        },
      }).appendTo($('span.dx-form-group-caption')[1]);  // basic info block is at index 1
  },

  getAttendeeFormConfigs: () => {  // this is the place to control blocks of AttendeeForm
    const isCreatingNewAttendee = Attendees.datagridUpdate.attendeeId === 'new';
    const basicItems = [
      {
        colSpan: 4,
        itemType: 'group',
        cssClass: 'h6',
        caption: 'Photo',
        items: [

          {
            dataField: 'photo_path',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => {
              if (data.editorOptions && data.editorOptions.value) {
                const $img = $('<img>', {src: data.editorOptions.value, class: 'attendee-photo-img'});
                const $imgLink = $('<a>', {href: data.editorOptions.value, target: '_blank'});
                itemElement.append($imgLink.append($img));
                // Todo: add check/uncheck photo-clear feature, store img link in data attributes when marking deleted
                const $inputDiv = $('<div>', {
                  class: 'form-check',
                  title: "If checked, it'll be deleted when you save"
                });
                const $clearInput = $('<input>', {
                  id: 'photo-clear',
                  disabled: !Attendees.utilities.editingEnabled,
                  type: 'checkbox',
                  name: 'photo-clear',
                  class: 'form-check-input',
                  onclick: "return confirm('Are you sure?')"
                });
                const $clearInputLabel = $('<label>', {
                  for: 'photo-clear',
                  text: 'delete photo',
                  class: 'form-check-label'
                });
                $inputDiv.append($clearInput);
                $inputDiv.append($clearInputLabel);
                itemElement.append($inputDiv);
              } else {
                $('<img>', {
                  src: Attendees.datagridUpdate.attendeeAttrs.dataset.emptyImageLink,
                  class: 'attendee-photo-img'
                }).appendTo(itemElement);
              }
            },
          },
          {
            template: (data, itemElement) => {
              photoFileUploader = $("<div>").attr('id', 'dxfu1').dxFileUploader(
                {
                  name: 'photo',
                  disabled: !Attendees.utilities.editingEnabled,
                  selectButtonText: 'Select photo',
                  accept: 'image/*;capture=camera',  // see if Android can take picture from camera
                  multiple: false,
                  uploadMode: 'useForm',
                  onValueChanged: (e) => {
                    if (e.value.length) {
                      $('img.attendee-photo-img')[0].src = (window.URL ? URL : webkitURL).createObjectURL(e.value[0]);
                      Attendees.datagridUpdate.attendeeFormConfigs.formData['photo'] = e.value[0];
                    }
                  },
                });
              Attendees.datagridUpdate.attendeePhotoFileUploader = photoFileUploader.dxFileUploader("instance");
              itemElement.append(photoFileUploader);
            },
          },
        ],
      },
      {
        colSpan: 20,
        colCount: 21,
        itemType: "group",
        name: 'basic-info-container',
        cssClass: 'h6',
        caption: 'Basic info: Fields after nick name can be removed by clearing & save',  // adding element in caption by $("<span>", {text:"hi 5"}).appendTo($("span.dx-form-group-caption")[1])
        items: [],  // will populate later for dynamic contacts
      },
    ];

    const potentialDuplicatesForNewAttendee = [
      {
        colSpan: 24,
        colCount: 24,
        caption: "Maybe it already exists, so there's no need to create new?",
        cssClass: 'h6',
        itemType: 'group',
        items: [
          {
            colSpan: 24,
            dataField: 'duplicates_new_attendee',
            name: 'duplicatesForNewAttendeeDatagrid',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => Attendees.datagridUpdate.initDuplicatesForNewAttendeeDatagrid(data, itemElement),
          }
        ],
      },
    ];

    if (Attendees.datagridUpdate.familyAttrDefaults.id) {
      potentialDuplicatesForNewAttendee.unshift({
        colSpan: 24,
        colCount: 24,
        caption: `What is the role of the new member in the ${Attendees.datagridUpdate.familyAttrDefaults.name} family?`,
        cssClass: 'h6 not-shrinkable',
        itemType: 'group',
        items: [
          {
            colSpan: 12,
            dataField: 'role',
            editorType: 'dxLookup',
            isRequired: true,
            label: {
              text: 'Family Role',
            },
            editorOptions: {
              valueExpr: 'id',
              displayExpr: 'title',
              placeholder: 'Select a value...',
              dataSource: new DevExpress.data.DataSource({
                paginate: false,
                store: new DevExpress.data.CustomStore({
                  key: 'id',
                  load: (searchOpts) => {
                    const params = {take: 100};
                    if (searchOpts.searchValue) {
                      const searchCondition = ['title', searchOpts.searchOperation, searchOpts.searchValue];
                      params.filter = JSON.stringify(searchCondition);
                    }
                    return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.relationsEndpoint, params);
                  },
                }),
              }),
            },
          },
        ],
      });
    }

    const moreItems = [
      {
        colSpan: 24,
        colCount: 24,
        caption: 'Addresses',
        cssClass: 'h6',
        itemType: "group",
        items: [
          {
            colSpan: 24,
            name: 'places',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => {
              const familyContentTypeId = document.querySelector('div.datagrid-attendee-update').dataset.familyContenttypeId;
              const $placeUl = $('<ul>', {class: 'list-group'});
              const newButtonAttrs = {
                text: 'Add new address+',
                disabled: !Attendees.utilities.editingEnabled,
                title: '+ Add the attendee to a new address',
                // type: 'button',
                class: 'place-button-new place-button btn-outline-primary btn button btn-sm ',
              };

              const $personalNewButton = Attendees.datagridUpdate.familyButtonFactory({
                ...newButtonAttrs,
                'data-desc': 'attendee address (' + Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original + ')',
                'data-content-type': parseInt(document.querySelector('div.datagrid-attendee-update').dataset.attendeeContenttypeId),
                'data-object-id': Attendees.datagridUpdate.attendeeId,
                'data-object-name': Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original,
              });
              const personalPlaces = Attendees.datagridUpdate.attendeeFormConfigs.formData.places || [];
              const familyattendees = Attendees.datagridUpdate.attendeeFormConfigs.formData.folkattendee_set || [];
              let $personalLi = $('<li>', {class: 'list-group-item', text: 'Personal'}).append($personalNewButton);

              personalPlaces.forEach(place => {
                const addressName = (place.street || '').replace(', USA', '');
                const $button = Attendees.datagridUpdate.familyButtonFactory({
                  // type: 'button',
                  'data-desc': 'attendee address (' + place.street + ')',
                  class: 'btn-outline-success place-button btn button btn-sm',
                  value: place.id,
                  text: (place.display_name && !addressName.includes(place.display_name) ? place.display_name + ': ' : '') + addressName,
                  'data-object-id': Attendees.datagridUpdate.attendeeId,
                  'data-object-name': Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original,
                  'data-address-raw': place.address && place.address.raw,
                });
                $personalLi = $personalLi.append($button);
              });
              let $places = $placeUl.append($personalLi);

              familyattendees.forEach(familyattendee => {
                const family = familyattendee.folk;
                if (family && family.category === 0) {
                  const $familyNewButton = Attendees.datagridUpdate.familyButtonFactory({
                    ...newButtonAttrs,
                    'data-desc': 'family address (' + family.display_name + ')',
                    'data-content-type': familyContentTypeId,
                    'data-object-id': family.id,
                    'data-object-name': family.display_name,
                  });

                  let $familyLi = $('<li>', {
                    class: 'list-group-item ' + family.id,
                    text: family.display_name,
                  }).append($familyNewButton);

                  familyattendee.folk.places.forEach(place => {
                    const addressName = (place.street || '').replace(', USA', '');
                    const $button = Attendees.datagridUpdate.familyButtonFactory({
                      // type: 'button',
                      'data-desc': family.display_name + ' family address (' + place.street + ')',
                      class: 'btn-outline-success place-button btn button btn-sm',
                      value: place.id,
                      text: (place.display_name && !addressName.includes(place.display_name) ? place.display_name + ': ' : '') + addressName,
                      'data-object-id': family.id,
                      'data-object-name': family.display_name,
                      'data-address-raw': place.address && place.address.raw,
                    });
                    $familyLi = $familyLi.append($button);
                  });
                  $places = $places.append($familyLi);
                }
              });
              itemElement.append($places);
            },
          },
        ],
      },
      {
        colSpan: 24,
        colCount: 24,
        caption: 'Families: Except current attendee, double click table cells to edit if editing mode is on. Click away or hit Enter to save',
        cssClass: 'h6',
        itemType: 'group',
        items: [
          {
            colSpan: 20,
            dataField: 'folkattendee_set',
            name: 'familyAttrs',
            label: {
              text: 'families',
            },
            template: (data, itemElement) => {
              Attendees.datagridUpdate.familyButtonFactory({
                text: 'New family for attendee+',
                disabled: !Attendees.utilities.editingEnabled,
                title: '+ Create a new family for the attendee',
                type: 'button',
                class: 'family-button-new family-button btn-outline-primary btn button btn-sm ',
              }).appendTo(itemElement);
              if (data.editorOptions && data.editorOptions.value) {
                data.editorOptions.value.forEach(folkAttendee => {
                  if (folkAttendee && typeof folkAttendee === 'object' && folkAttendee.folk.category === 0) {  // don'w show non-family in family section
                    Attendees.datagridUpdate.familyButtonFactory({value: folkAttendee.folk.id, text: folkAttendee.folk.display_name}).appendTo(itemElement);
                  }
                });
              }
            },
          },
          {
            colSpan: 4,
            dataField: 'add_new_attendee',
            editorType: 'dxDropDownButton',
            label: {
              location: 'left',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            editorOptions: {
              disabled: true,
              text: '+New family member',
              hint: 'Need at least one family to add family members',
              icon: 'user',
              items: Attendees.datagridUpdate.families,
              keyExpr: 'id',
              displayExpr: (item) => item ? `Add to ${item.display_name} family` : null,
              onItemClick: (item) => {
                window.location.href = `new?familyId=${item.itemData.id}&familyName=for%20${item.itemData.display_name}`;
              },
            },
          },
          {
            colSpan: 24,
            dataField: 'folkattendee_set',
            name: 'familyAttendeeDatagrid',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => Attendees.datagridUpdate.initFamilyAttendeeDatagrid(data, itemElement),
          }
        ],
      },
      {
        apiUrlName: 'api_attendee_relationships_view_set',
        colSpan: 24,
        colCount: 24,
        caption: 'Relationships & Access: double click table cells to edit if editing mode is on. Click away or hit Enter to save',
        cssClass: 'h6',
        itemType: "group",
        items: [
          {
            colSpan: 24,
            dataField: 'relationship_set',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => Attendees.datagridUpdate.initRelationshipDatagrid(data, itemElement),
          }
        ],
      },
      {
        apiUrlName: 'api_categorized_pasts_view_set_education',
        colSpan: 24,
        colCount: 24,
        caption: "Education: double click table cells to edit if editing mode is on. Click away or hit Enter to save",
        cssClass: 'h6',
        itemType: 'group',
        items: [
          {
            colSpan: 24,
            dataField: "past_education_set",
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => {
              Attendees.datagridUpdate.educationDatagrid = Attendees.datagridUpdate.initPastDatagrid(data, itemElement, {
                type: 'education',
                dataFieldAndOpts: {
                  category: {},
                  display_name: {},
                  'infos.show_secret': {},
                  'infos.comment': {},
                  when: {caption: 'Start'},
                  finish: {},
                },
              });
            },
          }
        ],
      },
      {
        apiUrlName: 'api_categorized_pasts_view_set_status',
        colSpan: 24,
        colCount: 24,
        caption: 'Status: double click table cells to edit if editing mode is on. Click away or hit Enter to save',
        cssClass: 'h6',
        itemType: 'group',
        items: [
          {
            colSpan: 24,
            dataField: 'past_status_set',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => {
              Attendees.datagridUpdate.statusDatagrid = Attendees.datagridUpdate.initPastDatagrid(data, itemElement, {
                type: 'status',
                dataFieldAndOpts: {
                  category: {},
                  display_name: {},
                  'infos.show_secret': {},
                  'infos.comment': {},
                  when: {},
                },
              });
            },
          }
        ],
      },
      {
        apiUrlName: 'api_categorized_pasts_view_set_note',
        colSpan: 24,
        colCount: 24,
        caption: 'Other notes',
        cssClass: 'h6',
        itemType: 'group',
        items: [
          {
            colSpan: 24,
            dataField: 'past_note_set',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => {
              Attendees.datagridUpdate.noteDatagrid = Attendees.datagridUpdate.initPastDatagrid(data, itemElement, {
                type: 'note',
                dataFieldAndOpts: {
                  category: {},
                  display_name: {caption: 'Title'},
                  'infos.show_secret': {},
                  'infos.comment': {},
                  when: {},
                },
              });
            },
          }
        ],
      },
      {
        colSpan: 24,
        colCount: 24,
        caption: 'Usually joins: register groups by buttons, or click \'edit\' to join activities',
        cssClass: 'h6',
        itemType: 'group',
        items: [
          {
            colSpan: 24,
            dataField: 'attendingmeets',
            cssClass: 'attendings-buttons',
            label: {
              text: 'registrant/group',
            },
            template: (data, itemElement) => {
                  const attendings = data.editorOptions && data.editorOptions.value || [];
                  Attendees.datagridUpdate.attendingsData = attendings.reduce((sum, now) => {
                    if (now.attending_is_removed) {
                      return {...sum}
                    }else {
                      return {
                        ...sum,
                        [now.attending_id]: now,
                      };
                    }
                  }, {});
                  Attendees.datagridUpdate.populateAttendingButtons(Object.values(Attendees.datagridUpdate.attendingsData), itemElement);
            },
          },
          {
            colSpan: 24,
            dataField: 'attendingmeets_set',
            label: {
              location: 'top',
              text: ' ',  // empty space required for removing label
              showColon: false,
            },
            template: (data, itemElement) => Attendees.datagridUpdate.initAttendingMeetsDatagrid(data, itemElement),
          },
        ],
      },
    ];

    const saveButtons = [
      {
        itemType: 'button',
        name: 'mainAttendeeFormSubmit',
        horizontalAlignment: 'left',
        buttonOptions: {
          elementAttr: {
            class: 'attendee-form-submits',  // for toggling editing mode
          },
          disabled: !Attendees.utilities.editingEnabled,
          text: 'Save Attendee details and photo',
          icon: 'save',
          hint: 'save attendee data in the page',
          type: 'default',
          useSubmitBehavior: false,
          onClick: (e) => Attendees.datagridUpdate.submitAttendeeForm(e, 'Are you sure?', {}),
        },
      },
    ];

    const deadAndDeleteButtons = [
      {
        itemType: 'button',
        name: 'mainAttendeeFormDead',
        horizontalAlignment: 'left',
        buttonOptions: {
          elementAttr: {
            class: 'attendee-form-dead',  // for toggling editing mode
          },
          disabled: !Attendees.utilities.editingEnabled,
          text: 'Pass away',
          icon: 'fas fa-dizzy',
          hint: "Attendee sadly passed away, let's ending all activities",
          type: 'danger',
          stylingMode: 'outlined',
          useSubmitBehavior: false,
          onClick: (e) => Attendees.datagridUpdate.submitAttendeeForm(e, 'Did attendee die? All activities of the attendee will be ended (not deleted).', {'X-End-All-Attendee-Activities': true}),
        },
      },
      {
        itemType: 'button',
        name: 'mainAttendeeFormDelete',
        horizontalAlignment: 'left',
        buttonOptions: {
          elementAttr: {
            class: 'attendee-form-delete',  // for toggling editing mode
          },
          disabled: !Attendees.utilities.editingEnabled,
          text: "Delete attendee",
          icon: 'trash',
          hint: "delete attendee's all data in the page",
          type: 'danger',
          onClick: (e) => {
            if (confirm("Sure to delete ALL data of the attendee? Everything of the attendee will be removed.  Instead, setting finish/deathday is usually enough!")) {
              window.scrollTo(0, 0);
              $('div.spinner-border').show();
              $.ajax({
                url: Attendees.datagridUpdate.attendeeAjaxUrl,
                method: 'DELETE',
                success: (response) => {
                  $('div.spinner-border').hide();
                  DevExpress.ui.notify(
                    {
                      message: 'delete attendee success',
                      position: {
                        my: 'center',
                        at: 'center',
                        of: window,
                      },
                    }, 'info', 2500);
                  window.location = new URL(window.location.origin);
                },
                error: (response) => {
                  console.log('Failed to delete data for main AttendeeForm, error: ', response);
                  DevExpress.ui.notify(
                    {
                      message: 'saving attendee error',
                      position: {
                        my: 'center',
                        at: 'center',
                        of: window,
                      },
                    }, 'error', 5000);
                },
              });
            }
          }
        },
      },
    ];

    const buttonItems = [
      {
        colSpan: 24,
        colCount: 24,
        cssClass: 'h6 not-shrinkable',
        itemType: 'group',
        items: isCreatingNewAttendee ? [...saveButtons] : [...saveButtons, ...deadAndDeleteButtons],
      },
    ];

    const originalItems = isCreatingNewAttendee ?
      [...basicItems, ...potentialDuplicatesForNewAttendee, ...buttonItems] :
      [...basicItems, ...buttonItems, ...moreItems];

    return {
      showValidationSummary: true,
      readOnly: !Attendees.utilities.editingEnabled,
      onContentReady: () => {
        $('div.spinner-border').hide();
        Attendees.utilities.toggleDxFormGroups();
      },
      onFieldDataChanged: (e) => {
        Attendees.datagridUpdate.attendeeMainDxForm.validate();
        if (isCreatingNewAttendee) {
          Attendees.datagridUpdate.duplicatesForNewAttendeeDatagrid.refresh();
        }
      },
      colCount: 24,
      formData: null, // will be fetched
      items: originalItems.filter(item => {
        return item.apiUrlName ? item.apiUrlName in Attendees.utilities.userApiAllowedUrlNames : true;
      }),
    };
  },

  submitAttendeeForm: (e, confirmMessage, extraHeaders) => {
    const validationResults = Attendees.datagridUpdate.attendeeMainDxForm.validate();
    if (validationResults.isValid && confirm(confirmMessage)) {
      if (extraHeaders && extraHeaders['X-End-All-Attendee-Activities']) {
        const deathdayEditor = Attendees.datagridUpdate.attendeeMainDxForm.getEditor("deathday");
        if (!deathdayEditor.option('value')) {
          deathdayEditor.option('value', new Date().toISOString());
        }
      }
      const userData = new FormData($('form#attendee-update-form')[0]);
      if (!$('input[name="photo"]')[0].value) {
        userData.delete('photo')
      }

      if (Attendees.datagridUpdate.attendeeId === 'new' && Attendees.datagridUpdate.familyAttrDefaults.id) {
        extraHeaders['X-Add-Folk'] = Attendees.datagridUpdate.familyAttrDefaults.id;
        extraHeaders['X-Folk-Role'] = userData.get('role');
        userData.delete('role');
      }

      if (Attendees.datagridUpdate.attendeeId === 'new' && Attendees.datagridUpdate.familyAttrDefaults.joinMeet) {
        extraHeaders['X-Join-Meet'] = Attendees.datagridUpdate.familyAttrDefaults.joinMeet;  // join by self attending
      }

      if (Attendees.datagridUpdate.attendeeId === 'new' && Attendees.datagridUpdate.familyAttrDefaults.joinGathering) {
        extraHeaders['X-Join-Gathering'] = Attendees.datagridUpdate.familyAttrDefaults.joinGathering;
      }

      const userInfos = Attendees.datagridUpdate.attendeeFormConfigs.formData.infos;
      userInfos['contacts'] = Attendees.utilities.trimBothKeyAndValueButKeepBasicContacts(userInfos.contacts);  // remove emptied contacts
      userData.set('infos', JSON.stringify(userInfos));

      $.ajax({
        url: Attendees.datagridUpdate.attendeeAjaxUrl,
        contentType: false,
        processData: false,
        headers: extraHeaders,
        dataType: 'json',
        data: userData,
        method: Attendees.datagridUpdate.attendeeId && Attendees.datagridUpdate.attendeeId !== 'new' ? 'PUT' : 'POST',
        success: (response) => {  // Todo: update photo link, temporarily reload to bypass the requirement
          const parser = new URL(window.location);
          parser.searchParams.set('success', 'Saving attendee success');

          if (parser.href.split('/').pop().startsWith('new')) {
            const newAttendeeIdUrl = '/' + response.id;
            window.location = parser.href.replace('/new', newAttendeeIdUrl);
          } else {
            window.location = parser.href;
          }
        },
        error: (response) => {
          console.log('Failed to save data for main AttendeeForm, error: ', response);
          console.log('formData: ', [...userData]);
          DevExpress.ui.notify(
            {
              message: 'saving attendee error',
              position: {
                my: 'center',
                at: 'center',
                of: window,
              },
            }, 'error', 5000);
        },
      });
    } else if (!validationResults.isValid) {
      validationMessages = validationResults.brokenRules.reduce((all, now) => {all.push(now.message); return all}, []);
      DevExpress.ui.notify(
        {
          message: validationMessages.join('. '),
          position: {
            my: 'center',
            at: 'center',
            of: window,
          },
        }, 'error', 2000);
    }
  },

  attendeeNameValidator: () => {
    const attendeeFromData = Attendees.datagridUpdate.attendeeMainDxForm.option('formData');
    return attendeeFromData.first_name || attendeeFromData.last_name || attendeeFromData.first_name2 || attendeeFromData.last_name2;
  },

  familyButtonFactory: (attrs) => {
    return $('<button>', {
      type: 'button',
      class: 'btn-outline-success family-button btn button btn-sm ',
      ...attrs
    });
  },

  populateAttendingButtons: (attendings, itemElement) => {
    itemElement.empty();

    $('<button>').attr({
      disabled: !Attendees.utilities.editingEnabled,
      title: '+ Add a new attending',
      type: 'button',
      class: 'attending-button-new attending-button btn-outline-primary btn button btn-sm'
    }).text('+ Register group').appendTo(itemElement);

    attendings.forEach(attending => {
      if (attending && attending.attending_id) {
        let label, title;
        if (attending.attending_label){
          const originalLabel = (attending.attending_label).match(/\(([^)]+)\)/).pop();  // get substring between parentheses
          label = originalLabel.replace(Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original, 'Self');
          title = label;
        } else {
          const registrant_name = attending.registrant.replace(Attendees.datagridUpdate.attendeeFormConfigs.formData.infos.names.original, 'Self');
          label = attending.registration_assembly ? registrant_name + ' ' + attending.registration_assembly : registrant_name + ' Generic';
          title = attending.registrant;
        }
        $('<button>', {
          text: label,
          type: 'button',
          title: title,
          class: 'attending-button btn button btn-sm btn-outline-success',
          value: attending.attending_id,
        }).appendTo(itemElement);
      }
    });
  },

  populateBasicInfoBlock: (allContacts = Attendees.datagridUpdate.attendeeMainDxForm.option('formData').infos.contacts) => {
    const basicInfoItems = [
      {
        colSpan: 7,
        dataField: 'first_name',
        editorOptions: {
          placeholder: 'English',
        },
        validationRules: [
          {
            type: 'custom',
            reevaluate: true,
            validationCallback: Attendees.datagridUpdate.attendeeNameValidator,
            message: 'first or last name is required'
          },
          {
            type: 'stringLength',
            reevaluate: true,
            max: 25,
            message: 'No more than 25 characters'
          },
        ],
      },
      {
        colSpan: 7,
        dataField: 'last_name',
        editorOptions: {
          placeholder: 'English',
        },
        validationRules: [
          {
            type: 'custom',
            validationCallback: Attendees.datagridUpdate.attendeeNameValidator,
            message: 'first or last name is required'
          },
          {
            type: 'stringLength',
            max: 25,
            message: 'No more than 25 characters'
          },
        ],
      },
      {
        colSpan: 7,
        dataField: 'division',
        editorType: 'dxSelectBox',
        isRequired: true,
        label: {
          text: 'Major Division',
        },
        editorOptions: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          placeholder: 'Select a value...',
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'id',
              loadMode: 'raw',
              load: () => {
                // const d = $.Deferred();
                // $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.divisionsEndpoint)
                //   .done( response => {
                //     d.resolve(response.data);
                //   });
                // return d.promise();
                return Attendees.datagridUpdate.divisions;
              }
            })
          }),
          onValueChanged: (e) => {
            for (const property in Attendees.datagridUpdate.divisionShowAttendeeInfos[e.value] || {}) {
              const itemName = `basic-info-container.${property}`;
              const itemValue = Attendees.datagridUpdate.divisionShowAttendeeInfos[e.value][property];
              Attendees.datagridUpdate.attendeeMainDxForm.itemOption(itemName, 'visible', itemValue);
            }
          },
        },
      },
      {
        colSpan: 7,
        dataField: 'last_name2',
        validationRules: [
          {
            type: 'custom',
            validationCallback: Attendees.datagridUpdate.attendeeNameValidator,
            message: 'first or last name is required'
          },
          {
            type: 'stringLength',
            max: 8,
            message: "No more than 8 characters"
          }
        ],
      },
      {
        colSpan: 7,
        dataField: 'first_name2',
        validationRules: [
          {
            type: 'custom',
            validationCallback: Attendees.datagridUpdate.attendeeNameValidator,
            message: 'first or last name is required'
          },
          {
            type: 'stringLength',
            max: 12,
            message: "No more than 12 characters"
          }
        ],
      },
      {
        colSpan: 7,
        dataField: 'gender',
        editorType: 'dxSelectBox',
        isRequired: true,
        editorOptions: {
          dataSource: Attendees.utilities.genderEnums(),
          valueExpr: 'name',
          displayExpr: 'name',
        },
        validationRules: [
          {
            type: 'required',
            message: 'gender is required'
          },
        ],
      },
      {
        colSpan: 7,
        dataField: 'actual_birthday',
        helpText: 'month / day / year',
        editorType: 'dxDateBox',
        label: {
          text: 'Real birthday',
        },
        editorOptions: {
          showClearButton: true,
          placeholder: 'click calendar',
          elementAttr: {
            title: 'month, day and year are all required',
          },
        },
      },
      {
        colSpan: 7,
        dataField: 'estimated_birthday',
        helpText: 'YYYY-MM-DD',
        label: {
          text: 'Guess birthday',
        },
//        editorType: 'dxDateBox',
        editorOptions: {
          showClearButton: true,
//          placeholder: 'click calendar',
          elementAttr: {
            title: 'Enter your best guess year for the age estimation, please enter year 1800 if year unknown. YYYY-MM or YYYY is also acceptable',
          },
        },
      },
      {
        colSpan: 7,
        dataField: 'deathday',
        editorType: 'dxDateBox',
        editorOptions: {
          showClearButton: true,
          placeholder: 'click calendar',
        },
      },
      {
        colSpan: 7,
        dataField: 'infos.contacts.phone1',  // DxTextBox maskRules can't accept variable length of country codes
        helpText: 'Will be in directory',
        label: {
          text: 'phone1',
        },
        editorOptions: {
          placeholder: '+1(000)000-0000',
          attr: { 'autocomplete': false },
        },
        template: (data, itemElement) => {
          const options = {
            readOnly: !Attendees.utilities.editingEnabled,
            value: Attendees.utilities.phoneNumberFormatter(data.editorOptions.value),
            onValueChanged: (e) => data.component.updateData(data.dataField, e.value.replace(/[-()]/g, '')),
          };
          const phoneEditor = $("<div id='attendee-mainform-phone1'>").dxTextBox(options);
          itemElement.append(phoneEditor);
          Attendees.datagridUpdate.phone1 = phoneEditor.dxTextBox('instance');
        },
        validationRules: [
          {
            type: 'pattern',
            pattern: /^(\+\d{1,3})(\(\d{0,3}\))([0-9a-zA-Z]{2,6})-([,0-9a-zA-Z]{3,10})$/,
            message: "Must be '+' national&area code like +1(510)123-4567,890 Comma for extension, for Singapore enter +65()1234-5678",
          },
        ],
      },
      {
        colSpan: 7,
        dataField: 'infos.contacts.phone2',
        helpText: 'Will NOT be in directory',
        label: {
          text: 'phone2',
        },
        editorOptions: {
          placeholder: '+1(000)000-0000',
          attr: { 'autocomplete': false },
        },
        template: (data, itemElement) => {
          const options = {
            readOnly: !Attendees.utilities.editingEnabled,
            value: Attendees.utilities.phoneNumberFormatter(data.editorOptions.value),
            onValueChanged: (e) => data.component.updateData(data.dataField, e.value.replace(/[-()]/g, '')),
          };
          const phoneEditor = $("<div id='attendee-mainform-phone2'>").dxTextBox(options);
          itemElement.append(phoneEditor);
          Attendees.datagridUpdate.phone2 = phoneEditor.dxTextBox('instance');
        },
        validationRules: [
          {
            type: 'pattern',
            pattern: /^(\+\d{1,3})(\(\d{0,3}\))([0-9a-zA-Z]{2,6})-([,0-9a-zA-Z]{3,10})$/,
            message: "Must be '+' national&area code like +1(510)123-4567,890 Comma for extension, for Singapore enter +65()1234-5678",
          },
        ],
      },
      {
        colSpan: 7,
        dataField: 'infos.names.nick',
        label: {
          text: 'nick name',
        },
      },
      {
        colSpan: 7,
        dataField: 'infos.contacts.email1',
        helpText: 'Will be in directory',
        label: {
          text: 'email1',
        },
        validationRules: [
          {
            type: "email",
            message: "Email is invalid"
          },
        ],
      },
      {
        colSpan: 7,
        dataField: 'infos.contacts.email2',
        helpText: 'Will NOT be in directory',
        label: {
          text: 'email2',
        },
        validationRules: [
          {
            type: "email",
            message: "Email is invalid"
          },
        ],
      },
//      {
//        colSpan: 7,
//        dataField: 'infos.fixed.mobility',   // for retreat only
//        label: {
//          text: 'mobility',
//        },
//      },
      {
        colSpan: 7,
        visible: Attendees.datagridUpdate.divisionShowAttendeeInfos[Attendees.datagridUpdate.attendeeFormConfigs.formData.division || Attendees.datagridUpdate.divisions[0].id]['infos-grade'],
        name: 'infos-grade',
        dataField: 'infos.fixed.grade',
        label: {
          text: 'School grade',
        },
      },
      {
        colSpan: 7,
        dataField: 'infos.fixed.insurer',
        name: 'infos-insurer',
        visible: Attendees.datagridUpdate.divisionShowAttendeeInfos[Attendees.datagridUpdate.attendeeFormConfigs.formData.division || Attendees.datagridUpdate.divisions[0].id]['infos-insurer'],
        label: {
          text: 'Insurer',
        },
      },
      {
        colSpan: 7,
        dataField: 'infos.fixed.food_pref',
        label: {
          text: 'Food pref',
        },
      },
    ];

    for (const contactKey in allContacts) {
      if (allContacts.hasOwnProperty(contactKey) && !(contactKey in Attendees.utilities.basicContacts)) {
        basicInfoItems.push({
          colSpan: 7,
          dataField: 'infos.contacts.' + contactKey,
          label: {
            text: contactKey,
          },
        });
      }
    }
    Attendees.datagridUpdate.attendeeMainDxForm.itemOption('basic-info-container', 'items', basicInfoItems);
  },

  contactPopupDxFormConfig: {
    maxWidth: '50%',
    maxHeight: '50%',
    visible: true,
    title: 'Add Contact',
    position: {
      my: 'center',
      at: 'center',
      of: window,
    },
    showCloseButton: true,  // for mobile browser
    dragEnabled: true,
    contentTemplate: (e) => {
      const formContainer = $('<div class="contact-form">');
      Attendees.datagridUpdate.contactPopupDxForm = formContainer.dxForm({
        scrollingEnabled: true,
        showColonAfterLabel: false,
        requiredMark: '*',
        showValidationSummary: true,
        items: [
          {
            dataField: 'contactKey',
            editorOptions: {
              placeholder: 'for example: WeChat1',
            },
            helpText: 'Any contact such as email3/phone3/fax1, etc',
            label: {
              text: 'Contact method',
            },
            isRequired: true,
            validationRules: [
              {
                type: 'required',
                message: 'Contact method is required'
              },
              {
                type: 'stringLength',
                min: 2,
                message: 'Contact method can\'t be less than 2 characters'
              },
              {
                type: 'custom',
                message: 'That contact method exists already',
                validationCallback: (e) => {
                  const currentContacts = Attendees.datagridUpdate.attendeeMainDxForm.option('formData').infos.contacts;
                  return !Object.keys(currentContacts).includes(e.value.trim());
                }
              }
            ],
          },
          {
            dataField: 'contactValue',
            editorOptions: {
              placeholder: 'for example: JohnSmith1225',
            },
            helpText: 'Contact such as name@email.com/+15101234567 etc',
            label: {
              text: 'Contact content',
            },
            isRequired: true,
            validationRules: [
              {
                type: 'required',
                message: 'Contact content is required'
              },
              {
                type: 'stringLength',
                min: 2,
                message: "Contact content can't be less than 2 characters"
              },
            ],
          },
          {
            itemType: 'button',
            horizontalAlignment: 'left',
            buttonOptions: {
              elementAttr: {
                class: 'attendee-form-submits',    // for toggling editing mode
              },
              disabled: !Attendees.utilities.editingEnabled,
              text: 'Save Custom Contact',
              icon: 'save',
              hint: 'save Custom Contact in the popup',
              type: 'default',
              useSubmitBehavior: false,
              onClick: (e) => {
                if (Attendees.datagridUpdate.contactPopupDxForm.validate().isValid) {
                  const currentInfos = Attendees.datagridUpdate.attendeeMainDxForm.option('formData').infos;
                  const newContact = Attendees.datagridUpdate.contactPopupDxForm.option('formData');
                  const trimmedNewContact = Attendees.utilities.trimBothKeyAndValueButKeepBasicContacts(newContact);
                  currentInfos.contacts = Attendees.utilities.trimBothKeyAndValueButKeepBasicContacts(currentInfos.contacts);  // remove emptied contacts
                  currentInfos.contacts[trimmedNewContact.contactKey] = trimmedNewContact.contactValue;

                  $.ajax({
                    url: Attendees.datagridUpdate.attendeeAjaxUrl,
                    data: JSON.stringify({infos: currentInfos}),
                    dataType: 'json',
                    contentType: 'application/json; charset=utf-8',
                    method: 'PATCH',
                    success: (response) => {
                      Attendees.datagridUpdate.contactPopupDxForm.resetValues();
                      Attendees.datagridUpdate.populateBasicInfoBlock(response.infos.contacts);
                      Attendees.datagridUpdate.contactPopup.hide();
                      DevExpress.ui.notify(
                        {
                          message: "saving custom contact success",
                          position: {
                            my: 'center',
                            at: 'center',
                            of: window,
                          },
                        }, 'success', 2500);
                    },
                    error: (response) => {
                      console.log('Failed to save data for custom contact in Popup, response and infos data: ', response, Attendees.datagridUpdate.attendeeMainDxForm.option('formData').infos);
                      Attendees.datagridUpdate.contactPopup.hide();
                      DevExpress.ui.notify(
                        {
                          message: 'saving custom contact error',
                          position: {
                            my: 'center',
                            at: 'center',
                            of: window,
                          },
                        }, 'error', 5000);
                    },
                  });
                }
              },
            },
          },
        ],
      }).dxForm('instance');
      e.append(formContainer);
    },
  },


  ///////////////////////  Attending Popup and DxForm  ///////////////////////


  initAttendingPopupDxForm: (event) => {
    const attendingButton = event.target;
    Attendees.datagridUpdate.attendingPopup = $("div.popup-attending-update").dxPopup(Attendees.datagridUpdate.attendingPopupDxFormConfig(attendingButton)).dxPopup('instance');
    Attendees.datagridUpdate.fetchAttendingFormData(attendingButton);
  },

  fetchAttendingFormData: (attendingButton) => {
    if (attendingButton.value) {
      $.ajax({
        url: $('form#attending-update-popup-form').attr('action') + attendingButton.value + '/',
        success: (response) => {
          Attendees.datagridUpdate.attendingPopupDxFormData = response;
          Attendees.datagridUpdate.attendingPopupDxForm.option('formData', response);
          // Attendees.datagridUpdate.attendingPopupDxForm.option('onFieldDataChanged', (e) => e.component.validate());
        },
        error: (response) => console.log('Failed to fetch data for AttendingForm in Popup, error: ', response),
      });
    }
  },

  attendingPopupDxFormConfig: (attendingButton) => {
    const ajaxUrl = $('form#attending-update-popup-form').attr('action') + (attendingButton.value ? attendingButton.value + '/' : '');
    return {
      visible: true,
      title: attendingButton.value ? 'Viewing attending' : 'Creating attending',
      minwidth: '20%',
      minheight: '30%',
      position: {
        my: 'center',
        at: 'center',
        of: window,
      },
      onHiding: () => {
        const $existingAttendeeSelector = $('div.attendee-lookup-search').dxLookup('instance');
        if ($existingAttendeeSelector) $existingAttendeeSelector.close();
      },
      dragEnabled: true,
      showCloseButton: true,  // for mobile browser
      contentTemplate: (e) => {
        const formContainer = $('<div class="attendingForm">');
        Attendees.datagridUpdate.attendingPopupDxForm = formContainer.dxForm({
          readOnly: !Attendees.utilities.editingEnabled,
          formData: Attendees.datagridUpdate.attendingDefaults,
          colCount: 3,
          scrollingEnabled: true,
          showColonAfterLabel: false,
          requiredMark: '*',
          labelLocation: 'top',
          minColWidth: '20%',
          showValidationSummary: true,
          items: [
            {
              dataField: 'registration.assembly',
              editorType: 'dxSelectBox',
              validationRules: [
                {
                  type: 'async',
                  message: 'Same Group/Registrant exists, please select other assembly or close the popup to find that registration',
                  validationCallback: (params) =>  Attendees.datagridUpdate.validateRegistration(params.value),
                },
              ],
              helpText: 'Same Group/Registrant can only register once',
              label: {
                text: 'Belonging Group (Assembly)',
                showColon: true,
              },
              editorOptions: {
                valueExpr: 'id',
                displayExpr: 'division_assembly_name',
                placeholder: 'Select a value...',
                showClearButton: true,
                dataSource: new DevExpress.data.DataSource({
                  store: new DevExpress.data.CustomStore({
                    key: 'id',
                    loadMode: 'raw',
                    load: () => {
                      const d = $.Deferred();
                      $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.assembliesEndpoint).done((response) => {
                        d.resolve(response.data);
                      });
                      return d.promise();
                    },
                  })
                }),
              },
            },
            {
              dataField: 'registration.registrant',
              validationRules: [
                {
                  type: 'async',
                  message: 'Same Group/Registrant exists, please select other registrant or close the popup to find that registration',
                  validationCallback: (params) =>  Attendees.datagridUpdate.validateRegistration(params.value),
                },
              ],
              helpText: 'Same Group/Registrant can only register once',
              label: {
                text: 'Registrant',
              },
              editorType: 'dxLookup',
              editorOptions: {
                showClearButton: true,
                elementAttr: {
                  class: 'attendee-lookup-search',  // calling closing by the parent
                },
                valueExpr: 'id',
                displayExpr: 'infos.names.original',
                placeholder: 'Select a value...',
                // searchExpr: ['first_name', 'last_name'],
                searchPlaceholder: 'Search attendee',
                minSearchLength: 3,  // cause values disappeared in drop down
                searchTimeout: 200,  // cause values disappeared in drop down
                dropDownOptions: {
                  showTitle: false,
                  closeOnOutsideClick: true,
                },
                dataSource: Attendees.datagridUpdate.attendeeSource,
              },
            },
            {
              dataField: 'category',
              helpText: 'help text can be changed in /static/js /persons /datagrid_attendee_update_view.js',
              isRequired: true,
            },
            {
              itemType: 'button',
              horizontalAlignment: 'left',
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Save Attending',
                icon: 'save',
                hint: 'save attending data in the popup',
                type: 'default',
                useSubmitBehavior: false,
                onClick: (clickEvent) => {
                  const validationResult = clickEvent.validationGroup.validate();
                  validationResult.status === 'pending' && validationResult.complete.then((validation) => {
                    if (validation.status === 'valid' && confirm('are you sure to submit the popup attendingForm?')) {
                      const userData = Attendees.datagridUpdate.attendingPopupDxForm.option('formData');

                      $.ajax({
                        url: ajaxUrl,
                        data: JSON.stringify(userData),
                        dataType: 'json',
                        contentType: 'application/json; charset=utf-8',
                        method: userData.id ? 'PUT' : 'POST',
                        success: (response) => {
                          Attendees.datagridUpdate.attendingPopup.hide();
                          DevExpress.ui.notify(
                            {
                              message: 'saving attending success',
                              position: {
                                my: 'center',
                                at: 'center',
                                of: window,
                              },
                            }, 'success', 2500);
                          response.attending_id = response.id;
                          Attendees.datagridUpdate.attendingsData[response.id] = response;
                          Attendees.datagridUpdate.populateAttendingButtons(Object.values(Attendees.datagridUpdate.attendingsData), $('div.attendings-buttons > div.dx-field-item-content'));
                        },
                        error: (response) => {
                          console.log('Failed to save data for AttendingForm in Popup, error: ', response);
                          console.log('formData: ', userData);
                          DevExpress.ui.notify(
                            {
                              message: 'saving attending error',
                              position: {
                                my: 'center',
                                at: 'center',
                                of: window,
                              },
                            }, 'error', 5000);
                        },
                      });
                    }
                  });
                }
              },
            },
            {
              itemType: 'button',
              horizontalAlignment: 'left',
              name: 'deleteAttendingButton',
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Delete Attending',
                icon: 'trash',
                hint: 'delete the current Attending in the popup',
                type: 'danger',
                useSubmitBehavior: false,
                onClick: (clickEvent) => {
                  if (confirm('Are you sure to delete the attending and all its registrations&activities? Instead, setting "finish" dates in all its activities in the table is usually enough!')) {
                    $.ajax({
                      url: ajaxUrl,
                      method: 'DELETE',
                      success: (response) => {
                        Attendees.datagridUpdate.attendingPopup.hide();
                        DevExpress.ui.notify(
                          {
                            message: 'attending deleted successfully',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'info', 2500);
                        attendingButton.remove();
                        Attendees.datagridUpdate.attendingMeetDatagrid.refresh();
                      },
                      error: (response) => {
                        console.log('Failed to delete attending in Popup, error: ', response);
                        DevExpress.ui.notify(
                          {
                            message: 'delete attending error!',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'error', 5000);
                      },
                    });
                  }
                },
              },
            },
          ]
        }).dxForm('instance');
        e.append(formContainer);
      }
    };
  },

  validateRegistration: (value) => {
    const registration = Attendees.datagridUpdate.attendingPopupDxForm.option('formData') && Attendees.datagridUpdate.attendingPopupDxForm.option('formData').registration || {};
    var d = $.Deferred();
    if (!Attendees.utilities.editingEnabled) {
      d.resolve();
    }else {
      $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.registrationsEndpoint, {
        assembly: registration.assembly,
        registrant: registration.registrant,
      }).done((response) => {
        const registrations = response && response.data || [];
        if (registrations.length < 1){
          d.resolve();
        } else if(registrations.length < 2){
          registrations[0].id === registration.id ? d.resolve() : d.reject();
        }
        d.reject();
      });
    }
    return d.promise();
  },

  attendeeSource: new DevExpress.data.CustomStore({
    key: 'id',
    load: (loadOptions) => {
      // if (!Attendees.utilities.editingEnabled) return [Attendees.datagridUpdate.attendingPopupDxFormData.registration.registrant];

      const deferred = $.Deferred();
      const args = {};

      [
        'skip',
        'take',
        'sort',
        'filter',
        'searchExpr',
        'searchOperation',
        'searchValue',
        'group',
      ].forEach((i) => {
        if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
          args[i] = loadOptions[i];
      });

      $.ajax({
        url: Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeEndpoint,
        dataType: 'json',
        data: args,
        success: (result) => {
          const registrant = Attendees.datagridUpdate.attendingPopupDxFormData.registration && Attendees.datagridUpdate.attendingPopupDxFormData.registration.registrant || null;
          const resulting_attendees = registrant ? result.data.concat([registrant]) : result.data;
          deferred.resolve(resulting_attendees, {
            totalCount: result.totalCount,
            summary: result.summary,
            groupCount: result.groupCount
          });
        },
        error: (response) => {
          console.log('ajax error here is response: ', response);
          deferred.reject('Data Loading Error, probably time out?');
        },
        timeout: 7000,
      });

      return deferred.promise();
    },
    byKey: (key) => {
      // if (!Attendees.utilities.editingEnabled && Attendees.datagridUpdate.placePopupDxFormData) {
      //   const mainAttendee = Attendees.datagridUpdate.attendingPopupDxFormData.registration && Attendees.datagridUpdate.attendingPopupDxFormData.registration.registrant || null;
      //   return mainAttendee ? [mainAttendee] : [];
      // } else {
        const d = new $.Deferred();
        $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeEndpoint + key + '/')
          .done((result) => {
            d.resolve(result);
          });
        return d.promise();
      // }
    },
  }),


  ///////////////////////  Place (Address) Popup and DxForm  ///////////////////////


  initPlacePopupDxForm: (event) => {
    const placeButton = event.target;
    Attendees.datagridUpdate.placePopup = $('div.popup-place-update').dxPopup(Attendees.datagridUpdate.placePopupDxFormConfig(placeButton)).dxPopup('instance');
    Attendees.datagridUpdate.fetchPlaceFormData(placeButton);
  },

  placePopupDxFormConfig: (placeButton) => {
    const ajaxUrl = $('form#place-update-popup-form').attr('action') + (placeButton.value ? placeButton.value + '/' : '');
    return {
      visible: true,
      title: (placeButton.value ? 'Viewing ' : 'Creating ') + placeButton.dataset.desc,
      minwidth: '20%',
      minheight: '30%',
      position: {
        my: 'center',
        at: 'center',
        of: window,
      },
      onHiding: () => {
        const $existingAddressSelector = $('div.address-lookup-search').dxLookup('instance');
        if ($existingAddressSelector) $existingAddressSelector.close();
        const $existingStateSelector = $('div.state-lookup-search').dxLookup('instance');
        if ($existingStateSelector) $existingStateSelector.close();
      },
      dragEnabled: true,
      showCloseButton: true,  // for mobile browser
      contentTemplate: (e) => {
        const formContainer = $('<div class="locate-form">');
        Attendees.datagridUpdate.placePopupDxForm = formContainer.dxForm({
          readOnly: !Attendees.utilities.editingEnabled,
          formData: {
            ...Attendees.datagridUpdate.placeDefaults,
            content_type: parseInt(placeButton.dataset.contentType),
            object_id: placeButton.dataset.objectId,
          },
          colCount: 12,
          scrollingEnabled: true,
          showColonAfterLabel: false,
          requiredMark: '*',
          labelLocation: 'top',
          minColWidth: '20%',
          showValidationSummary: true,
          items: [
            {
              colSpan: 3,
              dataField: 'display_name',
              // label: {
              //   text: 'Dwelling Reason',
              // },
              helpText: 'Why attendee occupy here',
              isRequired: true,
              editorOptions: {
                placeholder: 'Main/parent/past, etc',
              },
            },
            {
              colSpan: 3,
              dataField: 'display_order',
              helpText: '0 is shown before 1,2...',
              isRequired: true,
              editorOptions: {
                placeholder: '0/1/2/3, etc',
              },
              validationRules: [
                {
                  type: 'range',
                  max: 32767,
                  min: 0,
                  message: 'display_order should be between 0 and 32767'
                },
                {
                  type: 'required',
                  message: 'display_order is required'
                },
              ],
            },
            {
              colSpan: 3,
              dataField: 'start',
              editorType: 'dxDateBox',
              label: {
                text: 'stay from',
              },
              helpText: 'When moved in?',
              editorOptions: {
                type: 'date',
                showClearButton: true,
                dateSerializationFormat: 'yyyy-MM-dd',
                placeholder: 'click calendar',
              },
            },
            {
              colSpan: 3,
              dataField: 'finish',
              editorType: 'dxDateBox',
              label: {
                text: 'stay until',
              },
              helpText: 'When moved out?',
              editorOptions: {
                type: 'date',
                showClearButton: true,
                dateSerializationFormat: 'yyyy-MM-dd',
                placeholder: 'click calendar',
              },
            },
            {
              dataField: 'address',
              label: {
                location: 'left',
                text: ' ',  // empty space required for removing label
                showColon: false,
              },
              colSpan: 12,
              template: (data, itemElement) => {
                if (placeButton.dataset.addressRaw) {
                  itemElement.append($(`<span>Google Map Link: </span><a target="_blank" href="https://www.google.com/maps/place/${placeButton.dataset.addressRaw.replaceAll(" ", "+")}">${placeButton.dataset.addressRaw}</a>`));
                }
              },
            },
            {
              colSpan: 12,
              dataField: 'address.id',
              name: 'existingAddressSelector',
              label: {
                text: 'Address',
              },
              editorType: 'dxLookup',
              editorOptions: {
                showClearButton: true,
                elementAttr: {
                  class: 'address-lookup-search',  // calling closing by the parent
                },
                valueExpr: 'id',
                displayExpr: 'formatted',
                placeholder: 'Select a value...',
                searchExpr: ['street_number', 'formatted'],
//                searchMode: 'startswith',
                searchPlaceholder: 'Search addresses by family name or address',
                minSearchLength: 3,  // cause values disappeared in drop down
                searchTimeout: 200,  // cause values disappeared in drop down
                dropDownOptions: {
                  showTitle: false,
                  closeOnOutsideClick: true,
                },
                dataSource: Attendees.datagridUpdate.addressSource,
                onValueChanged: (e) => {
                  if (e.previousValue !== e.value) {
                    const selectedAddress = $('div.address-lookup-search').dxLookup('instance')._dataSource._items.find(x => x.id === e.value);
                    if (selectedAddress){
                      Attendees.datagridUpdate.placePopupDxForm.updateData('address', selectedAddress);
                    }
                  }
                },
              },
            },
            {
              itemType: 'group',
              visible: false,
              name: 'NewAddressItems',
              colSpan: 12,
              colCount: 12,
              items: [
                {
                  colSpan: 4,
                  dataField: 'address.street_number',
                  helpText: 'no road name please',
                  label: {
                    text: 'Door number',
                  },
                  editorOptions: {
                    placeholder: "example: '22416'",
                  },
                },
                {
                  colSpan: 4,
                  dataField: 'address.route',
                  helpText: 'no door number please',
                  label: {
                    text: 'Road',
                  },
                  editorOptions: {
                    placeholder: "example: 'A street'",
                  },
                },
                {
                  colSpan: 4,
                  dataField: 'address.extra',
                  helpText: 'suite/floor number, etc',
                  label: {
                    text: 'Extra: unit/apt',
                  },
                  editorOptions: {
                    placeholder: 'example: Apt 2G',
                  },
                },
                {
                  colSpan: 4,
                  dataField: 'address.city',
                  name: 'locality',
                  helpText: 'Village/Town name',
                  label: {
                    text: 'City',
                  },
                  editorOptions: {
                    placeholder: "example: 'San Francisco'",
                  },
                },
                {
                  colSpan: 4,
                  dataField: 'address.postal_code',
                  helpText: 'ZIP code',
                  editorOptions: {
                    placeholder: "example: '94106'",
                  },
                },
                {
                  colSpan: 4,
                  dataField: 'address.state_id',
                  label: {
                    text: 'State',
                  },
                  editorType: 'dxLookup',
                  editorOptions: {
                    elementAttr: {
                      class: 'state-lookup-search',  // calling closing by the parent
                    },
                    valueExpr: 'id',
                    displayExpr: (item) => {
                      return item ? item.name + ", " + item.country_name : null;
                    },
                    placeholder: "Example: 'CA'",
                    searchExpr: ['name'],
                    //                searchMode: 'startswith',
                    searchPlaceholder: 'Search states',
                    minSearchLength: 2,  // cause values disappeared in drop down
                    searchTimeout: 200,  // cause values disappeared in drop down
                    dropDownOptions: {
                      showTitle: false,
                      closeOnOutsideClick: true,
                    },
                    dataSource: Attendees.datagridUpdate.stateSource,
                    // onValueChanged: (e) => {
                    //   if (e.previousValue && e.previousValue !== e.value) {
                    //     const selectedState = $('div.state-lookup-search').dxLookup('instance')._dataSource._items.find(x => x.id === e.value);
                    //     console.log("hi 2004 here is selectedState: ", selectedState);
                    //   }
                    // },
                  },
                },
              ],
            },
            {
              colSpan: 3,
              itemType: 'button',
              horizontalAlignment: 'left',
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Save Place',
                icon: 'save',
                hint: 'save Place data in the popup',
                type: 'default',
                useSubmitBehavior: true,
                onClick: (clickEvent) => {
                  if (confirm('Are you sure to submit the popup Place Form?')) {
                    const userData = Attendees.datagridUpdate.placePopupDxForm.option('formData');
                    const addressMaybeEdited = Attendees.datagridUpdate.placePopupDxForm.itemOption('NewAddressItems').visible;

                    if (addressMaybeEdited) {  // no address id means user creating new address
                      const newAddressExtra = Attendees.datagridUpdate.placePopupDxForm.getEditor("address.extra").option('value') && Attendees.datagridUpdate.placePopupDxForm.getEditor("address.extra").option('value').trim();
                      const newStreetNumber = Attendees.datagridUpdate.placePopupDxForm.getEditor("address.street_number").option('value') && Attendees.datagridUpdate.placePopupDxForm.getEditor("address.street_number").option('value').trim();
                      const newRoute = Attendees.datagridUpdate.placePopupDxForm.getEditor("address.route").option('value').trim();
                      const newCity = Attendees.datagridUpdate.placePopupDxForm.getEditor("address.city").option('value').trim();
                      const newZIP = Attendees.datagridUpdate.placePopupDxForm.getEditor("address.postal_code").option('value').trim();
                      const newStateAttrs = Attendees.datagridUpdate.placePopupDxForm.getEditor("address.state_id")._options;
                      const newAddressWithoutZip = [newStreetNumber, newRoute, newAddressExtra, newCity, newStateAttrs.selectedItem.code].filter(item => !!item).join(', ');
                      const newAddressText = newAddressWithoutZip + (newZIP ? ', ' + newZIP + ', ' : ', ' ) + newStateAttrs.selectedItem.country_name;

                      if (!(userData.address && userData.address.id)) {
                        userData.address = {
                          raw: 'new',     // for bypassing DRF validations from Django-Address model
                          new_address: {  // for creating new django-address instance bypassing DRF model validations
                            raw: newAddressText,
                            type: 'street',   // use Django-admin to change if needed
                            extra: newAddressExtra,
                            formatted: placeButton.dataset.objectName + ': ' + newAddressText,
                            street_number: newStreetNumber,
                            route: newRoute,
                            locality: newCity,
                            post_code: newZIP,
                            state: newStateAttrs.selectedItem.name,
                            state_code: newStateAttrs.selectedItem.code,
                            country: newStateAttrs.selectedItem.country_name,
                            country_code: newStateAttrs.selectedItem.country_code,
                          },
                        };
                      }else{
                        userData.address.raw = newAddressText;
                        userData.address.formatted = placeButton.dataset.objectName + ': ' + newAddressText;
                      }
                    }

                    $.ajax({
                      url: ajaxUrl,
                      data: JSON.stringify(userData),
                      dataType: 'json',
                      contentType: 'application/json; charset=utf-8',
                      method: userData.id ? 'PUT' : 'POST',
                      success: (savedPlace) => {
                        Attendees.datagridUpdate.placePopup.hide();
                        DevExpress.ui.notify(
                          {
                            message: 'saving place success',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            }
                          }, 'success', 2500);

                        const clickedButtonDescPrefix = placeButton.dataset.desc.split(' (')[0];
                        const newDesc = clickedButtonDescPrefix + ' (' + savedPlace.address.formatted + ')';
                        const newText = savedPlace.display_name + ': ' + savedPlace.address.formatted;
                        if (placeButton.value) {
                          placeButton.dataset.desc = newDesc;
                          placeButton.textContent = newText;
                          placeButton.dataset.addressRaw = savedPlace.address && savedPlace.address.raw;
                        } else {
                          Attendees.datagridUpdate.familyButtonFactory({
                            class: placeButton.className.replace('place-button-new', '').replace('btn-outline-primary', 'btn-outline-success'),
                            value: savedPlace.id,
                            text: newText,
                            title: newDesc,
                            'data-desc': newDesc,
                            'data-object-id': placeButton.dataset.objectId,
                            'data-object-name': placeButton.dataset.objectName,
                            'data-content-type': placeButton.dataset.contentType,
                            'data-address-raw': savedPlace.address && savedPlace.address.raw,
                          }).insertAfter(placeButton);
                        }
                      },
                      error: (response) => {
                        console.log('Failed to save data for place Form in Popup, error: ', response);
                        console.log('formData: ', userData);
                        DevExpress.ui.notify(
                          {
                            message: 'saving locate error',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            }
                          }, 'error', 5000);
                      },
                    });
                  }
                },
              },
            },
            {
              colSpan: 3,
              itemType: 'button',
              horizontalAlignment: 'left',
              name: 'editAddressButton',
              visible: true,
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Edit the address',
                icon: 'edit',
                hint: 'Modifying the current address, without creating one',
                type: 'success',
                useSubmitBehavior: false,
                onClick: (clickEvent) => {
                  if (confirm(`Are you sure to edit the ${placeButton.dataset.objectName}'s address?`)) {
                    Attendees.datagridUpdate.placePopupDxForm.itemOption('NewAddressItems', 'visible', true);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('address.id').option('visible', false);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('address.id').option('disable', true);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('editAddressButton').option('visible', false);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('newAddressButton').option('visible', false);
                  }
                },
              },
            },
            {
              colSpan: 3,
              itemType: 'button',
              horizontalAlignment: 'left',
              name: 'newAddressButton',
              visible: true,
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Add new address',
                icon: 'home',
                hint: "Can't find exiting address, add a new address here",
                type: 'normal',
                useSubmitBehavior: false,
                onClick: (clickEvent) => {
                  if (confirm('Are you sure to add new address?')) {
                    Attendees.datagridUpdate.placePopupDxForm.itemOption('NewAddressItems', 'visible', true);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('address.id').option('visible', false);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('address.id').option('disable', true);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('newAddressButton').option('visible', false);
                    Attendees.datagridUpdate.placePopupDxForm.getEditor('editAddressButton').option('visible', false);
                    Attendees.datagridUpdate.placePopup.option('title', 'Creating Address');
                    Attendees.datagridUpdate.placePopupDxForm.option('formData').address.id = null;
                  }
                },
              },
            },
            {
              colSpan: 3,
              itemType: 'button',
              horizontalAlignment: 'left',
              name: 'deletePlaceButton',
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Delete Place',
                icon: 'trash',
                hint: 'delete the current place in the popup',
                type: 'danger',
                useSubmitBehavior: false,
                onClick: (clickEvent) => {
                  if (confirm('Are you sure to delete the place? Instead, setting "move out" date is usually enough!')) {
                    $.ajax({
                      url: ajaxUrl,
                      method: 'DELETE',
                      success: (response) => {
                        Attendees.datagridUpdate.placePopup.hide();
                        DevExpress.ui.notify(
                          {
                            message: 'Place deleted successfully',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'info', 2500);
                        placeButton.remove();
                      },
                      error: (response) => {
                        console.log('Failed to delete Place in Popup, error: ', response);
                        DevExpress.ui.notify(
                          {
                            message: 'delete place error',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'error', 5000);
                      },
                    });
                  }
                },
              },
            },
          ],
        }).dxForm('instance');
        e.append(formContainer);
      },
    };
  },

  fetchPlaceFormData: (placeButton) => {
    if (placeButton.value) {
      const allPlaces = Attendees.datagridUpdate.attendeeFormConfigs.formData.places.concat(Attendees.datagridUpdate.attendeeFormConfigs.formData.folkattendee_set.flatMap(folkattendee => folkattendee.folk.places));
      const fetchedPlace = allPlaces.find(x => x.id === placeButton.value);
      if (!Attendees.utilities.editingEnabled && fetchedPlace) {
        Attendees.datagridUpdate.placePopupDxFormData = fetchedPlace;
        Attendees.datagridUpdate.placePopupDxForm.option('formData', fetchedPlace);
        // Attendees.datagridUpdate.addressId = fetchedPlace.address && fetchedPlace.address.id;
      } else {
        $.ajax({
          url: $('form#place-update-popup-form').attr('action') + placeButton.value + '/',
          success: (response) => {
            Attendees.datagridUpdate.placePopupDxFormData = response;
            Attendees.datagridUpdate.placePopupDxForm.option('formData', response);
            Attendees.datagridUpdate.placePopupDxForm.option('onFieldDataChanged', (e) => {
              e.component.validate()
            });
            // Attendees.datagridUpdate.addressId = Attendees.datagridUpdate.placePopupDxFormData.address && Attendees.datagridUpdate.placePopupDxFormData.address.id;
          },
          error: (response) => console.log('Failed to fetch data for Locate Form in Popup, error: ', response),
        });
      }
    }
  },

  addressSource: new DevExpress.data.CustomStore({
    key: 'id',
    load: (loadOptions) => {
      if (!Attendees.utilities.editingEnabled) return [Attendees.datagridUpdate.placePopupDxFormData.address];

      const deferred = $.Deferred();
      const args = {};

      [
        'skip',
        'take',
        'sort',
        'filter',
        'searchExpr',
        'searchOperation',
        'searchValue',
        'group',
      ].forEach((i) => {
        if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
          args[i] = loadOptions[i];
      });

      $.ajax({
        url: $('div.datagrid-attendee-update').data('addresses-endpoint'),
        dataType: 'json',
        data: args,
        success: (result) => {
          deferred.resolve(result.data.concat([Attendees.datagridUpdate.placePopupDxFormData.place]), {
            totalCount: result.totalCount,
            summary: result.summary,
            groupCount: result.groupCount
          });
        },
        error: (response) => {
          console.log('ajax error here is response: ', response);
          deferred.reject('Data Loading Error, probably time out?');
        },
        timeout: 7000,
      });

      return deferred.promise();
    },
    byKey: (key) => {
      if (!Attendees.utilities.editingEnabled && Attendees.datagridUpdate.placePopupDxFormData) {
        return [Attendees.datagridUpdate.placePopupDxFormData.address];
      } else {
        const d = new $.Deferred();
        $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.addressesEndpoint, {id: key})
          .done((result) => {
            d.resolve(result.data);
          });
        return d.promise();
      }
    },
  }),

  stateSource: new DevExpress.data.CustomStore({
    key: 'id',
    load: (loadOptions) => {
//      if (!Attendees.utilities.editingEnabled) return [Attendees.datagridUpdate.placePopupDxFormData.address];

      const deferred = $.Deferred();
      const args = {};

      [
        'skip',
        'take',
        'sort',
        'filter',
        'searchExpr',
        'searchOperation',
        'searchValue',
        'group',
      ].forEach((i) => {
        if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
          args[i] = loadOptions[i];
      });

      $.ajax({
        url: Attendees.datagridUpdate.attendeeAttrs.dataset.statesEndpoint,
        dataType: 'json',
        data: args,
        success: (result) => {
          deferred.resolve(result.data, {
            totalCount: result.totalCount,
            summary: result.summary,
            groupCount: result.groupCount
          });
        },
        error: (response) => {
          console.log('ajax error here is response: ', response);
          deferred.reject('Data Loading Error, probably time out?');
        },
        timeout: 7000,
      });

      return deferred.promise();
    },
    byKey: (key) => {
//      if (!Attendees.utilities.editingEnabled && Attendees.datagridUpdate.placePopupDxFormData){
//        return [Attendees.datagridUpdate.placePopupDxFormData.address];
//      }else{
      const d = new $.Deferred();
      $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.statesEndpoint, {id: key})
        .done((result) => {
          d.resolve(result.data);
        });
      return d.promise();
//      }
    },
  }),


  ///////////////////////  Potential duplicate Attendees Datagrid under new Attendee DxForm  ///////////////////////

  initDuplicatesForNewAttendeeDatagrid: (data, itemElement) => {
    const $myDatagrid = $("<div id='duplicates-new-attendee-datagrid-container'>").dxDataGrid(Attendees.datagridUpdate.duplicatesForNewAttendeeDatagridConfig);
    itemElement.append($myDatagrid);
    Attendees.datagridUpdate.duplicatesForNewAttendeeDatagrid = $myDatagrid.dxDataGrid('instance');
  },

  duplicatesForNewAttendeeDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: () => {
          const firstName = Attendees.datagridUpdate.attendeeMainDxForm.getEditor('first_name').option('value');
          const lastName = Attendees.datagridUpdate.attendeeMainDxForm.getEditor('last_name').option('value');
          const firstName2 = Attendees.datagridUpdate.attendeeMainDxForm.getEditor('first_name2').option('value');
          const lastName2 = Attendees.datagridUpdate.attendeeMainDxForm.getEditor('last_name2').option('value');
          const phone1 = Attendees.datagridUpdate.phone1.option('value');
          const phone2 = Attendees.datagridUpdate.phone2.option('value');
          if (firstName || lastName || firstName2 || lastName2 || phone1 || phone2) {
            const searchData = [firstName, lastName, firstName2, lastName2, phone1, phone2].filter(name => name).map(name => ["infos", "contains", name]).flatMap(e => [e, 'or']);
            const d = new $.Deferred();
            $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeSearch, {include_dead: true, take: 10, filter: JSON.stringify(searchData)})
              .done( result => {
                d.resolve(result.data);
              });
            return d.promise();
          }
        },
      }),
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnChooser: {
      enabled: true,
      mode: 'select',
    },
    rowAlternationEnabled: true,
    hoverStateEnabled: true,
    columns: [
      {
        caption: "Full name",
        dataField: "infos.names",
        allowSorting: false,
        dataType: "string",
        allowHeaderFiltering: false,
        cellTemplate: (container, rowData) => {
          const attrs = {
            "class": "text-info",
            "text": rowData.data.infos.names.original,
            "href": Attendees.datagridUpdate.attendeeUrn + rowData.data.id,
          };
          $($('<a>', attrs)).appendTo(container);
        },
      },
      {
        dataField: 'gender',
        allowSorting: false,
      },
      {
        dataField: 'division',
        allowSorting: false,
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => {
                return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.divisionsEndpoint);
              },
              byKey: (key) => {
                const d = new $.Deferred();
                $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.divisionsEndpoint, {division_id: key})
                  .done( result => {
                    d.resolve(result.data);
                  });
                return d.promise();
              },
            }),
          },
        }
      },
      {
        caption: "Birthday Y-M-D",
        dataField: "birthday",
        dataType: "string",
        allowSorting: false,
        allowHeaderFiltering: false,
        cellTemplate: (container, rowData) => {
          if (rowData.data.actual_birthday || rowData.data.estimated_birthday) {
            const attrs = {
              "text": rowData.data.actual_birthday ? rowData.data.actual_birthday : `around ${rowData.data.estimated_birthday}`,
            };
            $($('<span>', attrs)).appendTo(container);
          }
        },
      },
      {
        dataField: "families",
        cellTemplate: (container, rowData) => {
          if (Array.isArray(rowData.data && rowData.data.folkattendee_set)) {
            const familyAttendees = rowData.data.folkattendee_set.filter(folkAttendee => folkAttendee.folk.category===0);
            const familyNames = familyAttendees.reduce((all, now) => {all.push(now.folk.display_name); return all}, []);
            $($('<span>').html(familyNames.join(', '))).appendTo(container);
          }
        },
      },
    ],
  },

  ///////////////////////  Family Attendees Datagrid in main DxForm  ///////////////////////


  initFamilyAttendeeDatagrid: (data, itemElement) => {
    const familyAttendeeDatagridConfig = Attendees.datagridUpdate.getFolkAttendeeDatagridConfig(0, 'Family');
    const $myDatagrid = $("<div id='family-attendee-datagrid-container'>").dxDataGrid(familyAttendeeDatagridConfig);
    itemElement.append($myDatagrid);
    Attendees.datagridUpdate.familyAttendeeDatagrid = $myDatagrid.dxDataGrid('instance');
  },

  getFolkAttendeeDatagridConfig: (categoryId, displayName) => {
    const originalColumns = [
      {
        dataField: 'folk.id',
        validationRules: [{type: 'required'}],
        caption: displayName,
        groupIndex: 0,
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeFamiliesEndpoint, {categoryId: categoryId}),
              byKey: (key) => $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeFamiliesEndpoint + key + '/'),
            }),
          },
        },
      },
      {
        dataField: 'role',
        validationRules: [{type: 'required'}],
        caption: 'Role',
        lookup: {
          valueExpr: 'id',
          displayExpr: 'title',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchOpts) => {
                const params = {take: 999};
                if (searchOpts.searchValue) {
                  const searchCondition = ['title', searchOpts.searchOperation, searchOpts.searchValue];
                  params.filter = JSON.stringify(searchCondition);
                }
                return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.relationsEndpoint, params);
              },
              byKey: (key) => {
                const d = new $.Deferred();
                $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.relationsEndpoint, {relation_id: key})
                  .done((result) => {
                    d.resolve(result.data);
                  });
                return d.promise();
              },
            }),
          },
        },
      },
      {
        dataField: 'attendee',
        validationRules: [{type: 'required'}],
        // caption: 'Attendee',
        cellTemplate: (container, rowData) => {
          if (rowData.value === Attendees.datagridUpdate.attendeeId) {
            $('<span>', {text: rowData.displayValue}).appendTo(container);
          } else {
            const attrs = {
              class: 'text-info',
              text: rowData.displayValue,
              href: Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeUrn + rowData.value,
            };
            $('<a>', attrs).appendTo(container);
          }
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: (item) => {
            const division_name = Attendees.datagridUpdate.divisionIdNames[item.division] ? ` [${Attendees.datagridUpdate.divisionIdNames[item.division]}]` : '';
            return item ? `(${item.gender[0]}) ${item.infos.names.original}${division_name}${item.deathday ? ', deathday: ' + item.deathday : ''}` : null;
          },
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchOpts) => {
                const params = {take: 30};
                if (searchOpts.searchValue) {
                  const searchCondition = ['infos__names', searchOpts.searchOperation, searchOpts.searchValue];
                  params.filter = JSON.stringify(searchCondition);
                }
                return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.relatedAttendeesEndpoint, params);
              },
              byKey: (key) => {
                const d = new $.Deferred();
                $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.relatedAttendeesEndpoint + key + '/')
                  .done(result => {
                    d.resolve(result.data);
                  });
                return d.promise();
              },
            }),
          },
        },
      },
      {
        dataField: "display_order",
        caption: 'Rank',
        dataType: 'number',
      },
      {
        apiUrlName: 'api_attendee_folkattendee_scheduler_column',
        dataField: 'schedulers',
        caption: 'Scheduler',
        calculateCellValue: (rowData) => {
          const attendeeData = Attendees.datagridUpdate.attendeeFormConfigs && Attendees.datagridUpdate.attendeeFormConfigs.formData;
          if (attendeeData && attendeeData.infos) {
            const schedulers = attendeeData.infos.schedulers;
            return !!(schedulers && schedulers[rowData.attendee]);
          } else {
            return false;
          }
        },
      },
      {
        dataField: "emergency_contacts",
        caption: 'Emergency contact',
        calculateCellValue: (rowData) => {
          const attendeeData = Attendees.datagridUpdate.attendeeFormConfigs && Attendees.datagridUpdate.attendeeFormConfigs.formData;
          if (attendeeData && attendeeData.infos) {
            const emergency_contacts = attendeeData.infos.emergency_contacts;
            return !!(emergency_contacts && emergency_contacts[rowData.attendee]);
          } else {
            return false;
          }
        },
      },
      {
        apiUrlName: 'api_attendee_folkattendee_secret_column',
        caption: 'Secret?',
        dataField: 'infos.show_secret',
        calculateCellValue: (rowData) => {
          if (rowData.infos) {
            const showSecret = rowData.infos.show_secret;
            return !!(showSecret && showSecret[Attendees.utilities.userAttendeeId]);
          } else {
            return false;
          }
        },
      },
      {
        dataField: 'start',
        dataType: 'date',
        editorOptions: {
          dateSerializationFormat: 'yyyy-MM-dd',
        },
      },
      {
        dataField: 'finish',
        dataType: 'date',
        editorOptions: {
          dateSerializationFormat: 'yyyy-MM-dd',
        },
      },
    ];
    return {
      dataSource: {
        store: new DevExpress.data.CustomStore({
          key: 'id',
          load: () => {
            return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.familyAttendeesEndpoint, {categoryId: categoryId});
          },
          byKey: (key) => {
            const d = new $.Deferred();
            $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.familyAttendeesEndpoint, {familyattendee_id: key, categoryId: categoryId})
              .done((result) => {
                d.resolve(result.data);
              });
            return d.promise();
          },
          update: (key, values) => {
            values.category = categoryId;
            return $.ajax({
              url: Attendees.datagridUpdate.attendeeAttrs.dataset.familyAttendeesEndpoint + key + '/',
              method: 'PATCH',
              dataType: 'json',
              contentType: 'application/json; charset=utf-8',
              data: JSON.stringify(values),
              success: (result) => {
                DevExpress.ui.notify(
                  {
                    message: 'update success, please reload page if changing family',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, 'success', 2000);
              },
            });
          },
          insert: function (values) {
            values.category = categoryId;
            return $.ajax({
              url: Attendees.datagridUpdate.attendeeAttrs.dataset.familyAttendeesEndpoint,
              method: 'POST',
              dataType: 'json',
              contentType: 'application/json; charset=utf-8',
              data: JSON.stringify(values),
              success: (result) => {
                DevExpress.ui.notify(
                  {
                    message: 'Create success, please find the new attendee in the table',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, "success", 2000);
              },
            });
          },
          remove: (key) => {
            return $.ajax({
              url: Attendees.datagridUpdate.attendeeAttrs.dataset.familyAttendeesEndpoint + key + '/',
              method: 'DELETE',
              success: (result) => {
                DevExpress.ui.notify(
                  {
                    message: displayName + ' member removed successfully',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, 'info', 2000);
              },
            });
          },
        }),
      },
      onInitNewRow: (e) => {
        DevExpress.ui.notify(
          {
            message: "Let's create a new family member, click away or hit Enter to save. Hit Esc to quit without save",
            position: {
              my: 'center',
              at: 'center',
              of: window,
            },
          }, 'info', 3000);
      },
      allowColumnReordering: true,
      columnAutoWidth: true,
      allowColumnResizing: true,
      columnResizingMode: 'nextColumn',
      rowAlternationEnabled: true,
      hoverStateEnabled: true,
      columnChooser: {
        enabled: true,
        mode: 'select',
      },
      loadPanel: {
        message: 'Fetching...',
        enabled: true,
      },
      wordWrapEnabled: false,
      grouping: {
        autoExpandAll: true,
      },
      editing: {
        mode: 'cell',
        allowUpdating: Attendees.utilities.editingEnabled,
        allowAdding: Attendees.utilities.editingEnabled,
        allowDeleting: false,
      },
      onEditingStart: (info) => {  // forbid editing names or names on top of page will be inconsistent.
        if (info.data.attendee && info.data.attendee === Attendees.datagridUpdate.attendeeId && !['start', 'finish', 'role', 'display_order','infos.show_secret'].includes(info.column.dataField)) {
          info.cancel = true;
        }
      },
      onRowPrepared: (e) => {
        if (e.rowType === 'data' && e.data.attendee && e.data.attendee.id === Attendees.datagridUpdate.attendeeId) {
          e.rowElement.css('color', 'SeaGreen');
          e.rowElement.attr('title', 'Please scroll up and change main attendee data there!');
        }
      },
      onRowInserting: (rowData) => {
        const infos = {show_secret: {}, updating_attendees: {}, comment: null, body: null};
        if (rowData.data.infos && rowData.data.infos.show_secret) {
          infos.show_secret[Attendees.utilities.userAttendeeId] = true;
        }
        rowData.data.infos = infos;
        Attendees.datagridUpdate.alterSchedulersAndEmergencyContacts(rowData.data.attendee, rowData.data, false);
      },
      onRowRemoving: (rowData) => {
        Attendees.datagridUpdate.alterSchedulersAndEmergencyContacts(rowData.data.attendee, Attendees.datagridUpdate.attendeeMainDxForm.option('formData.infos'), true);
      },
      onRowUpdating: (rowData) => { // checking box will arrive one at a time, never multiple fields simultaneously
        if (rowData.newData.infos && 'show_secret' in rowData.newData.infos) { // value could be intentionally false to prevent someone seeing it
          const showSecret = rowData.oldData.infos.show_secret;
          const isItSecretWithCurrentUser = rowData.newData.infos.show_secret;
          if (isItSecretWithCurrentUser) {
            showSecret[Attendees.utilities.userAttendeeId] = true;
          } else {
            delete showSecret[Attendees.utilities.userAttendeeId];
          }
          rowData.newData.infos.show_secret = showSecret;
        } // Todo 20211126 If user save datagrid with showSecret unchecked, don't let it save as false.  Only save false if previously labelled true.
        Attendees.datagridUpdate.alterSchedulersAndEmergencyContacts(rowData.oldData.attendee, rowData.newData, false); // changing fields are only available upon onRowUpdating, not after
      },
      columns: originalColumns.filter(item => {
        return item.apiUrlName ? item.apiUrlName in Attendees.utilities.userApiAllowedUrlNames : true;
      }),
    };
  },

  alterSchedulersAndEmergencyContacts: (attendeeId, newData, deleting) => {
    if (newData && ('schedulers' in newData || 'emergency_contacts' in newData) ) {  // user is changing scheduler or emergency_contact
      const attendeeData = Attendees.datagridUpdate.attendeeFormConfigs && Attendees.datagridUpdate.attendeeFormConfigs.formData;
      const previousInfos = Attendees.datagridUpdate.attendeeMainDxForm.option('formData.infos');
      if (attendeeData && attendeeData.infos) {
        Object.entries(newData).forEach(([key, value]) => {
          if (['schedulers', 'emergency_contacts'].includes(key)) {
            attendeeData.infos[key][attendeeId] = value;
            previousInfos[key][attendeeId] = value;
            if (deleting) {
              if (attendeeId in attendeeData.infos[key]) {
                attendeeData.infos[key][attendeeId] = false
              }
              if (attendeeId in previousInfos[key]) {
                previousInfos[key][attendeeId] = false
              }
            }
          }
        });

        $.ajax({
          url: Attendees.datagridUpdate.attendeeAjaxUrl,
          data: JSON.stringify({infos: attendeeData.infos}),
          dataType: 'json',
          contentType: 'application/json; charset=utf-8',
          method: 'PATCH',
          success: (response) => {
            Attendees.datagridUpdate.attendeeMainDxForm.option('formData.infos', previousInfos);
            Attendees.datagridUpdate.attendeeFormConfigs.formData = attendeeData;
          },
          error: (response) => {
            console.log('Failed to save data for scheduler or emergency contacts, response and infos data: ', response, Attendees.datagridUpdate.attendeeMainDxForm.option('formData').infos);
            // rowData.cancel = true;
            DevExpress.ui.notify(
              {
                message: 'saving scheduler or emergency contacts error, please try again',
                position: {
                  my: 'center',
                  at: 'center',
                  of: window,
                },
              }, 'error', 5000);
          },
        });
      }
    }
  },


  ///////////////////////  Family Attributes Popup and DxForm  ///////////////////////

  initFamilyAttrPopupDxForm: (event) => {
    const familyAttrButton = event.target;
    Attendees.datagridUpdate.familyAttrPopup = $('div.popup-family-attr-update').dxPopup(Attendees.datagridUpdate.familyAttrPopupDxFormConfig(familyAttrButton)).dxPopup('instance');
    Attendees.datagridUpdate.fetchFamilyAttrFormData(familyAttrButton);
  },

  familyAttrPopupDxFormConfig: (familyAttrButton) => {
    const ajaxUrl = $('form#family-attr-update-popup-form').attr('action') + (familyAttrButton.value ? familyAttrButton.value + '/': '');
    return {
      visible: true,
      title: familyAttrButton.value ? 'Viewing Family of ' + familyAttrButton.textContent : 'Creating new Family',
      minwidth: '20%',
      minheight: '30%',
      position: {
        my: 'center',
        at: 'center',
        of: window,
      },
      dragEnabled: true,
      showCloseButton: true,  // for mobile browser
      contentTemplate: (e) => {
        const formContainer = $('<div class="familyAttrForm">');
        Attendees.datagridUpdate.familyAttrPopupDxForm = formContainer.dxForm({
          readOnly: !Attendees.utilities.editingEnabled,
          formData: Attendees.datagridUpdate.familyAttrDefaults,
          colCount: 3,
          scrollingEnabled: true,
          showColonAfterLabel: false,
          requiredMark: '*',
          labelLocation: 'top',
          minColWidth: '20%',
          showValidationSummary: true,
          items: [
            {
              colSpan: 1,
              dataField: "display_name",
              label: {
                text: 'Name',
              },
              helpText: 'what family is this?',
              isRequired: true,
              editorOptions: {
                placeholder: 'Main/parent/past, etc',
              },
            },
            {
              colSpan: 1,
              dataField: 'display_order',
              helpText: '0 is shown before 1,2...',
              isRequired: true,
              editorOptions: {
                placeholder: '0/1/2/3, etc',
              },
              validationRules: [
                {
                  type: 'range',
                  max: 32767,
                  min: 0,
                  message: 'display_order should be between 0 and 32767'
                },
                {
                  type: 'required',
                  message: 'display_order is required'
                },
              ],
            },
            {
              colSpan: 1,
              dataField: 'division',
              editorType: 'dxSelectBox',
              isRequired: true,
              label: {
                text: 'Family major Division',
              },
              editorOptions: {
                valueExpr: 'id',
                displayExpr: 'display_name',
                placeholder: 'Select a value...',
                dataSource: new DevExpress.data.DataSource({
                  store: new DevExpress.data.CustomStore({
                    key: 'id',
                    loadMode: 'raw',
                    load: () => {
                      const d = $.Deferred();
                      $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.divisionsEndpoint).done((response) => {
                        d.resolve(response.data);
                      });
                      return d.promise();
                    },
                  })
                }),
              },
            },
            {
              colSpan: 1,
              visible: Attendees.datagridUpdate.attendeeAttrs.dataset.userOrganizationDirectoryMeet,
              dataField: 'infos.print_directory',
              label: {
                text: 'Print in directory?',
              },
              dataType: 'boolean',
              editorType: 'dxCheckBox',
            },
            {
              colSpan: 1,
              itemType: 'button',
              horizontalAlignment: 'left',
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                text: 'Save Family',
                icon: 'save',
                hint: 'save Family attr data in the popup',
                type: 'default',
                useSubmitBehavior: true,
                onClick: (clickEvent) => {
                  if (Attendees.datagridUpdate.familyAttrPopupDxForm.validate().isValid && confirm('are you sure to submit the popup Family attr Form?')) {
                    const userData = Attendees.datagridUpdate.familyAttrPopupDxForm.option('formData');
                    userData['categoryId'] = Attendees.datagridUpdate.attendeeAttrs.dataset.familyCategoryId;
                    extraHeaders = {};

                    if (userData.infos && userData.infos.print_directory){
                      extraHeaders['X-Print-Directory'] = true;
                    }
                    $.ajax({
                      url: ajaxUrl,
                      headers: extraHeaders,
                      data: JSON.stringify(userData),
                      dataType: 'json',
                      contentType: 'application/json; charset=utf-8',
                      method: userData.id ? 'PUT' : 'POST',
                      success: (savedFamily) => {
                        Attendees.datagridUpdate.familyAttrPopup.hide();
                        DevExpress.ui.notify(
                          {
                            message: 'saving Family attr success',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'success', 2500);

                        if (!userData.id) { Attendees.datagridUpdate.patchNewAttendeeDropDown(savedFamily); }
                        if (familyAttrButton.value) {
                          familyAttrButton.textContent = savedFamily.display_name;
                        } else {
                          Attendees.datagridUpdate.familyButtonFactory({value: savedFamily.id, text: savedFamily.display_name}).insertAfter(familyAttrButton);
                        }
                        Attendees.datagridUpdate.familyAttendeeDatagrid.refresh();
                      },
                      error: (response) => {
                        console.log('Failed to save data for Family attr Form in Popup, error: ', response);
                        console.log('formData: ', userData);
                        DevExpress.ui.notify(
                          {
                            message: 'saving Family error',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'error', 5000);
                      },
                    });
                  }
                },
              },
            },
            {
              colSpan: 1,
              itemType: 'button',
              horizontalAlignment: 'left',
              buttonOptions: {
                elementAttr: {
                  class: 'attendee-form-submits family-delete-button',    // for toggling editing mode
                },
                disabled: !Attendees.utilities.editingEnabled,
                hide: !familyAttrButton.value,
                text: 'Delete Family, Places, Relationships',
                icon: 'trash',
                hint: 'delete the Family with their places & marital relationships.',
                type: 'danger',
                useSubmitBehavior: false,
                onClick: (clickEvent) => {
                  if (confirm('Are you sure to delete the family and all its places and marital relationships in the popup?  Instead, editing the "finish" date or members is usually enough!')) {
                    $.ajax({
                      url: `${$('form#family-attr-update-popup-form').attr('action')}${Attendees.datagridUpdate.familyAttrPopupDxFormData.id}/`,
                      method: 'DELETE',
                      success: (response) => {
                        Attendees.datagridUpdate.familyAttrPopup.hide();
                        DevExpress.ui.notify(
                          {
                            message: 'Family deleted successfully',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'info', 2500);

                        Attendees.datagridUpdate.familyAttendeeDatagrid.refresh();
                        Attendees.datagridUpdate.relationshipDatagrid.refresh();
                        $('li.' + familyAttrButton.value).remove();
                        familyAttrButton.remove();
                      },
                      error: (response) => {
                        console.log('Failed to delete Family in Popup, error: ', response);
                        DevExpress.ui.notify(
                          {
                            message: 'delete Family error',
                            position: {
                              my: 'center',
                              at: 'center',
                              of: window,
                            },
                          }, 'error', 5000);
                      },
                    });
                  }
                },
              },
            },
            {
              colSpan: 1,
              name: 'familyMemberCount',
              helpText: 'Close the popup to see family members in the table',
              label: {
                text: 'family member count',
              },
              template: (data, itemElement) => {
                $('<p>', {class: 'family-member-count', text: 0}).appendTo(itemElement);
              },
            },
          ],
        }).dxForm('instance');
        e.append(formContainer);
      }
    };
  },

  fetchFamilyAttrFormData: (familyAttrButton) => {
    if (familyAttrButton.value) {
      const fetchedFamily = Attendees.datagridUpdate.families && Attendees.datagridUpdate.families.find(x => x.id === familyAttrButton.value);
      if (!Attendees.utilities.editingEnabled && fetchedFamily) {
        $('p.family-member-count')[0].textContent = fetchedFamily.attendees.length;
        if (fetchedFamily.attendees.length > 1) {$('div.family-delete-button span.dx-button-text').text('Remove attendee from Family')}  // FolkService.destroy_with_associations will preserve Family if other families exists
        Attendees.datagridUpdate.familyAttrPopupDxFormData = fetchedFamily;
        Attendees.datagridUpdate.familyAttrPopupDxForm.option('formData', fetchedFamily);
      } else {
        $.ajax({
          url: $('form#family-attr-update-popup-form').attr('action') + familyAttrButton.value + '/',
          success: (response) => {
            $('p.family-member-count')[0].textContent = response.attendees.length;
            if (response.attendees.length > 1) {$('div.family-delete-button span.dx-button-text').text('Remove attendee from Family')}  // FolkService.destroy_with_associations will preserve Family if other families exists
            Attendees.datagridUpdate.familyAttrPopupDxFormData = response;
            Attendees.datagridUpdate.familyAttrPopupDxForm.option('formData', response);
          },
          error: (response) => console.log('Failed to fetch data for Family Attr Form in Popup, error: ', response),
        });
      }
    } else {
      $('div.family-delete-button').remove();  // new family not saved yet.
    }
  },


  ///////////////////////  Relationship Datagrid in main DxForm  ///////////////////////


  initRelationshipDatagrid: (data, itemElement) => {
    const relationshipDatagridConfig = Attendees.datagridUpdate.getFolkAttendeeDatagridConfig(25, 'Circle');
    const $relationshipDatagrid = $("<div id='relationship-datagrid-container'>").dxDataGrid(relationshipDatagridConfig);
    itemElement.append($relationshipDatagrid);
    Attendees.datagridUpdate.relationshipDatagrid = $relationshipDatagrid.dxDataGrid('instance');
  },


  ///////////////////////  Past Datagrids (dynamic) in main DxForm  ///////////////////////

  initPastDatagrid: (data, itemElement, args) => {
    const $pastDatagrid = $("<div id='" + args.type + "-past-datagrid-container'>").dxDataGrid(Attendees.datagridUpdate.pastDatagridConfig(args));
    itemElement.append($pastDatagrid);
    return $pastDatagrid.dxDataGrid("instance");
  },

  pastDatagridConfig: (args) => { // {type: 'education', dataFields: {display_name: 'display_name', start: 'start'}, extraDatagridOpts:{editing:{mode:'popup'}}}
    const columns = [
      {
        dataField: 'category',
        validationRules: [{type: 'required'}],
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => {
                return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.categoriesEndpoint, {
                  take: 100,
                  type: args.type,
                });
              },
              byKey: (key) => {
                const d = new $.Deferred();
                $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.categoriesEndpoint + key + '/')
                  .done((result) => {
                    d.resolve(result);
                  });
                return d.promise();
              },
            }),
          },
        },
      },
      {
        dataField: 'display_name',
      },
      {
        caption: 'Secret shared with you',
        dataField: 'infos.show_secret',
        width: '18%',
        calculateCellValue: (rowData) => {
          if (rowData.infos) {
            const showSecret = rowData.infos.show_secret;
            return !!(showSecret && showSecret[Attendees.utilities.userAttendeeId]);
          } else {
            return false;
          }
        },
        dataType: 'boolean',
      },
      {
        dataField: 'infos.comment',
        caption: 'Comment',
        dataType: 'string',
        width: '32%',
      },
      {
        dataField: 'when',
        dataType: 'date',
      },
      {
        dataField: 'finish',
        dataType: 'date',
      },
    ];

    return {
      dataSource: {
        store: new DevExpress.data.CustomStore({
          key: 'id',
          load: () => {
            return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.pastsEndpoint, {category__type: args.type});
          },
          byKey: (key) => {
            const d = new $.Deferred();
            $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.pastsEndpoint + key + '/')
              .done((result) => {
                d.resolve(result.data);
              });
            return d.promise();
          },
          update: (key, values) => {
            return $.ajax({
              url: Attendees.datagridUpdate.attendeeAttrs.dataset.pastsEndpoint + key + '/?' + $.param({category__type: args.type}),
              method: 'PATCH',
              dataType: 'json',
              contentType: 'application/json; charset=utf-8',
              data: JSON.stringify(values),
              success: (result) => {
                DevExpress.ui.notify(
                  {
                    message: 'update ' + args.type + ' success',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, 'success', 2000);
              },
            });
          },
          insert: function (values) {
            const subject = {
              content_type: Attendees.datagridUpdate.attendeeAttrs.dataset.attendeeContenttypeId,
              object_id: Attendees.datagridUpdate.attendeeId,
            };
            return $.ajax({
              url: Attendees.datagridUpdate.attendeeAttrs.dataset.pastsEndpoint,
              method: 'POST',
              dataType: 'json',
              contentType: 'application/json; charset=utf-8',
              data: JSON.stringify({...values, ...subject}),
              success: (result) => {
                DevExpress.ui.notify(
                  {
                    message: 'Create ' + args.type + ' success',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, 'success', 2000);
                if (args.type === 'status') {
                  Attendees.datagridUpdate.attendingMeetDatagrid.refresh();
                }
              },
            });
          },
          remove: (key) => {
            return $.ajax({
              url: Attendees.datagridUpdate.attendeeAttrs.dataset.pastsEndpoint + key + '/?' + $.param({category__type: args.type}),
              method: 'DELETE',
              success: (result) => {
                DevExpress.ui.notify(
                  {
                    message: 'removed '+ args.type +' success',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, 'info', 2000);
              },
            });
          },
        }),
      },
      onRowInserting: (rowData) => {
        const infos = {show_secret: {}, comment: rowData.data.infos && rowData.data.infos.comment};
        if (rowData.data.infos && rowData.data.infos.show_secret) {
          infos.show_secret[Attendees.utilities.userAttendeeId] = true;
        }
        rowData.data.infos = infos;
      },
      onInitNewRow: (e) => {  // don't assign e.data or show_secret somehow messed up
        DevExpress.ui.notify(
          {
            message: "Let's create a " + args.type + ", click away or hit Enter to save. Hit Esc to quit without save",
            position: {
              my: 'center',
              at: 'center',
              of: window,
            },
          }, 'info', 3000);
      },
      allowColumnReordering: true,
      columnAutoWidth: true,
      allowColumnResizing: true,
      columnResizingMode: 'nextColumn',
      rowAlternationEnabled: true,
      hoverStateEnabled: true,
      columnChooser: {
        enabled: true,
        mode: 'select',
      },
      loadPanel: {
        message: 'Fetching...',
        enabled: true,
      },
      wordWrapEnabled: false,
      width: '100%',
      grouping: {
        autoExpandAll: true,
      },
      onRowUpdating: (rowData) => {
        if (rowData.newData.infos) { // could be comment or show_secret or both
          const updatingInfos = rowData.oldData.infos || {};
          if ('show_secret' in rowData.newData.infos) {  // infos.show_secret could be false or true
            let updatingShowSecret = typeof (updatingInfos.show_secret) === 'object' && updatingInfos.show_secret || {};  // could show_secret to others
            if (rowData.newData.infos.show_secret) {  // boolean from UI but db needs to store attendee
              updatingShowSecret[Attendees.utilities.userAttendeeId] = true;
            } else {
              delete updatingShowSecret[Attendees.utilities.userAttendeeId];
            }
            updatingInfos.show_secret = updatingShowSecret;
          }
          if ('comment' in rowData.newData.infos) {  // UI may send this or not
            updatingInfos.comment = rowData.newData.infos.comment;
          }
          rowData.newData.infos = updatingInfos;
        }
      },
      columns: columns.flatMap(column => {
        if (column.dataField in args.dataFieldAndOpts) {
          return [{...column, ...args.dataFieldAndOpts[column.dataField]}];
        } else {
          return [];
        }
      }),
    };
  },

  noteEditingArgs: {
    mode: 'popup',
    popup: {
      showTitle: true,
      showCloseButton: true,  // for mobile browser
      title: 'Editing note of Attendee'
    },
    form: {
      items: [
        {
          dataField: 'category',
        },
        {
          dataField: 'display_name',
        },
        {
          dataField: 'infos.show_secret',
        },
        {
          dataField: 'when',
        },
        {
          dataField: 'infos.comment',
          editorType: 'dxTextArea',
          colSpan: 2,
          editorOptions: {
            autoResizeEnabled: true,
          }
        },
      ],
    },
  },


  ///////////////////////  AttendingMeet Datagrid in main DxForm  ///////////////////////

  initAttendingMeetsDatagrid: (data, itemElement) => {
    const $attendingMeetDatagrid = $("<div id='attendingmeet-datagrid-container'>").dxDataGrid(Attendees.datagridUpdate.attendingMeetDatagridConfig);
    itemElement.append($attendingMeetDatagrid);
    Attendees.datagridUpdate.attendingMeetDatagrid = $attendingMeetDatagrid.dxDataGrid('instance');
  },

  attendingMeetDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: () => {
          return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.attendingmeetsEndpoint);
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.attendingmeetsEndpoint + key + '/')
            .done((result) => {
              d.resolve(result.data);
            });
          return d.promise();
        },
        update: (key, values) => {
          return $.ajax({
            url: Attendees.datagridUpdate.attendeeAttrs.dataset.attendingmeetsEndpoint + key + '/',
            method: 'PATCH',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'update attendingmeet success',
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  }
                }, 'success', 2000);
            },
          });
        },
        insert: (values) => {
          return $.ajax({
            url: Attendees.datagridUpdate.attendeeAttrs.dataset.attendingmeetsEndpoint,
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'Create success, please find the new activity in the table',
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  },
                }, 'success', 2000);
              Attendees.datagridUpdate.statusDatagrid.refresh();
            },
          });
        },
        remove: (key) => {
          return $.ajax({
            url: Attendees.datagridUpdate.attendeeAttrs.dataset.attendingmeetsEndpoint + key + '/',
            method: 'DELETE',
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'removed AttendingMeet success',
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  },
                }, 'info', 2000);
            },
          });
        },
      }),
    },
    onRowInserted: (e) => {
      Attendees.datagridUpdate.attendingMeetDatagrid.refresh();
    },
    onInitNewRow: (e) => {
      for (const [key, value] of Object.entries(Attendees.datagridUpdate.attendingmeetDefaults)) {
        e.data[key] = value;
      }
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    rowAlternationEnabled: true,
    hoverStateEnabled: true,
    columnChooser: {
      enabled: true,
      mode: 'select',
    },
    loadPanel: {
      message: 'Fetching...',
      enabled: true,
    },
    wordWrapEnabled: true,
    grouping: {
      autoExpandAll: true,
    },
    columns: [
      {
        dataField: 'attending',
        validationRules: [{type: 'required'}],
        visible: false,
        lookup: {
          valueExpr: 'id',
          displayExpr: 'attending_label',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (e) => {
                return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.attendingsEndpoint);
              },
              byKey: (key) => {
                if (key) {
                  const d = $.Deferred();
                  $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.attendingsEndpoint + key + '/').done((response) => {
                    d.resolve(response);
                  });
                  return d.promise();
                }
              },
            }),
          },
        },
      },
      {
        dataField: 'meet__assembly',
        groupIndex: 0,
        validationRules: [{type: 'required'}],
        caption: 'Group (Assembly)',
        setCellValue: (newData, value, currentData) => {
          newData.assembly = value;
          newData.meet = null;
          newData.character = null;
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.assembliesEndpoint),
              byKey: (key) => {
                if (key) {
                  const d = $.Deferred();
                  $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.assembliesEndpoint + key + '/').done((response) => {
                    d.resolve(response);
                  });
                  return d.promise();
                }
              },
            }),
          },
        },
      },
      {
        dataField: 'meet',
        caption: 'Activity (Meet)',
        validationRules: [{type: 'required'}],
        setCellValue: (newData, value, currentData) => {
          newData.meet = value;
          const majorCharacter = Attendees.datagridUpdate.meetCharacters[value];
          if (majorCharacter && currentData.character === null) {newData.character = majorCharacter;}
        },  // setting majorCharacter of the corresponding meet
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              filter: options.data ? {'assemblies[]': options.data.assembly} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  const d = new $.Deferred();
                  $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.meetsEndpoint, searchOpts.filter)
                    .done((result) => {
                      if (result.data && Attendees.datagridUpdate.meetCharacters === null) {
                        Attendees.datagridUpdate.meetCharacters = result.data.reduce((all, now)=> {all[now.id] = now.major_character; return all}, {});
                      }  // cache the every meet's major characters for later use
                      d.resolve(result);
                    });
                  return d.promise();
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.meetsEndpoint + key + '/')
                    .done((result) => {
                      d.resolve(result);
                    });
                  return d.promise();
                },
              }),
            };
          },
        },
      },
      {
        dataField: 'character',
        validationRules: [{type: 'required'}],
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              filter: options.data ? {'assemblies[]': options.data.assembly} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.charactersEndpoint, searchOpts.filter);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.charactersEndpoint + key + '/')
                    .done((result) => {
                      d.resolve(result);
                    });
                  return d.promise();
                },
              }),
            };
          }
        },
      },
      {
        dataField: 'category',
        validationRules: [{type: 'required'}],
        editorOptions: {
          showClearButton: true,
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts.type = 'attendance';
                  return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.categoriesEndpoint, searchOpts);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.categoriesEndpoint + key + '/')
                    .done((result) => {
                      d.resolve(result);
                    });
                  return d.promise();
                },
              }),
            };
          }
        },
      },
      {
        dataField: 'start',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'team',
        visible: false,
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              filter: options.data ? {'meets[]': [options.data.meet]} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  return $.getJSON(Attendees.datagridUpdate.attendeeAttrs.dataset.teamsEndpoint, searchOpts.filter);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get(Attendees.datagridUpdate.attendeeAttrs.dataset.teamsEndpoint + key + '/')
                    .done((result) => {
                      d.resolve(result);
                    });
                  return d.promise();
                },
              }),
            };
          }
        },
      },
      {
        dataField: 'finish',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'infos.note',
        visible: false,
        caption: 'Note',
        dataType: 'string',
      },
    ],
  },

  attendingMeetEditingArgs: {
    mode: 'popup',
    popup: {
      showTitle: true,
      title: 'Editing Attendee activities'
    },
    texts: {
      confirmDeleteMessage: "Warning! Please don't delete unless it's purely typo/entry error.  For real process such as terminating activities, please set the 'finish date' to expire it instead. Otherwise mass assignments will revert the deletion.",
    },
    form: {
      items: [
        {
          colSpan: 2,
          dataField: 'attending',
        },
        {
          dataField: 'assembly',
        },
        {
          dataField: 'meet',
        },
        {
          dataField: 'character',
          editorOptions: {
            showClearButton: true,
          }
        },
        {
          dataField: 'team',
        },
        {
          dataField: 'category',
        },
        {
          dataField: 'start',
        },
        {
          dataField: 'finish',
        },
        {
          dataField: 'infos.note',
          helpText: 'special memo',
          editorOptions: {
            autoResizeEnabled: true,
          },
        },
      ],
    },
  },
};

$(document).ready(() => {
  Attendees.datagridUpdate.init();
});
