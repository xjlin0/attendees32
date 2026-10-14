// The merge screen: two records of one person become one, decided before
// anything changes. Used by the attendee page (Merge with another record,
// Undo merge) and the Attending Meet list (Merge 2 selected). The server does
// the merge and takes no choices; the older record keeps its id, its details
// stay, the newer record's fill its blanks, contacts of every kind are kept.
// What the coworker picks here is an ordinary edit of the merged record after.
Attendees.merge = {
  endpoint: '/persons/api/datagrid_data_attendee/',
  divisionsEndpoint: '/whereabouts/api/user_divisions/',
  pageUrn: '/persons/attendee/',
  divisions: {},  // {id: display_name}, fetched once
  labels: {
    first_name: 'First name',
    last_name: 'Last name',
    first_name2: 'First name 2',
    last_name2: 'Last name 2',
    gender: 'Gender',
    actual_birthday: 'Birthday',
    estimated_birthday: 'Estimated birthday',
    deathday: 'Death date',
    division: 'Division',
    photo: 'Photo',
  },

  csrf: () => document.querySelector('input[name="csrfmiddlewaretoken"]').value,

  notify: (message, type) => {
    DevExpress.ui.notify({message: message, position: {my: 'center', at: 'center', of: window}}, type, type === 'error' ? 5000 : 2500);
  },

  reason: (xhr, fallback) => {
    const body = xhr && xhr.responseJSON;
    return (body && (body.detail || body.primary)) || fallback;
  },

  popup: (options) => {
    const $element = $('<div>').appendTo('body');
    return $element.dxPopup({
      showCloseButton: true,
      height: 'auto',
      maxHeight: '90vh',
      onHidden: (e) => { e.component.dispose(); $element.remove(); },
      ...options,
    }).dxPopup('instance');
  },

  escape: (value) => $('<span>').text(value === null || value === undefined ? '' : String(value)).html(),

  ///////////////////////  The picker: which record is the same person?  ///////////////////////

  // From the attendee page. ``record`` is the page's attendee; ``afterwards``
  // is called with the merged record's id once the merge is done.
  pick: (record, afterwards) => {
    const name = record.infos.names.original;
    const $items = $('<div>');
    let latest = 0;  // searches answer out of order; only the newest one is shown
    const search = (term) => {
      const request = ++latest;
      if (!term) { $items.empty(); return; }
      // The organization's live records whose names or contacts contain the words.
      $.get(Attendees.merge.endpoint, {searchValue: term, take: 10}).done((result) => {
        if (request !== latest) { return; }
        const others = result.data.filter((row) => row.id !== record.id);
        $items.empty();
        if (others.length === 0) { $items.append('<div class="text-secondary">No other record matches.</div>'); return; }
        $('<div>').appendTo($items).dxList({
          dataSource: others,
          height: 'auto',
          itemTemplate: (row) => $('<div>').html(Attendees.merge.matchLine(row)),
          onItemClick: (e) => {
            picker.hide();
            Attendees.merge.confirm(record.id, e.itemData.id, afterwards);
          },
        });
      });
    };
    const picker = Attendees.merge.popup({
      title: `Which record is the same person as ${name}?`,
      width: 640,
      contentTemplate: (container) => {
        $('<div>').appendTo(container).dxTextBox({
          value: record.first_name || record.last_name || '',
          placeholder: 'Type a name',
          mode: 'search',
          stylingMode: 'outlined',
          valueChangeEvent: 'input',
          onValueChanged: (e) => search(e.value.trim()),
          onInitialized: (e) => search(e.component.option('value').trim()),
        });
        $('<div class="text-secondary small mt-2 mb-1">Pick the other record. You choose what the merged record keeps on the next screen.</div>').appendTo(container);
        $items.appendTo(container);
      },
    });
    picker.show();
  },

  // One line per match: name, birthday, family, phone.
  matchLine: (row) => {
    const esc = Attendees.merge.escape;
    const families = (row.folkattendee_set || []).filter((membership) => membership.folk && membership.folk.category === 0).map((membership) => membership.folk.display_name);
    const name = (row.infos.names || {}).original || `${row.first_name || ''} ${row.last_name || ''}`.trim();
    const parts = [
      `<b>${esc(name)}</b>`,
      row.actual_birthday ? esc(row.actual_birthday) : '',
      families.length ? esc(families.join(', ')) : '',
      row.infos.contacts && row.infos.contacts.phone1 ? esc(row.infos.contacts.phone1) : '',
      row.is_removed ? '<span class="text-secondary">deleted</span>' : '',
    ].filter((part) => part);
    return parts.join(' &middot; ');
  },

  ///////////////////////  The merge screen  ///////////////////////

  // Shows what merging the two records would do, lets the coworker pick where
  // they differ, then merges and applies the picks. ``afterwards`` gets the
  // merged record's id.
  confirm: (oneId, otherId, afterwards) => {
    $.when(
      $.get(`${Attendees.merge.endpoint}merge_preview/`, {a: oneId, b: otherId}),
      Attendees.merge.loadDivisions(),
    ).done((previewResponse) => {
      Attendees.merge.show(previewResponse[0], afterwards);
    }).fail((xhr) => {
      Attendees.merge.notify(Attendees.merge.reason(xhr, 'Could not read the two records.'), 'error');
    });
  },

  loadDivisions: () => {
    if (Object.keys(Attendees.merge.divisions).length) { return $.Deferred().resolve().promise(); }
    return $.get(Attendees.merge.divisionsEndpoint).done((result) => {
      (result.data || result).forEach((division) => { Attendees.merge.divisions[division.id] = division.display_name; });
    });
  },

  label: (name) => {
    if (name.startsWith('fixed.')) {
      const key = name.slice('fixed.'.length).replace(/_/g, ' ');
      return key.charAt(0).toUpperCase() + key.slice(1);
    }
    return Attendees.merge.labels[name] || name;
  },

  // How a value reads on the screen.
  shown: (name, value) => {
    if (value === null || value === undefined || value === '') { return '<span class="text-secondary">blank</span>'; }
    if (name === 'division') { return Attendees.merge.escape(Attendees.merge.divisions[value] || value); }
    if (name === 'photo') { return 'a photo'; }
    if (name === 'fixed.grade') {
      const converter = document.getElementById('organization-grade-converter');
      const grades = converter ? JSON.parse(converter.textContent) : [];
      return Attendees.merge.escape(grades[value] !== undefined ? grades[value] : value);
    }
    return Attendees.merge.escape(value);
  },

  show: (preview, afterwards) => {
    const esc = Attendees.merge.escape;
    const older = 'older record', newer = 'newer record';
    const from = (who) => `<span class="text-secondary small">${who === 'primary' ? older : newer}</span>`;
    const row = (field, body) => `<tr><th class="text-secondary fw-normal pe-3 align-top" style="white-space:nowrap;width:11em">${field}</th><td>${body}</td></tr>`;
    const head = (text) => `<tr><td colspan="2" class="pt-3 pb-1 fw-semibold" style="border-bottom:2px solid #dee2e6">${text}</td></tr>`;
    const radio = (name, who, value, checked) =>
      `<label class="form-check form-check-inline me-3 mb-0" style="cursor:pointer"><input class="form-check-input" type="radio" name="${esc(name)}" value="${who}"${checked ? ' checked' : ''}> <span class="form-check-label">${Attendees.merge.shown(name, value)}</span> ${from(who)}</label>`;

    const choose = [], one = [], same = [], photos = [];
    Object.entries(preview.details).forEach(([name, values]) => {
      const label = Attendees.merge.label(name);
      const has = (value) => value !== null && value !== undefined && value !== '';
      if (has(values.primary) && has(values.duplicate) && String(values.primary) !== String(values.duplicate)) {
        if (name === 'photo') { photos.push(row(label, `the older record's stays; the other can be uploaded afterwards`)); return; }
        choose.push(row(label, radio(name, 'primary', values.primary, true) + radio(name, 'duplicate', values.duplicate, false)));
      } else if (has(values.primary) && has(values.duplicate)) {
        same.push(row(label, Attendees.merge.shown(name, values.primary)));
      } else {
        const who = has(values.primary) ? 'primary' : 'duplicate';
        one.push(row(label, `${Attendees.merge.shown(name, values[who])} ${from(who)}`));
      }
    });

    // Contacts: every value from both records, in the slot it will get.
    const byKind = {};
    Object.entries(preview.contacts).forEach(([key, entry]) => {
      const kind = key.replace(/[0-9]+$/, '');
      (byKind[kind] = byKind[kind] || []).push(`<div class="mb-1">${esc(entry.value)} <span class="text-secondary small">${esc(key)}${key === 'phone1' || key === 'email1' ? ', in directory' : ''} &middot; ${entry.from === 'primary' ? older : newer}</span></div>`);
    });
    const contacts = Object.entries(byKind).map(([kind, lines]) => row(esc(kind.charAt(0).toUpperCase() + kind.slice(1) + 's'), lines.join(''))).join('');

    const counts = preview.moves;
    const count = (number, one, many) => `${number} ${number === 1 ? one : many}`;
    const moves = [
      row('Groups', count(counts.enrollments, 'enrollment', 'enrollments')),
      row('Attendance', count(counts.attendances, 'check-in', 'check-ins')),
      row('Family and relationships', count(counts.memberships, 'membership', 'memberships')),
      row('Addresses', count(counts.addresses, 'address', 'addresses')),
      row('Notes', count(counts.notes, 'note', 'notes')),
      row('Statuses', count(counts.statuses, 'status', 'statuses')),
      row('Registrations', count(counts.registrations, 'registration', 'registrations')),
    ].concat(photos).join('');

    const section = (title, rows, empty) => head(title) + (rows.length ? rows.join('') : `<tr><td colspan="2" class="text-secondary small">${empty}</td></tr>`);
    const html =
      `<div style="font-size:14px;max-height:calc(100vh - 220px);overflow-y:auto">` +
      `<p class="mb-2"><b>${esc(preview.primary.name)}</b> (older record) and <b>${esc(preview.duplicate.name)}</b> (newer record) become one record. This is what it will keep.</p>` +
      `<table class="table table-sm mb-2"><tbody>` +
      section('Different on the two records — choose one', choose, 'Nothing differs.') +
      section('Contacts from both — kept', contacts ? [contacts] : [], 'No contacts on either.') +
      `<tr><td colspan="2" class="text-secondary small pb-2">A stale number or address is removed on the merged record afterwards, like any other edit.</td></tr>` +
      section('Only on one record — kept', one, 'Nothing.') +
      section('Same on both', same, 'Nothing.') +
      head('Moves over from the newer record as it is') + moves +
      `</tbody></table>` +
      `<p class="mb-0 text-secondary">Merge makes one record, then applies what you picked above. The merged record keeps the older record's link; the other link opens it too. You can undo this once.</p>` +
      `</div>`;

    const screen = Attendees.merge.popup({
      title: 'Merge into one record',
      width: 820,
      contentTemplate: (container) => container.append(html),
      toolbarItems: [
        {
          toolbar: 'bottom', location: 'after', widget: 'dxButton',
          options: {
            text: 'Merge', type: 'default', stylingMode: 'contained', icon: 'group',
            onClick: (e) => {
              e.component.option('disabled', true);
              const picks = {};
              screen.content().find('input[type=radio]:checked').each((index, input) => {
                if (input.value === 'duplicate') { picks[input.name] = preview.details[input.name].duplicate; }
              });
              Attendees.merge.merge(preview, picks).done(() => {
                screen.hide();
                afterwards(preview.primary.id);
              }).fail((xhr) => {
                e.component.option('disabled', false);
                Attendees.merge.notify(Attendees.merge.reason(xhr, 'The merge did not go through.'), 'error');
              });
            },
          },
        },
        {toolbar: 'bottom', location: 'after', widget: 'dxButton', options: {text: 'Cancel', stylingMode: 'outlined', onClick: () => screen.hide()}},
      ],
    });
    screen.show();
  },

  // Merges, then writes the picks on the merged record as an ordinary edit.
  merge: (preview, picks) => {
    return $.ajax({
      url: `${Attendees.merge.endpoint}${preview.duplicate.id}/merge/`,
      method: 'POST',
      contentType: 'application/json',
      headers: {'X-CSRFToken': Attendees.merge.csrf()},
      data: JSON.stringify({primary: preview.primary.id}),
    }).then(() => Attendees.merge.applyPicks(preview.primary.id, picks));
  },

  applyPicks: (primaryId, picks) => {
    if (Object.keys(picks).length === 0) { return $.Deferred().resolve().promise(); }
    const url = `${Attendees.merge.endpoint}${primaryId}/`;
    // Built on a fresh read, since the merge just changed the record.
    return $.get(url).then((record) => {
      const body = {};
      Object.entries(picks).forEach(([name, value]) => {
        if (name.startsWith('fixed.')) {
          record.infos.fixed = record.infos.fixed || {};
          record.infos.fixed[name.slice('fixed.'.length)] = value;
          body.infos = record.infos;
        } else {
          body[name] = value;
        }
      });
      return $.ajax({
        url: url,
        method: 'PATCH',
        contentType: 'application/json',
        headers: {'X-CSRFToken': Attendees.merge.csrf(), 'X-Target-Attendee-Id': primaryId},
        data: JSON.stringify(body),
      });
    });
  },

  ///////////////////////  Undo  ///////////////////////

  undo: (duplicateId, afterwards) => {
    const screen = Attendees.merge.popup({
      title: 'Undo this merge?',
      width: 560,
      contentTemplate: (container) => container.append(
        '<div style="font-size:14px"><p class="mb-1">Both records come back as they were before the merge.</p>' +
        '<p class="mb-1">Groups, attendance and family added since stay on this record. Details edited since go back to what they were.</p>' +
        '<p class="mb-0">This can be done once.</p></div>'),
      toolbarItems: [
        {
          toolbar: 'bottom', location: 'after', widget: 'dxButton',
          options: {
            text: 'Undo merge', type: 'default', stylingMode: 'contained', icon: 'undo',
            onClick: (e) => {
              e.component.option('disabled', true);
              $.ajax({
                url: `${Attendees.merge.endpoint}${duplicateId}/unmerge/`,
                method: 'POST',
                headers: {'X-CSRFToken': Attendees.merge.csrf()},
              }).done(() => { screen.hide(); afterwards(); }).fail((xhr) => {
                e.component.option('disabled', false);
                Attendees.merge.notify(Attendees.merge.reason(xhr, 'The merge could not be undone.'), 'error');
              });
            },
          },
        },
        {toolbar: 'bottom', location: 'after', widget: 'dxButton', options: {text: 'Cancel', stylingMode: 'outlined', onClick: () => screen.hide()}},
      ],
    });
    screen.show();
  },
};
