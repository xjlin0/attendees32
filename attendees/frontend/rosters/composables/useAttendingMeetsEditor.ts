import { Ref } from 'vue';
import { Endpoints, FilterState, AttendeeRow } from '../types';
import { meetsMap, meetsInfoMap, charactersMap } from './useLookups';
import dxPopup from 'devextreme/ui/popup';
import dxForm from 'devextreme/ui/form';
import dxTabPanel from 'devextreme/ui/tab_panel';
import notify from 'devextreme/ui/notify';

const WARNING_NOTIFY_TIME = 5000;

export function useAttendingMeetsEditor(
  endpoints: Endpoints,
  gridInstanceRef: Ref<any>,
  filterData: FilterState,
  reloadCallback?: (targetAttendeeId?: number | string) => Promise<any> | void
) {
  let popupInstance: any = null;
  let popupElement: HTMLElement | null = null;
  let currentAttendeeData: any = null;
  let currentRawMeets: any[] = [];
  let currentSortedMeets: any[] = [];
  let currentFormInstances: any[] = [];
  let currentActiveIndex = 0;
  let currentSelectedMeetId: any = null;

  const lookupsCache = {
    loaded: false,
    loadingPromise: null as Promise<void> | null,
    meets: [] as any[],
    characters: [] as any[],
    categories: [] as any[],
    teams: [] as any[],
    meetNames: {} as Record<string | number, string>,
    attendings: new Map<string | number, any>()
  };

  const preloadLookups = async () => {
    if (lookupsCache.loaded) return;
    if (lookupsCache.loadingPromise) return lookupsCache.loadingPromise;

    lookupsCache.loadingPromise = (async () => {
      try {
        const [meetsRes, charsRes, catsRes, teamsRes] = await Promise.all([
          fetch(`${endpoints.meets}?take=9999&model=attendingmeet`).then(r => r.json()).catch(() => ({})),
          fetch(`${endpoints.characters}?take=9999`).then(r => r.json()).catch(() => ({})),
          fetch(`${endpoints.categories}?type=attendance&take=9999`).then(r => r.json()).catch(() => ({})),
          fetch(`${endpoints.teams}?take=9999`).then(r => r.json()).catch(() => ({}))
        ]);

        const rawMeets = meetsRes.data || meetsRes.results || (Array.isArray(meetsRes) ? meetsRes : []);
        lookupsCache.meets = Array.isArray(rawMeets) ? rawMeets : [];
        const rawChars = charsRes.data || charsRes.results || (Array.isArray(charsRes) ? charsRes : []);
        lookupsCache.characters = Array.isArray(rawChars) ? rawChars : [];
        lookupsCache.characters.forEach((c: any) => {
          if (c.id !== undefined && c.id !== null) {
            charactersMap.set(c.id, c);
            charactersMap.set(String(c.id), c);
          }
        });
        const rawCats = catsRes.data || catsRes.results || (Array.isArray(catsRes) ? catsRes : []);
        lookupsCache.categories = Array.isArray(rawCats) ? rawCats : [];
        const rawTeams = teamsRes.data || teamsRes.results || (Array.isArray(teamsRes) ? teamsRes : []);
        lookupsCache.teams = Array.isArray(rawTeams) ? rawTeams : [];

        lookupsCache.meets.forEach((m: any) => {
          if (m.id !== undefined && m.id !== null) {
            if (m.display_name) {
              lookupsCache.meetNames[m.id] = m.display_name;
              meetsInfoMap.set(m.id, m.display_name);
              meetsInfoMap.set(String(m.id), m.display_name);
            }
            meetsMap.set(m.id, m);
            meetsMap.set(String(m.id), m);
            if (m.slug) {
              if (m.display_name) meetsInfoMap.set(m.slug, m.display_name);
              meetsMap.set(m.slug, m);
            }
          }
        });

        lookupsCache.loaded = true;
      } catch (e) {
        console.error('Error preloading lookups:', e);
      } finally {
        lookupsCache.loadingPromise = null;
      }
    })();

    return lookupsCache.loadingPromise;
  };

  const getSelectedAssemblies = (): Set<any> => {
    const selectedSlugsOrIds = new Set(filterData && filterData.meets ? filterData.meets : []);
    const assemblies = new Set<any>();
    (lookupsCache.meets || []).forEach(m => {
      if (
        selectedSlugsOrIds.has(m.slug) ||
        selectedSlugsOrIds.has(m.id) ||
        selectedSlugsOrIds.has(String(m.id))
      ) {
        if (m.assembly !== undefined && m.assembly !== null) {
          assemblies.add(m.assembly);
        }
      }
    });
    return assemblies;
  };

  const getSelectedMeetIds = (): Set<any> => {
    const selectedSlugsOrIds = new Set(filterData && filterData.meets ? filterData.meets : []);
    const allowedIds = new Set<any>();
    (lookupsCache.meets || []).forEach(m => {
      if (
        selectedSlugsOrIds.has(m.slug) ||
        selectedSlugsOrIds.has(m.id) ||
        selectedSlugsOrIds.has(String(m.id))
      ) {
        allowedIds.add(m.id);
      }
    });
    return allowedIds;
  };

  const ensureAttendingId = async () => {
    let attendingId = (currentAttendeeData && (currentAttendeeData.attending_id || currentAttendeeData.attending))
      || (currentRawMeets[0] && currentRawMeets[0].attending);
    if (attendingId) {
      if (currentAttendeeData) currentAttendeeData.attending_id = attendingId;
      return attendingId;
    }

    if (!currentAttendeeData || !currentAttendeeData.attendee_id) return null;

    if (endpoints.attendings) {
      try {
        const getRes = await fetch(`${endpoints.attendings}?take=1`, {
          headers: {
            'X-Target-Attendee-Id': String(currentAttendeeData.attendee_id)
          }
        });
        if (getRes.ok) {
          const data = await getRes.json();
          const items = data.data || data.results || (Array.isArray(data) ? data : []);
          if (items.length > 0 && items[0].id) {
            currentAttendeeData.attending_id = items[0].id;
            return items[0].id;
          }
        }
      } catch (e) {
        console.warn('Could not fetch attending:', e);
      }

      try {
        const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value || '';
        const attgRes = await fetch(endpoints.attendings, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Target-Attendee-Id': String(currentAttendeeData.attendee_id),
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            attendee: currentAttendeeData.attendee_id,
            registration: null
          })
        });
        if (attgRes.ok) {
          const newAttending = await attgRes.json();
          currentAttendeeData.attending_id = newAttending.id;
          return newAttending.id;
        }
      } catch (e) {
        console.warn('Could not initialize attending:', e);
      }
    }

    return null;
  };

  /**
   * Saves the attendingmeet form data by sending a POST (for new) or PATCH (for existing) request.
   */
  const saveCurrentForm = async () => {
    if (!currentSortedMeets.length || !currentAttendeeData) return;
    const form = currentFormInstances[currentActiveIndex];
    if (!form) return;

    const validation = form.validate();
    if (!validation.isValid) {
      notify('Please check required fields', 'warning', WARNING_NOTIFY_TIME);
      return;
    }

    const formData = form.option('formData');
    const targetAm = currentSortedMeets[currentActiveIndex];
    const isNew = !targetAm.id || targetAm.isNew;

    let attendingId = formData.attending || targetAm.attending;
    if (!attendingId) {
      attendingId = await ensureAttendingId();
    }

    const payload = {
      meet: formData.meet,
      attending: attendingId,
      character: formData.character,
      team: formData.team || null,
      category: formData.category,
      start: formData.start ? (formData.start instanceof Date ? formData.start.toISOString() : new Date(formData.start).toISOString()) : null,
      finish: formData.finish ? (formData.finish instanceof Date ? formData.finish.toISOString() : new Date(formData.finish).toISOString()) : null,
      infos: {
        ...(targetAm.infos || {}),
        note: formData.note !== undefined ? formData.note : (formData['infos.note'] || '')
      }
    };

    try {
      const url = isNew ? endpoints.attendingmeets : `${endpoints.attendingmeets}${targetAm.id}/`;
      const method = isNew ? 'POST' : 'PATCH';
      const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value || '';

      const updateRes = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-Target-Attendee-Id': String(currentAttendeeData.attendee_id)
        },
        body: JSON.stringify(payload)
      });

      if (!updateRes.ok) {
        const errData = await updateRes.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to ${isNew ? 'create' : 'update'} attendingmeet`);
      }

      const resData = await updateRes.json().catch(() => ({}));
      const savedAm = resData.data || resData;
      if (isNew && savedAm && savedAm.id) {
        targetAm.id = savedAm.id;
        targetAm.isNew = false;
        currentRawMeets.push(savedAm);
      }

      // Update currentAttendeeData in memory so check-in buttons immediately get active state
      if (currentAttendeeData) {
        if (!currentAttendeeData.attendingmeets) {
          currentAttendeeData.attendingmeets = [];
        }
        const savedAmId = (savedAm && savedAm.id) || targetAm.id;
        const targetMeetId = Number(formData.meet || targetAm.meet);
        const targetCharId = Number(formData.character || targetAm.character);
        const targetCatId = Number(formData.category || targetAm.category);
        const targetTeamId = formData.team || targetAm.team || null;
        const updatedAmItem = {
          ...(savedAm || {}),
          id: savedAmId,
          attendingmeet_id: savedAmId,
          meet_id: targetMeetId,
          meet: targetMeetId,
          start: payload.start,
          finish: payload.finish,
          character_id: targetCharId,
          character: targetCharId,
          category_id: targetCatId,
          category: targetCatId,
          team_id: targetTeamId,
          team: targetTeamId,
          infos: payload.infos
        };

        const amIndex = currentAttendeeData.attendingmeets.findIndex(
          (am: any) => (am.id && am.id === savedAmId) ||
                (am.attendingmeet_id && am.attendingmeet_id === savedAmId) ||
                Number(am.meet_id || am.meet) === targetMeetId
        );
        if (amIndex >= 0) {
          currentAttendeeData.attendingmeets[amIndex] = {
            ...currentAttendeeData.attendingmeets[amIndex],
            ...updatedAmItem
          };
        } else {
          currentAttendeeData.attendingmeets.push(updatedAmItem);
        }

        if (gridInstanceRef && gridInstanceRef.value) {
          const rIdx = gridInstanceRef.value.getRowIndexByKey(currentAttendeeData.attendee_id);
          if (rIdx >= 0) {
            gridInstanceRef.value.repaintRows([rIdx]);
          }
        }
      }

      notify(
        {
          message: `${isNew ? 'Create' : 'Update'} attendingmeet success`,
          position: { my: 'center', at: 'center', of: window as any }
        },
        'success',
        2000
      );

      if (popupInstance) {
        popupInstance.hide();
      }
      if (typeof reloadCallback === 'function') {
        await reloadCallback(currentAttendeeData.attendee_id);
      } else if (gridInstanceRef && gridInstanceRef.value) {
        gridInstanceRef.value.refresh();
      }
    } catch (saveErr: any) {
      console.error('Error saving attendingmeet:', saveErr);
      notify(`Save failed: ${saveErr.message}`, 'error', WARNING_NOTIFY_TIME);
    }
  };

  const endCurrentEnrollment = async () => {
    if (!currentSortedMeets.length || !currentAttendeeData) return;
    const targetAm = currentSortedMeets[currentActiveIndex];
    if (!targetAm || !targetAm.id || targetAm.isNew) return;

    const nowIso = new Date().toISOString();
    const payload = {
      finish: nowIso
    };

    try {
      const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value || '';
      const updateRes = await fetch(`${endpoints.attendingmeets}${targetAm.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-Target-Attendee-Id': String(currentAttendeeData.attendee_id)
        },
        body: JSON.stringify(payload)
      });

      if (!updateRes.ok) {
        const errData = await updateRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to end attendingmeet');
      }

      if (currentAttendeeData && currentAttendeeData.attendingmeets) {
        const targetMeetId = Number(targetAm.meet);
        const amIndex = currentAttendeeData.attendingmeets.findIndex(
          (am: any) => (am.id && am.id === targetAm.id) ||
                (am.attendingmeet_id && am.attendingmeet_id === targetAm.id) ||
                Number(am.meet_id || am.meet) === targetMeetId
        );
        if (amIndex >= 0) {
          currentAttendeeData.attendingmeets[amIndex].finish = nowIso;
        }
        if (gridInstanceRef && gridInstanceRef.value) {
          const rIdx = gridInstanceRef.value.getRowIndexByKey(currentAttendeeData.attendee_id);
          if (rIdx >= 0) {
            gridInstanceRef.value.repaintRows([rIdx]);
          }
        }
      }

      notify(
        {
          message: 'Enrollment ended successfully',
          position: { my: 'center', at: 'center', of: window as any }
        },
        'success',
        2000
      );

      if (popupInstance) popupInstance.hide();
      if (typeof reloadCallback === 'function') {
        await reloadCallback(currentAttendeeData.attendee_id);
      } else if (gridInstanceRef && gridInstanceRef.value) {
        gridInstanceRef.value.refresh();
      }
    } catch (err: any) {
      console.error('Error ending attendingmeet:', err);
      notify(err.message || 'Error ending attendingmeet', 'error', WARNING_NOTIFY_TIME);
    }
  };

  const extractContactElements = (contactsDict: any, fallbackContactsStr: string | null, includeTypeIcons = true): string[] => {
    const links: string[] = [];
    const dict = contactsDict || {};

    if (typeof dict === 'object' && dict !== null && Object.keys(dict).length > 0) {
      for (const [key, rawVal] of Object.entries(dict)) {
        if (!rawVal) continue;
        const val = String(rawVal).trim();
        if (!val) continue;

        if (key.toLowerCase().includes('email') || val.includes('@')) {
          const iconHtml = includeTypeIcons ? '<i class="fas fa-envelope me-1 text-secondary"></i>' : '';
          links.push(`
            <a href="mailto:${val}" class="text-decoration-none text-primary me-2 d-inline-flex align-items-center" title="Send email: ${val}">
              ${iconHtml}${val}
            </a>
          `);
        } else if (key.toLowerCase().includes('phone') || key.toLowerCase().includes('tel') || key.toLowerCase().includes('mobile') || key.toLowerCase().includes('cell')) {
          const cleanPhone = val.replace(/[^0-9+]/g, '');
          const iconHtml = includeTypeIcons ? '<i class="fas fa-phone me-1 text-secondary"></i>' : '';
          links.push(`
            <span class="d-inline-flex align-items-center me-2">
              <a href="tel:${cleanPhone}" class="text-decoration-none text-primary me-1" title="Call: ${val}">
                ${iconHtml}${val}
              </a>
              <a href="sms:${cleanPhone}" class="text-decoration-none text-success d-inline-flex align-items-center" title="Send text: ${val}"><i class="fas fa-comment me-1 text-success"></i>text</a>
            </span>
          `);
        } else {
          links.push(`<span class="text-muted me-2">${val}</span>`);
        }
      }
    }

    if (links.length === 0 && fallbackContactsStr) {
      const parts = String(fallbackContactsStr).split(',').map(s => s.trim()).filter(Boolean);
      for (const part of parts) {
        if (part.includes('@')) {
          const iconHtml = includeTypeIcons ? '<i class="fas fa-envelope me-1 text-secondary"></i>' : '';
          links.push(`
            <a href="mailto:${part}" class="text-decoration-none text-primary me-2 d-inline-flex align-items-center" title="Send email: ${part}">
              ${iconHtml}${part}
            </a>
          `);
        } else if (/[0-9]{7,}/.test(part.replace(/[^0-9]/g, ''))) {
          const cleanPhone = part.replace(/[^0-9+]/g, '');
          const iconHtml = includeTypeIcons ? '<i class="fas fa-phone me-1 text-secondary"></i>' : '';
          links.push(`
            <span class="d-inline-flex align-items-center me-2">
              <a href="tel:${cleanPhone}" class="text-decoration-none text-primary me-1" title="Call: ${part}">
                ${iconHtml}${part}
              </a>
              <a href="sms:${cleanPhone}" class="text-decoration-none text-success d-inline-flex align-items-center" title="Send text: ${part}"><i class="fas fa-comment me-1 text-success"></i>text</a>
            </span>
          `);
        } else {
          links.push(`<span class="text-muted me-2">${part}</span>`);
        }
      }
    }

    return links;
  };

  const formatContactLinks = (attendeeData: any): string => {
    if (!attendeeData) return '';
    const links = extractContactElements(attendeeData.infos_contacts, attendeeData.contacts, true);
    if (links.length === 0) return '';
    return `<div class="attendingmeets-modal-contacts d-flex flex-wrap align-items-center small mt-1">${links.join('')}</div>`;
  };

  const formatParentsContactLinks = (attendeeData: any): string => {
    if (!attendeeData || !Array.isArray(attendeeData.parents) || attendeeData.parents.length === 0) {
      return '';
    }

    const parentBlocks: string[] = [];
    for (const parent of attendeeData.parents) {
      const parentName = parent.name || 'Parent';
      const pId = parent.id || '';
      const nameHtml = pId
        ? `<u><a href="/persons/attendee/${pId}" target="_blank" class="attendee-info-link text-secondary fw-semibold me-1" title="Open parent profile page">${parentName}:</a></u>`
        : `<span class="fw-semibold text-secondary me-1">${parentName}:</span>`;

      const contactElements = extractContactElements(parent.infos_contacts, parent.contacts, false);
      const contactsContent = contactElements.length > 0
        ? contactElements.join('')
        : `<span class="text-muted me-2">(no contacts)</span>`;

      parentBlocks.push(`
        <span class="d-inline-flex align-items-center me-3 my-1 flex-wrap">
          ${nameHtml}
          ${contactsContent}
        </span>
      `);
    }

    if (parentBlocks.length === 0) return '';

    return `
      <div class="attendingmeets-modal-parents d-flex flex-wrap align-items-center small mt-1">
        <i class="fas fa-home me-2 text-secondary" title="Parents / Guardians"></i>Parents:
        ${parentBlocks.join('')}
      </div>
    `;
  };

  const createHeaderElement = (attendeeData: any): HTMLElement => {
    const headerEl = document.createElement('div');
    headerEl.className = 'attendingmeets-modal-header d-flex align-items-start p-2 bg-light rounded border';

    let photoHtml = '';
    if (attendeeData && attendeeData.photo_url) {
      photoHtml = `
        <a href="${attendeeData.photo_url}" target="_blank" title="Click to view full image" class="me-3 d-inline-block flex-shrink-0">
          <img src="${attendeeData.photo_url}" class="attendingmeets-modal-photo" alt="${attendeeData.attendee_name || 'Attendee'}">
        </a>
      `;
    } else {
      photoHtml = `
        <div class="attendingmeets-modal-photo d-flex justify-content-center align-items-center bg-white text-muted me-3 flex-shrink-0">
          <i class="fas fa-user fa-3x text-secondary"></i>
        </div>
      `;
    }

    const attendeeId = (attendeeData && attendeeData.attendee_id) || '';
    const attendeeName = (attendeeData && attendeeData.attendee_name) || '';
    const contactsHtml = formatContactLinks(attendeeData);
    const parentsHtml = formatParentsContactLinks(attendeeData);

    let siblingsHtml = '';
    if (attendeeData && Array.isArray(attendeeData.siblings) && attendeeData.siblings.length > 0) {
      const siblingItems = attendeeData.siblings.map((s: any) => {
        const colorClass = s.attending ? 'text-success fw-semibold' : 'text-muted';
        const infoLink = s.id ? ` <u><a href="/persons/attendee/${s.id}" target="_blank" class="attendee-info-link small" title="Open sibling profile page">(Info)</a></u>` : '';
        return `
          <div class="attendingmeets-sibling-item text-truncate" title="${s.name} (${s.attending ? 'Attending' : 'Not attending'})">
            <u class="sibling-search-link ${colorClass}" role="button" data-name="${s.name}" title="Click to search this sibling in the roster">• ${s.name}</u>${infoLink}
          </div>
        `;
      }).join('');

      siblingsHtml = `
        <div class="attendingmeets-modal-siblings mt-2 pt-1 border-top">
          <div class="text-muted small fw-semibold mb-1"><i class="fas fa-user-friends me-1"></i>Siblings:</div>
          ${siblingItems}
        </div>
      `;
    }

    headerEl.innerHTML = `
      ${photoHtml}
      <div class="attendingmeets-modal-info flex-grow-1" style="min-width: 0;">
        <div class="d-flex align-items-center flex-wrap">
          <span class="fs-5 fw-bold text-dark me-2">${attendeeName}</span>
          ${attendeeId ? `<u><a href="/persons/attendee/${attendeeId}" target="_blank" class="attendee-info-link" title="Open attendee profile page">(Info)</a></u>` : ''}
        </div>
        ${contactsHtml}
        ${parentsHtml}
        ${siblingsHtml}
      </div>
    `;

    headerEl.querySelectorAll('.sibling-search-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const name = link.getAttribute('data-name');
        if (popupInstance) popupInstance.hide();
        if (name && gridInstanceRef && gridInstanceRef.value) {
          gridInstanceRef.value.searchByText(name);
        }
      });
    });

    return headerEl;
  };

  const createFormConfig = (am: any): any => {
    const isMobile = window.innerWidth < 768;
    const selectedAssemblies = getSelectedAssemblies();

    // Only show meets belonging to the same assembly as the page's selected meets
    let availableMeets = selectedAssemblies.size
      ? lookupsCache.meets.filter(m => selectedAssemblies.has(m.assembly))
      : lookupsCache.meets;
    if (am.meet !== undefined && am.meet !== null && !availableMeets.some(m => m.id === am.meet)) {
      const currentMeetObj = lookupsCache.meets.find(m => m.id === am.meet);
      if (currentMeetObj) availableMeets = [currentMeetObj, ...availableMeets];
    }

    // Only show characters belonging to the same assembly as the page's selected meets
    let availableCharacters = selectedAssemblies.size
      ? lookupsCache.characters.filter(c => selectedAssemblies.has(c.assembly))
      : lookupsCache.characters;
    if (am.character !== undefined && am.character !== null && !availableCharacters.some(c => c.id === am.character)) {
      const currentCharObj = lookupsCache.characters.find(c => c.id === am.character);
      if (currentCharObj) availableCharacters = [currentCharObj, ...availableCharacters];
    }

    // Only show teams belonging to the page's selected meets
    const selectedMeetIds = getSelectedMeetIds();
    let availableTeams = selectedMeetIds.size
      ? lookupsCache.teams.filter(t => selectedMeetIds.has(t.meet))
      : lookupsCache.teams;
    if (am.team !== undefined && am.team !== null && !availableTeams.some(t => t.id === am.team)) {
      const currentTeamObj = lookupsCache.teams.find(t => t.id === am.team);
      if (currentTeamObj) availableTeams = [currentTeamObj, ...availableTeams];
    }

    const formData = {
      meet: am.meet,
      attending: am.attending,
      character: am.character,
      team: am.team || null,
      category: am.category,
      start: am.start ? new Date(am.start) : null,
      finish: am.finish ? new Date(am.finish) : null,
      note: (am.infos && am.infos.note) || ''
    };

    const attendingItem = {
      id: am.attending,
      attending_label: am.attending__attendee || (currentAttendeeData ? currentAttendeeData.attendee_name : `Attending #${am.attending}`)
    };

    return {
      formData: formData,
      width: '100%',
      colCount: isMobile ? 1 : 2,
      colCountByScreen: {
        xs: 1,
        sm: 1,
        md: 2,
        lg: 2
      },
      items: [
        {
          colSpan: 1,
          cssClass: 'attendingmeets-top-left-header-item',
          label: { visible: false },
          template: (_data: any, itemElement: HTMLElement) => {
            if (currentAttendeeData) {
              const headerEl = createHeaderElement(currentAttendeeData);
              if (itemElement && itemElement.appendChild) {
                itemElement.appendChild(headerEl);
              }
            }
          }
        },
        {
          itemType: 'group',
          colSpan: 1,
          cssClass: 'attendingmeets-top-right-group',
          items: [
            {
              dataField: 'meet',
              editorType: 'dxSelectBox',
              label: { text: 'Meet' },
              helpText: "What's the activity?",
              validationRules: [{ type: 'required' }],
              editorOptions: {
                value: am.meet,
                dataSource: availableMeets,
                valueExpr: 'id',
                displayExpr: 'display_name',
                searchEnabled: true,
                placeholder: 'Select meet...'
              }
            },
            {
              dataField: 'attending',
              editorType: 'dxSelectBox',
              label: { text: 'Attending' },
              helpText: "who?",
              validationRules: [{ type: 'required' }],
              editorOptions: {
                value: am.attending,
                dataSource: [attendingItem],
                valueExpr: 'id',
                displayExpr: 'attending_label',
                readOnly: true,
                placeholder: 'Select attending...'
              }
            },
            {
              dataField: 'character',
              editorType: 'dxSelectBox',
              label: { text: 'Character' },
              helpText: 'define participation role',
              validationRules: [{ type: 'required' }],
              editorOptions: {
                value: am.character,
                dataSource: availableCharacters,
                valueExpr: 'id',
                displayExpr: 'display_name',
                searchEnabled: true,
                placeholder: 'Select character...'
              }
            }
          ]
        },
        {
          dataField: 'team',
          editorType: 'dxSelectBox',
          colSpan: 1,
          label: { text: 'Team' },
          helpText: '(Optional) joining team',
          editorOptions: {
            value: am.team || null,
            dataSource: availableTeams,
            valueExpr: 'id',
            displayExpr: 'display_name',
            showClearButton: true,
            searchEnabled: true,
            placeholder: '(Optional) select team...'
          }
        },
        {
          dataField: 'category',
          editorType: 'dxSelectBox',
          colSpan: 1,
          label: { text: 'Category' },
          helpText: 'What type of participation?',
          validationRules: [{ type: 'required' }],
          editorOptions: {
            value: am.category,
            dataSource: lookupsCache.categories,
            valueExpr: 'id',
            displayExpr: 'display_name',
            showClearButton: true,
            searchEnabled: true,
            placeholder: 'Select category...'
          }
        },
        {
          dataField: 'start',
          editorType: 'dxDateBox',
          colSpan: 1,
          label: { text: 'Start' },
          helpText: 'participation start time in browser timezone',
          validationRules: [{ type: 'required' }],
          editorOptions: {
            value: am.start ? new Date(am.start) : null,
            type: 'datetime',
            displayFormat: 'yyyy-MM-dd HH:mm',
            dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss'
          }
        },
        {
          dataField: 'finish',
          editorType: 'dxDateBox',
          colSpan: 1,
          label: { text: 'Finish' },
          helpText: 'participation end time in browser timezone',
          validationRules: [{ type: 'required' }],
          editorOptions: {
            value: am.finish ? new Date(am.finish) : null,
            type: 'datetime',
            displayFormat: 'yyyy-MM-dd HH:mm',
            dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss'
          }
        },
        {
          dataField: 'note',
          editorType: 'dxTextArea',
          label: { text: 'Note' },
          helpText: 'special memo',
          colSpan: isMobile ? 1 : 2,
          editorOptions: {
            value: (am.infos && am.infos.note) || '',
            autoResizeEnabled: true,
            minHeight: 60,
            placeholder: 'Special memo or note...'
          }
        }
      ]
    };
  };

  const updateToolbarVisibility = (hasAm: boolean, isNewAm = false) => {
    if (!popupInstance) return;
    const items = popupInstance.option('toolbarItems');
    if (Array.isArray(items)) {
      const updated = items.map((item: any) => {
        if (item.options && item.options.text === 'Save') {
          return {
            ...item,
            options: {
              ...item.options,
              visible: Boolean(hasAm)
            }
          };
        }
        if (item.options && item.options.text === 'End') {
          return {
            ...item,
            options: {
              ...item.options,
              visible: Boolean(hasAm) && !isNewAm
            }
          };
        }
        return item;
      });
      popupInstance.option('toolbarItems', updated);
    }
  };

  const createDefaultAttendingMeet = (meetId: any): any => {
    const meetObj = (lookupsCache.meets || []).find(m => String(m.id) === String(meetId) || m.slug === meetId)
      || meetsMap.get(meetId)
      || meetsMap.get(String(meetId));

    const defaultWeeks = (meetObj && meetObj.infos && meetObj.infos.default_attendingmeet_in_weeks)
      ? Number(meetObj.infos.default_attendingmeet_in_weeks)
      : 53;

    const nowTime = Date.now();
    let baseStartMs = nowTime;
    if (filterData && filterData.startDate && filterData.endDate) {
      const filterStartMs = new Date(filterData.startDate).getTime();
      const filterEndMs = new Date(filterData.endDate).getTime();
      if (nowTime < filterStartMs || nowTime > filterEndMs) {
        baseStartMs = filterStartMs;
      }
    }

    const startDate = new Date(baseStartMs);
    const finishDate = new Date(baseStartMs + defaultWeeks * 7 * 24 * 60 * 60 * 1000);

    let defaultCharacter = meetObj && meetObj.major_character;
    if (!defaultCharacter && meetObj && meetObj.assembly && lookupsCache.characters) {
      const charInAssembly = lookupsCache.characters.find((c: any) => c.assembly === meetObj.assembly && (c.slug === 'attendee' || c.display_name === 'Attendee'))
        || lookupsCache.characters.find((c: any) => c.assembly === meetObj.assembly);
      if (charInAssembly) defaultCharacter = charInAssembly.id;
    }
    if (!defaultCharacter) {
      defaultCharacter = (lookupsCache.characters && lookupsCache.characters[0] && lookupsCache.characters[0].id) || 1;
    }

    const scheduledCategory = endpoints.scheduledCategory
      || (document.getElementById('app')?.dataset?.scheduledCategory ? parseInt(document.getElementById('app')!.dataset.scheduledCategory!, 10) : 1);

    const defaultCategory = (meetObj && meetObj.infos && meetObj.infos.active_category)
      || scheduledCategory;

    const attendingId = (currentAttendeeData && (currentAttendeeData.attending_id || currentAttendeeData.attending))
      || (currentRawMeets[0] && currentRawMeets[0].attending)
      || null;

    const parsedMeetId = meetObj ? meetObj.id : (Number(meetId) || meetId);

    return {
      isNew: true,
      meet: parsedMeetId,
      attending: attendingId,
      character: defaultCharacter,
      team: null,
      category: defaultCategory,
      start: startDate.toISOString(),
      finish: finishDate.toISOString(),
      infos: { note: '' }
    };
  };

  const getPageMeets = (): any[] => {
    const selectedSlugsOrIds = filterData && filterData.meets ? filterData.meets : [];
    const result: any[] = [];
    const seenIds = new Set<string>();

    selectedSlugsOrIds.forEach(slugOrId => {
      let meetObj = (lookupsCache.meets || []).find(m =>
        m.slug === slugOrId || m.id === slugOrId || String(m.id) === String(slugOrId)
      ) || meetsMap.get(slugOrId) || meetsMap.get(String(slugOrId));

      const id = meetObj ? meetObj.id : slugOrId;
      const displayName = meetObj ? (meetObj.display_name || meetObj.name || slugOrId) : (meetsInfoMap.get(slugOrId) || String(slugOrId));

      if (!seenIds.has(String(id))) {
        seenIds.add(String(id));
        result.push({
          id: id,
          slug: meetObj ? meetObj.slug : slugOrId,
          display_name: displayName
        });
      }
    });

    return result;
  };

  const renderSelectedMeetContent = (meetId: any, contentArea: HTMLElement, _pageMeets: any[]) => {
    contentArea.innerHTML = '';
    currentFormInstances = [];
    currentActiveIndex = 0;

    // Find attendingmeets for this meet
    const matched = currentRawMeets.filter(am => am.meet === meetId || String(am.meet) === String(meetId));
    if (matched.length > 0) {
      currentSortedMeets = matched.slice().sort((a, b) => {
        if (!a.finish && !b.finish) return 0;
        if (!a.finish) return -1;
        if (!b.finish) return 1;
        return new Date(b.finish).getTime() - new Date(a.finish).getTime();
      });

      updateToolbarVisibility(true, false);

      if (currentSortedMeets.length === 1) {
        const formEl = document.createElement('div');
        contentArea.appendChild(formEl);
        const formInst = new (dxForm as any)(formEl, createFormConfig(currentSortedMeets[0]));
        currentFormInstances.push(formInst);
      } else {
        const tabItems = currentSortedMeets.map((am, i) => {
          const meetName = lookupsCache.meetNames[am.meet] || am.meet__display_name || `Meet #${am.meet}`;
          const finishLabel = am.finish ? am.finish.substring(0, 10) : 'Ongoing';
          return {
            title: `${meetName} (${finishLabel})`,
            am: am,
            index: i
          };
        });

        new (dxTabPanel as any)(contentArea, {
          dataSource: tabItems,
          width: '100%',
          selectedIndex: 0,
          deferRendering: false,
          loop: false,
          animationEnabled: true,
          swipeEnabled: false,
          onSelectionChanged: (e: any) => {
            currentActiveIndex = e.component.option('selectedIndex');
          },
          itemTemplate: (itemData: any, itemIndex: number, itemElement: HTMLElement) => {
            const formEl = document.createElement('div');
            itemElement.append(formEl);
            const formInst = new (dxForm as any)(formEl, createFormConfig(itemData.am));
            currentFormInstances[itemIndex] = formInst;
          }
        });
      }
    } else {
      // No existing enrollment -> open form with default values so user can create attendingmeet
      const defaultAm = createDefaultAttendingMeet(meetId);
      currentSortedMeets = [defaultAm];

      updateToolbarVisibility(true, true);

      const formEl = document.createElement('div');
      contentArea.appendChild(formEl);
      const formInst = new (dxForm as any)(formEl, createFormConfig(defaultAm));
      currentFormInstances.push(formInst);
    }
  };

  const renderPopupContent = (container: HTMLElement) => {
    container.innerHTML = '';

    const pageMeets = getPageMeets();
    const isMultiMeet = pageMeets.length > 1;

    if (isMultiMeet) {
      const topBar = document.createElement('div');
      topBar.className = 'attendingmeets-top-meet-bar d-flex align-items-center mb-3 p-2 bg-light rounded border';

      const label = document.createElement('label');
      label.className = 'form-label mb-0 me-2 fw-semibold text-secondary text-nowrap';
      label.htmlFor = 'attendingmeets-meet-select';
      label.innerHTML = '<i class="fas fa-calendar-alt me-1"></i>Meet:';
      topBar.appendChild(label);

      const selectEl = document.createElement('select');
      selectEl.id = 'attendingmeets-meet-select';
      selectEl.className = 'form-select form-select-sm attendingmeets-meet-dropdown flex-grow-1';
      pageMeets.forEach(pm => {
        const opt = document.createElement('option');
        opt.value = String(pm.id);
        opt.textContent = pm.display_name;
        if (String(pm.id) === String(currentSelectedMeetId)) {
          opt.selected = true;
        }
        selectEl.appendChild(opt);
      });

      topBar.appendChild(selectEl);
      container.appendChild(topBar);

      const contentArea = document.createElement('div');
      contentArea.className = 'attendingmeets-content-area';
      container.appendChild(contentArea);

      selectEl.addEventListener('change', (e: any) => {
        currentSelectedMeetId = e.target.value;
        renderSelectedMeetContent(currentSelectedMeetId, contentArea, pageMeets);
      });

      renderSelectedMeetContent(currentSelectedMeetId, contentArea, pageMeets);
    } else {
      const allowedMeetIds = getSelectedMeetIds();
      const matchedMeets = currentRawMeets.filter(am => allowedMeetIds.has(am.meet));
      if (matchedMeets.length > 0) {
        currentSortedMeets = matchedMeets.slice().sort((a, b) => {
          if (!a.finish && !b.finish) return 0;
          if (!a.finish) return -1;
          if (!b.finish) return 1;
          return new Date(b.finish).getTime() - new Date(a.finish).getTime();
        });

        updateToolbarVisibility(true, false);

        const contentArea = document.createElement('div');
        contentArea.className = 'attendingmeets-content-area';
        container.appendChild(contentArea);

        currentFormInstances = [];
        currentActiveIndex = 0;

        if (currentSortedMeets.length === 1) {
          const formEl = document.createElement('div');
          contentArea.appendChild(formEl);
          const formInst = new (dxForm as any)(formEl, createFormConfig(currentSortedMeets[0]));
          currentFormInstances.push(formInst);
        } else {
          const tabItems = currentSortedMeets.map((am, i) => {
            const meetName = lookupsCache.meetNames[am.meet] || am.meet__display_name || `Meet #${am.meet}`;
            const finishLabel = am.finish ? am.finish.substring(0, 10) : 'Ongoing';
            return {
              title: `${meetName} (${finishLabel})`,
              am: am,
              index: i
            };
          });

          new (dxTabPanel as any)(contentArea, {
            dataSource: tabItems,
            width: '100%',
            selectedIndex: 0,
            deferRendering: false,
            loop: false,
            animationEnabled: true,
            swipeEnabled: false,
            onSelectionChanged: (e: any) => {
              currentActiveIndex = e.component.option('selectedIndex');
            },
            itemTemplate: (itemData: any, itemIndex: number, itemElement: HTMLElement) => {
              const formEl = document.createElement('div');
              itemElement.append(formEl);
              const formInst = new (dxForm as any)(formEl, createFormConfig(itemData.am));
              currentFormInstances[itemIndex] = formInst;
            }
          });
        }
      } else {
        const singleMeetId = allowedMeetIds.size > 0 ? Array.from(allowedMeetIds)[0] : (pageMeets[0] ? pageMeets[0].id : null);
        const defaultAm = createDefaultAttendingMeet(singleMeetId);
        currentSortedMeets = [defaultAm];

        updateToolbarVisibility(true, true);

        const contentArea = document.createElement('div');
        contentArea.className = 'attendingmeets-content-area';
        container.appendChild(contentArea);

        currentFormInstances = [];
        currentActiveIndex = 0;

        const formEl = document.createElement('div');
        contentArea.appendChild(formEl);
        const formInst = new (dxForm as any)(formEl, createFormConfig(defaultAm));
        currentFormInstances.push(formInst);
      }
    }
  };

  const openAttendingMeetsPopup = async (attendeeData: AttendeeRow | any) => {
    currentAttendeeData = attendeeData;
    if (!popupElement) {
      popupElement = document.createElement('div');
      popupElement.id = 'attendingmeets-editor-popup';
      document.body.appendChild(popupElement);
    }

    await preloadLookups();

    try {
      const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value || '';
      const res = await fetch(endpoints.attendingmeets, {
        headers: {
          'X-Target-Attendee-Id': String(attendeeData.attendee_id),
          'X-CSRFToken': csrfToken
        }
      });
      if (!res.ok) throw new Error('Failed to load attendee enrollments');
      const json = await res.json();
      currentRawMeets = json.data || [];
    } catch (err: any) {
      notify(`Error loading enrollments: ${err.message}`, 'error', WARNING_NOTIFY_TIME);
      return;
    }

    const pageMeets = getPageMeets();
    const isMultiMeet = pageMeets.length > 1;

    // Ensure attendee has attending_id
    await ensureAttendingId();

    if (isMultiMeet) {
      const firstEnrolledMeet = pageMeets.find(pm =>
        currentRawMeets.some(am => am.meet === pm.id || String(am.meet) === String(pm.id))
      );
      currentSelectedMeetId = firstEnrolledMeet ? firstEnrolledMeet.id : pageMeets[0].id;

      const matched = currentRawMeets.filter(am => am.meet === currentSelectedMeetId || String(am.meet) === String(currentSelectedMeetId));
      if (matched.length > 0) {
        currentSortedMeets = matched.slice().sort((a, b) => {
          if (!a.finish && !b.finish) return 0;
          if (!a.finish) return -1;
          if (!b.finish) return 1;
          return new Date(b.finish).getTime() - new Date(a.finish).getTime();
        });
      } else {
        currentSortedMeets = [createDefaultAttendingMeet(currentSelectedMeetId)];
      }
    } else {
      const allowedMeetIds = getSelectedMeetIds();
      const matchedMeets = currentRawMeets.filter(am => allowedMeetIds.has(am.meet));
      if (matchedMeets.length > 0) {
        currentSortedMeets = matchedMeets.slice().sort((a, b) => {
          if (!a.finish && !b.finish) return 0;
          if (!a.finish) return -1;
          if (!b.finish) return 1;
          return new Date(b.finish).getTime() - new Date(a.finish).getTime();
        });
      } else {
        const singleMeetId = allowedMeetIds.size > 0 ? Array.from(allowedMeetIds)[0] : (pageMeets[0] ? pageMeets[0].id : null);
        currentSortedMeets = [createDefaultAttendingMeet(singleMeetId)];
      }
    }

    const isMobile = window.innerWidth < 768;
    const popupWidth = isMobile ? '92%' : '70%';
    const popupHeight = isMobile ? 'auto' : '70%';
    const popupTitle = `${attendeeData.attendee_name} enrollment`;

    const isFirstNew = currentSortedMeets.length > 0 && (currentSortedMeets[0].isNew || !currentSortedMeets[0].id);
    const toolbarItems = [
      {
        toolbar: 'top',
        location: 'after',
        widget: 'dxButton',
        options: {
          text: 'End',
          type: 'danger',
          icon: 'trash',
          stylingMode: 'contained',
          visible: currentSortedMeets.length > 0 && !isFirstNew,
          onClick: endCurrentEnrollment
        }
      },
      {
        toolbar: 'top',
        location: 'after',
        widget: 'dxButton',
        options: {
          text: 'Save',
          type: 'success',
          icon: 'save',
          stylingMode: 'contained',
          visible: currentSortedMeets.length > 0,
          onClick: saveCurrentForm
        }
      }
    ];

    if (!popupInstance) {
      popupInstance = new (dxPopup as any)(popupElement, {
        title: popupTitle,
        width: popupWidth,
        height: popupHeight,
        fullScreen: false,
        animation: null,
        wrapperAttr: {
          class: 'attendingmeets-popup-wrapper'
        },
        showCloseButton: true,
        dragEnabled: !isMobile,
        toolbarItems: toolbarItems,
        onShowing: () => {
          if ((window as any).Attendees && (window as any).Attendees.utilities) {
            (window as any).Attendees.utilities.editingEnabled = true;
          }
        },
        onHiding: () => {
          if ((window as any).Attendees && (window as any).Attendees.utilities) {
            (window as any).Attendees.utilities.editingEnabled = false;
          }
        },
        contentTemplate: (container: HTMLElement) => {
          renderPopupContent(container);
        }
      });
    } else {
      popupInstance.option({
        title: popupTitle,
        width: popupWidth,
        height: popupHeight,
        fullScreen: false,
        animation: null,
        wrapperAttr: {
          class: 'attendingmeets-popup-wrapper'
        },
        dragEnabled: !isMobile,
        toolbarItems: toolbarItems,
        onShowing: () => {
          if ((window as any).Attendees && (window as any).Attendees.utilities) {
            (window as any).Attendees.utilities.editingEnabled = true;
          }
        },
        onHiding: () => {
          if ((window as any).Attendees && (window as any).Attendees.utilities) {
            (window as any).Attendees.utilities.editingEnabled = false;
          }
        }
      });
      const contentEl = popupInstance.content ? popupInstance.content() : null;
      if (contentEl) {
        renderPopupContent(contentEl);
      }
    }

    popupInstance.show();
  };

  return { openAttendingMeetsPopup, preloadLookups };
}
