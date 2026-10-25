;(() => {
  window.Attendees = window.Attendees || {};
  window.Attendees.utilities = window.Attendees.utilities || {};
  if (window.Attendees.utilities.editingEnabled === undefined) {
    window.Attendees.utilities.editingEnabled = false;
  }

  const { createApp, ref, reactive, onMounted } = Vue;
  const WARNING_NOTIFY_TIME = 5000;
  // Shared registry of gatherings for columns:
  const gatheringsRegistry = new Map();
  const meetsInfoMap = new Map();
  const meetsMap = new Map();

  const getMeetSignatureRequiredAt = (meetId) => {
    if (!meetId) return null;
    const m = meetsMap.get(meetId) || meetsMap.get(String(meetId));
    return (m && m.infos) ? m.infos.signature_required_at : null;
  };

  const getColumnIdentifier = (gathering) => {
    return (gathering && gathering.id) ? String(gathering.id) : `future_${gathering ? gathering.meet_id : ''}_${gathering ? gathering.start : ''}`;
  };

  const registerGathering = (gathering) => {
    if (!gathering) return null;
    const meetStartKey = (gathering.meet_id && gathering.start) ? `${gathering.meet_id}_${gathering.start}` : '';
    let existing = (meetStartKey && gatheringsRegistry.get(meetStartKey)) || (gathering.id && gatheringsRegistry.get(String(gathering.id))) || null;
    if (!existing) {
      existing = {
        id: gathering.id || null,
        meet_id: gathering.meet_id,
        meet_display_name: gathering.meet_display_name || '',
        start: gathering.start,
        finish: gathering.finish
      };
      if (meetStartKey) gatheringsRegistry.set(meetStartKey, existing);
    } else {
      if (gathering.id && !existing.id) {
        existing.id = gathering.id;
      }
      if (gathering.meet_id && !existing.meet_id) existing.meet_id = gathering.meet_id;
      if (gathering.meet_display_name && !existing.meet_display_name) existing.meet_display_name = gathering.meet_display_name;
      if (gathering.start && !existing.start) existing.start = gathering.start;
      if (gathering.finish && !existing.finish) existing.finish = gathering.finish;
    }

    if (existing.id) {
      gatheringsRegistry.set(String(existing.id), existing);
    }
    const colId = getColumnIdentifier(existing);
    gatheringsRegistry.set(colId, existing);
    return existing;
  };

  let gradeConverter = [];
  const loadGradeConverter = () => {
    const gradeConverterEl = document.getElementById('organization-grade-converter');
    if (gradeConverterEl) {
      try {
        const parsed = JSON.parse(gradeConverterEl.textContent) || [];
        gradeConverter = parsed.map((item, index) => {
          if (typeof item === 'object' && item !== null) return item;
          return { id: index, label: String(item) };
        });
      } catch (e) {
        gradeConverter = [];
      }
    }
  };

  let organizationDivisions = [];
  const loadOrganizationDivisions = async (divisionsEndpoint) => {
    if (organizationDivisions.length > 0) return organizationDivisions;
    const url = (divisionsEndpoint || '/whereabouts/api/user_divisions/') + ((divisionsEndpoint || '').includes('?') ? '&take=999' : '?take=999');
    try {
      const res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      });
      if (res.ok) {
        const json = await res.json();
        const raw = json.data || (Array.isArray(json) ? json : []);
        if (Array.isArray(raw) && raw.length > 0) {
          organizationDivisions = raw;
          return organizationDivisions;
        }
      }
    } catch (e) {
      console.warn('Could not fetch divisions from API:', e);
    }
    const divisionsEl = document.getElementById('organization-divisions');
    if (divisionsEl) {
      try {
        organizationDivisions = JSON.parse(divisionsEl.textContent) || [];
      } catch (e) {
        organizationDivisions = [];
      }
    }
    return organizationDivisions;
  };

  const meetGatheringsCache = new Map();
  const loadMeetGatherings = async (meetSlug, meetId, gatheringsEndpoint) => {
    if (!meetSlug && !meetId) return [];
    if (!meetId && meetSlug) {
      const m = meetsMap.get(meetSlug) || meetsMap.get(String(meetSlug));
      if (m && m.id) meetId = m.id;
    }
    const cacheKey = String(meetSlug || meetId);
    if (meetGatheringsCache.has(cacheKey) && meetGatheringsCache.get(cacheKey).length > 0) {
      return meetGatheringsCache.get(cacheKey);
    }

    const seen = new Set();
    const result = [];
    const addG = (g) => {
      if (!g) return;
      const idKey = g.id ? String(g.id) : (g.start ? `start_${g.start}` : null);
      if (idKey && !seen.has(idKey)) {
        seen.add(idKey);
        result.push(g);
      }
    };

    // 1. Gatherings from registry
    for (const g of gatheringsRegistry.values()) {
      if (g && ((meetId && String(g.meet_id) === String(meetId)) || (meetSlug && String(g.meet_slug) === String(meetSlug)))) {
        addG(g);
      }
    }

    // 2. Fetch from gatherings API for this meet only if not found in registry
    if (result.length === 0 && meetSlug) {
      const url = (gatheringsEndpoint || '/occasions/api/organization_team_gatherings/') + `?meets[]=${encodeURIComponent(meetSlug)}&take=999`;
      try {
        const res = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin'
        });
        if (res.ok) {
          const json = await res.json();
          const items = json.data || (Array.isArray(json) ? json : []);
          items.forEach(item => {
            addG({
              id: item.id,
              meet_id: meetId || item.meet_id,
              meet_display_name: item.meet_display_name || '',
              display_name: item.display_name,
              start: item.start,
              finish: item.finish
            });
          });
        }
      } catch (e) {
        console.warn('Could not fetch gatherings for meet from API:', e);
      }
    }

    // Sort chronologically
    result.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());

    // If completely empty, generate a synthetic option for Today
    if (result.length === 0) {
      const nowIso = new Date().toISOString();
      result.push({
        id: null,
        meet_id: meetId,
        display_name: `Today (${new Date().toLocaleDateString()})`,
        start: nowIso,
        finish: null
      });
    }

    meetGatheringsCache.set(cacheKey, result);
    return result;
  };

  let allFamilyRelations = [];
  let allRawRelations = [];
  const loadFamilyRelations = async (relationsEndpoint) => {
    if (allRawRelations.length > 0) return allRawRelations;
    const url = (relationsEndpoint || '/persons/api/all_relations/') + '?category_id=0&take=999';
    try {
      const res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      });
      if (!res.ok) throw new Error('Failed to fetch relations');
      const json = await res.json();
      const rawList = json.data || (Array.isArray(json) ? json : []);
      const excludedRoles = new Set(['masked', 'hidden']);
      allRawRelations = rawList.filter(r => r && r.id > 0 && !excludedRoles.has((r.title || '').trim().toLowerCase()));
      allFamilyRelations = allRawRelations.filter(r => (r.title || '').trim().toLowerCase() !== 'self');
      return allRawRelations;
    } catch (e) {
      console.warn('Could not load relations from API, using fallback:', e);
      allRawRelations = [
        { id: 1, title: 'parent' },
        { id: 2, title: 'child' },
        { id: 3, title: 'son' },
        { id: 4, title: 'daughter' },
        { id: 5, title: 'husband' },
        { id: 6, title: 'wife' },
        { id: 14, title: 'spouse' },
        { id: 28, title: 'self' }
      ];
      allFamilyRelations = allRawRelations.filter(r => r.title.toLowerCase() !== 'self');
      return allRawRelations;
    }
  };

  // ==========================================================
  // 1. Endpoints Logic
  // ==========================================================
  function useEndpoints() {
    const endpoints = reactive({
      rosters: '',
      meets: '',
      attendances: '', // '/occasions/api/organization_meet_character_attendances/',
      assemblies: '',
      categories: '',
      attendingmeets: '',
      attendings: '',
      characters: '',
      teams: '',
      divisions: '', // divisions: '/whereabouts/api/user_divisions/',
      gatherings: '', // '/occasions/api/organization_team_gatherings/',
      searchAttendees: '', // '/persons/api/search_attendees_for_roster/',
      fastOnboard: '', // '/persons/api/fast_onboard_attendee/',
      relations: '', // '/persons/api/all_relations/',
      userCanWrite: true
    });

    const initEndpoints = () => {
      const appEl = document.getElementById('app');
      if (appEl) {
        endpoints.rosters = appEl.dataset.rostersEndpoint || '';
        endpoints.attendances = appEl.dataset.attendancesEndpoint || '';
        endpoints.meets = appEl.dataset.meetsEndpointBySlug || '';
        endpoints.assemblies = appEl.dataset.assembliesEndpoint || '';
        endpoints.categories = appEl.dataset.categoriesEndpoint || '';
        endpoints.attendingmeets = appEl.dataset.attendingmeetsEndpoint || '';
        endpoints.attendings = appEl.dataset.attendingsEndpoint || '';
        endpoints.characters = appEl.dataset.charactersEndpoint || '';
        endpoints.teams = appEl.dataset.teamsEndpoint || '';
        endpoints.divisions = appEl.dataset.divisionsEndpoint;
        endpoints.gatherings = appEl.dataset.gatheringsEndpoint;
        endpoints.searchAttendees = appEl.dataset.searchAttendeesEndpoint;
        endpoints.fastOnboard = appEl.dataset.fastOnboardEndpoint;
        endpoints.relations = appEl.dataset.relationsEndpoint;
        endpoints.userCanWrite = appEl.dataset.userCanWrite !== 'false';
      }
      loadGradeConverter();
      loadOrganizationDivisions(endpoints.divisions);
      loadFamilyRelations(endpoints.relations);
    };

    return { endpoints, initEndpoints };
  }

  // ==========================================================
  // 2. Attendance & API Logic
  // ==========================================================
  function useAttendanceLogic(endpoints, gridInstanceRef) {
    const getAttendanceRecord = (rowData, gatheringId) => {
      if (!rowData || !rowData.attendances || !gatheringId) return null;
      return rowData.attendances.find(a => a && String(a.gathering_id) === String(gatheringId));
    };

    const isCheckedIn = (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      return !!(record && record.category_id !== 1);
    };

    const isCheckedOut = (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      return !!(record && record.finish);
    };

    const getAttendingMeetForGathering = (rowData, gathering) => {
      if (!rowData.attendingmeets || !rowData.attendingmeets.length) return null;
      if (!gathering || !gathering.meet_id) return rowData.attendingmeets[0];
      return rowData.attendingmeets.find(am => String(am.meet_id) === String(gathering.meet_id)) || null;
    };

    const getActiveAttendingMeet = (rowData, gathering) => {
      if (!rowData.attendingmeets || !rowData.attendingmeets.length) return null;
      if (!gathering || !gathering.start) {
        return rowData.attendingmeets[0];
      }
      const gStart = new Date(gathering.start);
      return rowData.attendingmeets.find(am => {
        if (gathering.meet_id && String(am.meet_id) !== String(gathering.meet_id)) {
          return false;
        }
        const amStart = am.start ? new Date(am.start) : new Date('1970-01-01');
        const amFinish = am.finish ? new Date(am.finish) : new Date('2099-12-31');
        return gStart >= amStart && gStart <= amFinish;
      }) || null;
    };

    const getAttendingMeetStatus = (rowData, gathering) => {
      if (!rowData.attendingmeets || !rowData.attendingmeets.length) return 'not_attending';
      const am = getAttendingMeetForGathering(rowData, gathering);
      if (!am) return 'not_attending';
      if (!gathering || !gathering.start) return 'active';

      const gStart = new Date(gathering.start);
      const amStart = am.start ? new Date(am.start) : new Date('1970-01-01');
      const amFinish = am.finish ? new Date(am.finish) : new Date('2099-12-31');

      if (gStart >= amStart && gStart <= amFinish) {
        return 'active';
      }
      return 'expired';
    };

    const isAttendingValid = (rowData, gathering) => {
      return getAttendingMeetStatus(rowData, gathering) !== 'not_attending';
    };

    const executeAttendanceToggle = async (rowData, gathering, domElements, rowIndex, colName, newCategory, encodedFile, clearFile) => {
      const gatheringMeta = (gathering && typeof gathering === 'object') ? gathering : null;
      let gatheringId = gatheringMeta ? gatheringMeta.id : gathering;
      let record = getAttendanceRecord(rowData, gatheringId);
      const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);

      const targetAm = getActiveAttendingMeet(rowData, gatheringMeta || gathering)
                    || getAttendingMeetForGathering(rowData, gatheringMeta || gathering);
      const attendingId = targetAm ? targetAm.attending_id : (rowData.attending_id || (rowData.attendingmeets && rowData.attendingmeets[0] ? rowData.attendingmeets[0].attending_id : null));
      const characterId = targetAm ? targetAm.character_id : (rowData.attendingmeets && rowData.attendingmeets[0] ? rowData.attendingmeets[0].character_id : 1);

      if (window.Attendees && window.Attendees.utilities) {
        window.Attendees.utilities.editingEnabled = true;
      }

      try {
        const recordId = record ? (record.attendance_id || record.id) : '';
        const payload = {
          gathering: gatheringId || null,
          attending: attendingId,
          character: characterId,
          category: newCategory
        };
        if (!gatheringId && gatheringMeta) {
          payload.meet = gatheringMeta.meet_id;
          payload.gathering_start = gatheringMeta.start;
        }

        if (encodedFile) {
          payload.encoded_file = encodedFile;
          payload.start = new Date().toISOString();
        } else if (newCategory !== 1 && (!record || !record.start)) {
          payload.start = new Date().toISOString();
        }

        if (newCategory === 1) {
          payload.finish = null;
        }

        if (clearFile) {
          payload.file = null;
          payload.start = null;
          payload.finish = null;
        }

        const response = await fetch(`${endpoints.attendances}${recordId ? recordId + '/' : ''}`, {
          method: record ? 'PATCH' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || errData.error || 'Failed to update attendance');
        }
        const updatedRecord = await response.json();

        const normalizedRecord = {
          attendance_id: updatedRecord.id,
          gathering_id: updatedRecord.gathering,
          category_id: updatedRecord.category,
          start: clearFile ? null : updatedRecord.start,
          finish: (newCategory === 1 || clearFile) ? null : updatedRecord.finish,
          file_path: clearFile ? null : (updatedRecord.file_path || null),
          file: clearFile ? null : (updatedRecord.file_path || null)
        };

        if (!rowData.attendances) {
          rowData.attendances = [];
        }
        record = getAttendanceRecord(rowData, updatedRecord.gathering);
        if (record) {
          Object.assign(record, normalizedRecord);
        } else {
          rowData.attendances.push(normalizedRecord);
        }

        // If a new gathering was created, update gatheringMeta and shared registry
        const newGatheringId = updatedRecord.gathering;
        if (newGatheringId) {
          if (gatheringMeta) {
            gatheringMeta.id = newGatheringId;
          }
          registerGathering(gatheringMeta || {
            id: newGatheringId,
            meet_id: payload.meet,
            start: payload.gathering_start
          });
        }

        // Directly update the button & out-button in the cell DOM
        if (domElements) {
          if (newCategory !== 1) { // Checked in!
            if (targetAm && gatheringMeta && gatheringMeta.start) {
              const gStart = new Date(gatheringMeta.start);
              const amFinish = targetAm.finish ? new Date(targetAm.finish) : null;
              if (!amFinish || gStart > amFinish) {
                const endOfDay = new Date(gatheringMeta.start);
                endOfDay.setHours(23, 59, 59, 999);
                targetAm.finish = endOfDay.toISOString();
              }
            }
            if (domElements.checkInBtn) {
              domElements.checkInBtn.className = 'roster-btn checked-in';
              domElements.checkInBtn.innerText = 'Checked In';
            }
            if (domElements.outBtn) {
              domElements.outBtn.style.display = 'inline-block';
              if (normalizedRecord.finish) {
                domElements.outBtn.className = 'roster-btn roster-btn-out checked-out';
                domElements.outBtn.innerText = 'Checked Out';
              } else {
                domElements.outBtn.className = 'roster-btn roster-btn-out';
                domElements.outBtn.innerText = 'Out';
              }
            }
          } else { // Undone check in
            if (domElements.checkInBtn) {
              domElements.checkInBtn.className = 'roster-btn';
              domElements.checkInBtn.innerText = 'Check In';
            }
            if (domElements.outBtn) {
              domElements.outBtn.style.display = 'none';
              domElements.outBtn.className = 'roster-btn roster-btn-out';
              domElements.outBtn.innerText = 'Out';
            }
          }
        }

        // Update the total attendances count dynamically
        const newTotal = isCurrentlyCheckedIn 
          ? Math.max(0, (rowData.total_attendances || 0) - 1)
          : (rowData.total_attendances || 0) + 1;
        
        rowData.total_attendances = newTotal;

        if (gridInstanceRef.value) {
          const rowKey = rowData.attendee_id || rowData.attending_id;
          let rIndex = (typeof rowIndex === 'number' && rowIndex >= 0) ? rowIndex : -1;
          if (rIndex < 0 && rowKey !== undefined) {
            rIndex = gridInstanceRef.value.getRowIndexByKey(rowKey);
          }
          if (rIndex >= 0) {
            const cellEl = gridInstanceRef.value.getCellElement(rIndex, 'total_attendances');
            if (cellEl) {
              if (cellEl.text) {
                cellEl.text(String(newTotal));
              } else if (cellEl[0]) {
                cellEl[0].innerText = String(newTotal);
              }
            }
            const visibleRows = typeof gridInstanceRef.value.getVisibleRows === 'function' ? gridInstanceRef.value.getVisibleRows() : null;
            if (visibleRows && visibleRows[rIndex] && visibleRows[rIndex].data) {
              const gridRowData = visibleRows[rIndex].data;
              gridRowData.total_attendances = newTotal;
              if (!gridRowData.attendances) gridRowData.attendances = [];
              const existingRec = gridRowData.attendances.find(a => a && String(a.gathering_id) === String(updatedRecord.gathering));
              if (existingRec) {
                Object.assign(existingRec, normalizedRecord);
              } else {
                gridRowData.attendances.push(normalizedRecord);
              }
            }
          }
        }

        // Dynamically adjust column width: expand to 150px on check-in, shrink to 100px if all checked out
        if (gridInstanceRef.value && colName) {
          if (newCategory !== 1) {
            const curWidth = gridInstanceRef.value.columnOption(colName, 'width');
            if (curWidth !== 150) {
              gridInstanceRef.value.columnOption(colName, 'width', 150);
              gridInstanceRef.value.columnOption(colName, 'minWidth', 150);
            }
          } else {
            const currentGId = gatheringMeta ? gatheringMeta.id : gatheringId;
            let anyOtherCheckedIn = false;
            const visibleRows = typeof gridInstanceRef.value.getVisibleRows === 'function' ? gridInstanceRef.value.getVisibleRows() : null;
            if (visibleRows && currentGId) {
              anyOtherCheckedIn = visibleRows.some(vr => 
                vr.data && vr.data !== rowData && isCheckedIn(vr.data, currentGId)
              );
            }
            if (!anyOtherCheckedIn) {
              gridInstanceRef.value.columnOption(colName, 'width', 100);
              gridInstanceRef.value.columnOption(colName, 'minWidth', 100);
            }
          }
        }

        DevExpress.ui.notify(newCategory !== 1 ? 'Checked in successfully' : 'Check-in undone', 'success', 2000);
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', WARNING_NOTIFY_TIME);
      } finally {
        if (window.Attendees && window.Attendees.utilities) {
          window.Attendees.utilities.editingEnabled = false;
        }
      }
    };

    const toggleAttendance = async (rowData, gathering, domElements, rowIndex, colName) => {
      const gatheringMeta = (gathering && typeof gathering === 'object') ? gathering : null;
      let gatheringId = gatheringMeta ? gatheringMeta.id : gathering;
      let record = getAttendanceRecord(rowData, gatheringId);
      const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);
      const meetId = (gatheringMeta && gatheringMeta.meet_id) || (gathering && gathering.meet_id) || null;
      const signatureRequiredAt = getMeetSignatureRequiredAt(meetId);

      if (!isCurrentlyCheckedIn) {
        // Checking in!
        if (signatureRequiredAt === 'check_in') {
          const attendeeName = rowData.attendee_name || 'Attendee';
          await openSignaturePopup({
            title: `Checking in ${attendeeName}`,
            onSign: async (encodedFile) => {
              await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, 9, encodedFile, false);
            }
          });
        } else {
          await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, 9, null, false);
        }
      } else {
        // Undoing check in!
        const hasSignature = !!(record && (record.file_path || record.file));
        const needsConfirm = (signatureRequiredAt === 'check_in') || hasSignature;

        if (needsConfirm) {
          const attendeeName = rowData.attendee_name || 'Attendee';
          let fileImgTag = '';
          const filePath = record ? (record.file_path || record.file) : null;
          if (filePath) {
            const fullUrl = (filePath.startsWith('http') || filePath.startsWith('/')) ? filePath : `/media/${filePath}`;
            fileImgTag = `<br><div style="text-align: center; margin-top: 10px;"><img style="max-width: 100%; max-height: 120px; border: 1px solid #dee2e6; border-radius: 4px;" src="${fullUrl}" alt="Signature"></div>`;
          }
          const resultPromise = DevExpress.ui.dialog.confirm(
            `<strong>Clear check-in record of ${attendeeName} and REMOVE signature?</strong>${fileImgTag}`,
            "UNDO check-in record?"
          );
          resultPromise.done(async (dialogResult) => {
            if (dialogResult) {
              await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, 1, null, true);
            }
          });
        } else {
          await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, 1, null, false);
        }
      }
    };

    let signaturePopupInstance = null;
    let signaturePadInstance = null;
    let currentSignatureCallback = null;

    const ensureSignaturePadLoaded = () => {
      if (typeof SignaturePad !== 'undefined') {
        return Promise.resolve();
      }
      return new Promise((resolve, reject) => {
        const existingScript = document.querySelector('script[src*="signature_pad"]');
        if (existingScript) {
          if (typeof SignaturePad !== 'undefined') return resolve();
          existingScript.addEventListener('load', () => resolve());
          existingScript.addEventListener('error', () => reject(new Error('Failed to load SignaturePad')));
        } else {
          const script = document.createElement('script');
          script.src = 'https://cdn.jsdelivr.net/npm/signature_pad@4.0.9/dist/signature_pad.umd.min.js';
          script.onload = () => resolve();
          script.onerror = () => reject(new Error('Failed to load SignaturePad'));
          document.head.appendChild(script);
        }
      });
    };

    const updateGridRowAttendance = (rowData, gatheringId, normalizedRecord, rowIndex) => {
      if (!gridInstanceRef.value) return;
      const rowKey = rowData.attendee_id || rowData.attending_id;
      let rIndex = (typeof rowIndex === 'number' && rowIndex >= 0) ? rowIndex : -1;
      if (rIndex < 0 && rowKey !== undefined) {
        rIndex = gridInstanceRef.value.getRowIndexByKey(rowKey);
      }
      if (rIndex >= 0) {
        const visibleRows = typeof gridInstanceRef.value.getVisibleRows === 'function' ? gridInstanceRef.value.getVisibleRows() : null;
        if (visibleRows && visibleRows[rIndex] && visibleRows[rIndex].data) {
          const gridRowData = visibleRows[rIndex].data;
          if (!gridRowData.attendances) gridRowData.attendances = [];
          const existingRec = gridRowData.attendances.find(a => a && String(a.gathering_id) === String(gatheringId));
          if (existingRec) {
            Object.assign(existingRec, normalizedRecord);
          } else {
            gridRowData.attendances.push(normalizedRecord);
          }
        }
      }
    };

    const initSignatureCanvas = () => {
      const canvas = document.querySelector('canvas.signature');
      if (canvas && typeof SignaturePad !== 'undefined') {
        canvas.style.width = '100%';
        canvas.style.height = '100px';
        const width = canvas.offsetWidth || 378;
        const height = canvas.offsetHeight || 100;
        canvas.width = width;
        canvas.height = height;

        if (signaturePadInstance) {
          try { signaturePadInstance.off(); } catch (e) {}
        }
        signaturePadInstance = new SignaturePad(canvas, {
          maxWidth: 2,
          backgroundColor: 'rgb(255,255,255)',
        });
        signaturePadInstance.clear();
      } else {
        console.warn('[Rosters] Signature canvas or SignaturePad not found!', { canvas, hasSignaturePad: typeof SignaturePad !== 'undefined' });
      }
    };

    const getSignaturePopup = () => {
      if (signaturePopupInstance) return signaturePopupInstance;

      let popupEl = document.getElementById('signature-canvas-popup');
      if (!popupEl) {
        popupEl = document.createElement('div');
        popupEl.id = 'signature-canvas-popup';
        const container = document.querySelector('.rosters-container') || document.body;
        container.appendChild(popupEl);
      }

      signaturePopupInstance = $(popupEl).dxPopup({
        visible: false,
        contentTemplate: () => {
          const t = document.getElementById('signature-popup-template');
          if (t && t.content && t.content.firstElementChild) {
            return $(t.content.firstElementChild.cloneNode(true));
          }
          return $('<div style="width: 100%; height: 100px;"><canvas class="signature" style="width: 100%; height: 100px;"></canvas></div>');
        },
        maxWidth: 400,
        width: '95%',
        height: 200,
        container: '.rosters-container',
        showTitle: true,
        title: 'Sign here',
        dragEnabled: false,
        hideOnOutsideClick: false,
        showCloseButton: false,
        position: {
          at: 'center',
          my: 'center',
        },
        onShown: () => {
          if (window.Attendees && window.Attendees.utilities) {
            window.Attendees.utilities.editingEnabled = true;
          }
          const canvas = document.querySelector('canvas.signature');
          if (canvas && (!signaturePadInstance || canvas.width === 0 || canvas.height === 0)) {
            initSignatureCanvas();
          }
        },
        onHiding: () => {
          if (window.Attendees && window.Attendees.utilities) {
            window.Attendees.utilities.editingEnabled = false;
          }
        },
        toolbarItems: [
          {
            widget: 'dxButton',
            toolbar: 'bottom',
            location: 'before',
            options: {
              icon: 'edit',
              text: 'Sign',
              type: 'default',
              onClick: async () => {
                if (signaturePadInstance && !signaturePadInstance.isEmpty()) {
                  const encodedFile = signaturePadInstance.toDataURL('image/jpeg', 0.5);
                  signaturePopupInstance.hide();
                  const cb = currentSignatureCallback;
                  currentSignatureCallback = null;
                  if (cb) {
                    await cb(encodedFile);
                  }
                  if (signaturePadInstance) signaturePadInstance.clear();
                } else {
                  DevExpress.ui.notify({
                    message: 'Signing requires signature!',
                    position: {
                      my: 'center',
                      at: 'center',
                      of: window,
                    },
                  }, 'error', WARNING_NOTIFY_TIME);
                }
              },
            },
          },
          {
            widget: 'dxButton',
            toolbar: 'bottom',
            location: 'after',
            options: {
              icon: 'clear',
              text: 'Clear signing',
              stylingMode: 'outlined',
              onClick: () => {
                if (signaturePadInstance) {
                  signaturePadInstance.clear();
                }
              },
            },
          },
          {
            widget: 'dxButton',
            toolbar: 'bottom',
            location: 'after',
            options: {
              text: 'Cancel',
              stylingMode: 'text',
              onClick: () => {
                signaturePopupInstance.hide();
                if (signaturePadInstance) {
                  signaturePadInstance.clear();
                }
                currentSignatureCallback = null;
              },
            },
          },
        ],
      }).dxPopup('instance');

      return signaturePopupInstance;
    };

    const openSignaturePopup = async ({ title, onSign }) => {
      try {
        await ensureSignaturePadLoaded();
        const popup = getSignaturePopup();
        popup.option('title', title || 'Sign here');
        currentSignatureCallback = onSign;
        popup.show();
        initSignatureCanvas();
      } catch (e) {
        DevExpress.ui.notify(e.message, 'error', WARNING_NOTIFY_TIME);
      }
    };

    const executeCheckOut = async (rowData, record, domElements, rowIndex, newFinish, encodedFile, clearFile) => {
      try {
        const recordId = record.attendance_id || record.id;
        const payload = {
          finish: newFinish,
        };
        if (encodedFile !== undefined && encodedFile !== null) {
          payload.encoded_file = encodedFile;
        }
        if (clearFile) {
          payload.file = null;
        }

        const response = await fetch(`${endpoints.attendances}${recordId}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || errData.error || (newFinish ? 'Failed to check out' : 'Failed to undo check out'));
        }
        const updatedRecord = await response.json();

        const normalizedRecord = {
          attendance_id: updatedRecord.id,
          gathering_id: updatedRecord.gathering,
          category_id: updatedRecord.category,
          start: updatedRecord.start,
          finish: updatedRecord.finish,
          file_path: clearFile ? null : (updatedRecord.file_path || record.file_path || null),
          file: clearFile ? null : (updatedRecord.file_path || record.file || null)
        };

        Object.assign(record, normalizedRecord);

        if (domElements && domElements.outBtn) {
          if (newFinish) {
            domElements.outBtn.className = 'roster-btn roster-btn-out checked-out';
            domElements.outBtn.innerText = 'Checked Out';
          } else {
            domElements.outBtn.className = 'roster-btn roster-btn-out';
            domElements.outBtn.innerText = 'Out';
          }
        }

        updateGridRowAttendance(rowData, updatedRecord.gathering, normalizedRecord, rowIndex);
        DevExpress.ui.notify(newFinish ? 'Checked out successfully' : 'Check-out undone', newFinish ? 'success' : 'info', 2000);
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', WARNING_NOTIFY_TIME);
      }
    };

    const markOut = async (rowData, gathering, domElements, rowIndex) => {
      const gatheringMeta = (gathering && typeof gathering === 'object') ? gathering : null;
      const gatheringId = gatheringMeta ? gatheringMeta.id : gathering;
      const record = getAttendanceRecord(rowData, gatheringId);
      if (!record) return;

      const isCurrentlyCheckedOut = !!record.finish;
      const meetId = (gatheringMeta && gatheringMeta.meet_id) || (gathering && gathering.meet_id) || null;
      const signatureRequiredAt = getMeetSignatureRequiredAt(meetId);

      if (!isCurrentlyCheckedOut) {
        // Checking out!
        if (signatureRequiredAt === 'check_out') {
          const attendeeName = rowData.attendee_name || 'Attendee';
          await openSignaturePopup({
            title: `Checking out ${attendeeName}`,
            onSign: async (encodedFile) => {
              const nowIso = new Date().toISOString();
              await executeCheckOut(rowData, record, domElements, rowIndex, nowIso, encodedFile, false);
            }
          });
        } else {
          const nowIso = new Date().toISOString();
          await executeCheckOut(rowData, record, domElements, rowIndex, nowIso, null, false);
        }
      } else {
        // Undoing check out!
        const hasSignature = !!(record && (record.file_path || record.file));
        const needsConfirm = (signatureRequiredAt === 'check_out') || (hasSignature && signatureRequiredAt !== 'check_in');

        if (needsConfirm) {
          const attendeeName = rowData.attendee_name || 'Attendee';
          let fileImgTag = '';
          const filePath = record ? (record.file_path || record.file) : null;
          if (filePath) {
            const fullUrl = (filePath.startsWith('http') || filePath.startsWith('/')) ? filePath : `/media/${filePath}`;
            fileImgTag = `<br><div style="text-align: center; margin-top: 10px;"><img style="max-width: 100%; max-height: 120px; border: 1px solid #dee2e6; border-radius: 4px;" src="${fullUrl}" alt="Signature"></div>`;
          }

          const resultPromise = DevExpress.ui.dialog.confirm(
            `<strong>Clear the time-out record of ${attendeeName} and REMOVE signature?</strong>${fileImgTag}`,
            "UNDO check-out record?"
          );

          resultPromise.done(async (dialogResult) => {
            if (dialogResult) {
              await executeCheckOut(rowData, record, domElements, rowIndex, null, null, true);
            }
          });
        } else {
          await executeCheckOut(rowData, record, domElements, rowIndex, null, null, false);
        }
      }
    };

    return {
      getAttendingMeetStatus,
      isAttendingValid,
      isCheckedIn,
      isCheckedOut,
      toggleAttendance,
      markOut,
      initSignaturePopup: getSignaturePopup,
      initCheckOutPopup: getSignaturePopup
    };
  }

  // ==========================================================
  // 3. AttendingMeets Editor Logic (dxPopup & dxForm)
  // ==========================================================
  function useAttendingMeetsEditor(endpoints, gridInstanceRef, filterData) {
    let popupInstance = null;
    let popupElement = null;
    let currentAttendeeData = null;
    let currentSortedMeets = [];
    let currentFormInstances = [];
    let currentActiveIndex = 0;

    const lookupsCache = {
      loaded: false,
      loadingPromise: null,
      meets: [],
      characters: [],
      categories: [],
      teams: [],
      meetNames: {},
      attendings: new Map()
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

          lookupsCache.meets = meetsRes.data || meetsRes.results || meetsRes || [];
          lookupsCache.characters = charsRes.data || charsRes.results || charsRes || [];
          lookupsCache.categories = catsRes.data || catsRes.results || catsRes || [];
          lookupsCache.teams = teamsRes.data || teamsRes.results || teamsRes || [];

          lookupsCache.meets.forEach(m => {
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

    const getSelectedAssemblies = () => {
      const selectedSlugsOrIds = new Set(filterData && filterData.meets ? filterData.meets : []);
      const assemblies = new Set();
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

    const getSelectedMeetIds = () => {
      const selectedSlugsOrIds = new Set(filterData && filterData.meets ? filterData.meets : []);
      const allowedIds = new Set();
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

    const saveCurrentForm = async () => {
      if (!currentSortedMeets.length || !currentAttendeeData) return;
      const form = currentFormInstances[currentActiveIndex];
      if (!form) return;

      const validation = form.validate();
      if (!validation.isValid) {
        DevExpress.ui.notify('Please check required fields', 'warning', WARNING_NOTIFY_TIME);
        return;
      }

      const formData = form.option('formData');
      const targetAm = currentSortedMeets[currentActiveIndex];

      const payload = {
        meet: formData.meet,
        attending: formData.attending,
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
        const updateRes = await fetch(`${endpoints.attendingmeets}${targetAm.id}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'X-Target-Attendee-Id': String(currentAttendeeData.attendee_id)
          },
          body: JSON.stringify(payload)
        });

        if (!updateRes.ok) {
          const errData = await updateRes.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to update attendingmeet');
        }

        DevExpress.ui.notify(
          {
            message: 'Update attendingmeet success',
            position: { my: 'center', at: 'center', of: window }
          },
          'success',
          2000
        );

        if (popupInstance) popupInstance.hide();
        if (gridInstanceRef && gridInstanceRef.value) {
          gridInstanceRef.value.refresh();
        }
      } catch (saveErr) {
        DevExpress.ui.notify(`Save failed: ${saveErr.message}`, 'error', WARNING_NOTIFY_TIME);
      }
    };

    const createFormConfig = (am) => {
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
          },
          {
            dataField: 'team',
            editorType: 'dxSelectBox',
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

    const renderPopupContent = (container) => {
      container.innerHTML = '';

      if (!currentSortedMeets.length) {
        container.innerHTML = `
          <div class="alert alert-info" style="margin-top: 15px;">No enrollments (attendingmeets) found for this attendee under the selected meet(s).</div>
        `;
        return;
      }

      // Content Area: Single Form or TabPanel for multiple attendingmeets
      const contentArea = document.createElement('div');
      contentArea.className = 'attendingmeets-content-area';
      container.appendChild(contentArea);

      currentFormInstances = [];
      currentActiveIndex = 0;

      if (currentSortedMeets.length === 1) {
        const formEl = document.createElement('div');
        contentArea.appendChild(formEl);
        const formInst = new DevExpress.ui.dxForm(formEl, createFormConfig(currentSortedMeets[0]));
        currentFormInstances.push(formInst);
      } else {
        // Multiple attendingmeets -> dxTabPanel
        const tabItems = currentSortedMeets.map((am, i) => {
          const meetName = lookupsCache.meetNames[am.meet] || am.meet__display_name || `Meet #${am.meet}`;
          const finishLabel = am.finish ? am.finish.substring(0, 10) : 'Ongoing';
          return {
            title: `${meetName} (${finishLabel})`,
            am: am,
            index: i
          };
        });

        new DevExpress.ui.dxTabPanel(contentArea, {
          dataSource: tabItems,
          width: '100%',
          selectedIndex: 0,
          deferRendering: false,
          loop: false,
          animationEnabled: true,
          swipeEnabled: false,
          onSelectionChanged: (e) => {
            currentActiveIndex = e.component.option('selectedIndex');
          },
          itemTemplate: (itemData, itemIndex, itemElement) => {
            const formEl = document.createElement('div');
            itemElement.append(formEl);
            const formInst = new DevExpress.ui.dxForm(formEl, createFormConfig(itemData.am));
            currentFormInstances[itemIndex] = formInst;
          }
        });
      }
    };

    const openAttendingMeetsPopup = async (attendeeData) => {
      currentAttendeeData = attendeeData;
      if (!popupElement) {
        popupElement = document.createElement('div');
        popupElement.id = 'attendingmeets-editor-popup';
        document.body.appendChild(popupElement);
      }

      await preloadLookups();

      const allowedMeetIds = getSelectedMeetIds();
      let rawMeets = [];
      try {
        const res = await fetch(endpoints.attendingmeets, {
          headers: {
            'X-Target-Attendee-Id': String(attendeeData.attendee_id),
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          }
        });
        if (!res.ok) throw new Error('Failed to load attendee enrollments');
        const json = await res.json();
        rawMeets = json.data || [];
      } catch (err) {
        DevExpress.ui.notify(`Error loading enrollments: ${err.message}`, 'error', WARNING_NOTIFY_TIME);
        return;
      }

      // Filter: only keep attendingmeets matching the currently selected meets on the page
      const matchedMeets = rawMeets.filter(am => allowedMeetIds.has(am.meet));

      // Sort by finish descending (ongoing/null finish first, then newest to oldest)
      currentSortedMeets = matchedMeets.slice().sort((a, b) => {
        if (!a.finish && !b.finish) return 0;
        if (!a.finish) return -1;
        if (!b.finish) return 1;
        return new Date(b.finish) - new Date(a.finish);
      });

      const isMobile = window.innerWidth < 768;
      const popupWidth = isMobile ? '92%' : '70%';
      const popupHeight = isMobile ? 'auto' : '70%';
      const popupTitle = `${attendeeData.attendee_name} enrollment`;

      const toolbarItems = [
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
        },
        {
          toolbar: 'top',
          location: 'after',
          widget: 'dxButton',
          options: {
            text: 'Cancel',
            icon: 'close',
            stylingMode: 'outlined',
            onClick: () => popupInstance.hide()
          }
        }
      ];

      if (!popupInstance) {
        popupInstance = new DevExpress.ui.dxPopup(popupElement, {
          title: popupTitle,
          fullScreen: false,
          wrapperAttr: {
            class: 'attendingmeets-popup-wrapper'
          },
          showCloseButton: true,
          dragEnabled: !isMobile,
          toolbarItems: toolbarItems,
          onShowing: () => {
            if (window.Attendees && window.Attendees.utilities) {
              window.Attendees.utilities.editingEnabled = true;
            }
          },
          onHiding: () => {
            if (window.Attendees && window.Attendees.utilities) {
              window.Attendees.utilities.editingEnabled = false;
            }
          },
          contentTemplate: (container) => {
            renderPopupContent(container[0]);
          }
        });
      } else {
        popupInstance.option({
          title: popupTitle,
          fullScreen: false,
          wrapperAttr: {
            class: 'attendingmeets-popup-wrapper'
          },
          dragEnabled: !isMobile,
          toolbarItems: toolbarItems,
          onShowing: () => {
            if (window.Attendees && window.Attendees.utilities) {
              window.Attendees.utilities.editingEnabled = true;
            }
          },
          onHiding: () => {
            if (window.Attendees && window.Attendees.utilities) {
              window.Attendees.utilities.editingEnabled = false;
            }
          }
        });
        const contentEl = popupInstance.content ? popupInstance.content()[0] : null;
        if (contentEl) {
          renderPopupContent(contentEl);
        }
      }

      popupInstance.show();
    };

    return { openAttendingMeetsPopup, preloadLookups };
  }

  // ==========================================================
  // 4. Grid View Logic
  // ==========================================================
  function useRosterGrid(endpoints, filterData, gridInstanceRef, attendanceLogic, attendingMeetsEditor, onResetCallback) {
    const formatDate = (dateString) => {
      if (!dateString) return '';
      const d = new Date(dateString);
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    };

    const getColumnCaption = (gathering) => {
      const timeStr = formatDate(gathering.start);
      const isMultiMeet = filterData && filterData.meets && filterData.meets.length > 1;
      if (isMultiMeet) {
        const meetName = gathering.meet_display_name
          || (gathering.meet_id && meetsInfoMap.get(gathering.meet_id))
          || (gathering.meet_id && meetsInfoMap.get(String(gathering.meet_id)))
          || '';
        if (meetName) {
          return `${meetName}\n${timeStr}`;
        }
      }
      return timeStr;
    };

    let activeHighlightedIndex = null;
    let lastHighlightedGathering = null;
    let highlightStyleEl = null;

    const getHighlightStyleEl = () => {
      if (!highlightStyleEl) {
        highlightStyleEl = document.getElementById('roster-column-highlight-style');
        if (!highlightStyleEl) {
          highlightStyleEl = document.createElement('style');
          highlightStyleEl.id = 'roster-column-highlight-style';
          document.head.appendChild(highlightStyleEl);
        }
      }
      return highlightStyleEl;
    };

    const highlightColumn = (colIndex, gatheringMeta) => {
      if (colIndex === undefined || colIndex === null) return;
      lastHighlightedGathering = gatheringMeta || null;
      if (activeHighlightedIndex === colIndex) {
        return;
      }
      activeHighlightedIndex = colIndex;
      const styleTag = getHighlightStyleEl();
      styleTag.textContent = `
        #rosters-datagrid-container .dx-datagrid-headers .roster-col-idx-${colIndex} {
          background-color: #cfe2ff;
        }
        #rosters-datagrid-container .dx-datagrid-rowsview .dx-data-row > td.roster-col-idx-${colIndex} {
          background-color: rgba(13, 110, 253, 0.08);
        }
        #rosters-datagrid-container .dx-datagrid-rowsview .dx-data-row.dx-row-alt > td.roster-col-idx-${colIndex} {
          background-color: rgba(13, 110, 253, 0.16);
        }
        #rosters-datagrid-container .dx-datagrid-rowsview .dx-data-row.dx-state-hover > td.roster-col-idx-${colIndex} {
          background-color: rgba(13, 110, 253, 0.22);
        }
        #rosters-datagrid-container .dx-datagrid-rowsview .dx-data-row.dx-selection > td.roster-col-idx-${colIndex} {
          background-color: #a3e0c0;
        }
      `;
    };

    const clearColumnHighlight = () => {
      if (activeHighlightedIndex === null) return;
      activeHighlightedIndex = null;
      lastHighlightedGathering = null;
      const styleTag = getHighlightStyleEl();
      styleTag.textContent = '';
    };

    const highlightGatheringColumn = (gatheringId) => {
      if (!gatheringId || !gridInstanceRef.value) return;
      const columns = gridInstanceRef.value.option('columns') || [];
      const col = columns.find(c => c.gatheringMeta && (String(c.gatheringMeta.id) === String(gatheringId)));
      if (col && col.colIndex !== undefined) {
        highlightColumn(col.colIndex, col.gatheringMeta);
      }
    };

    document.addEventListener('click', (e) => {
      if (activeHighlightedIndex === null) return;
      const gridContainer = document.getElementById('rosters-datagrid-container');
      if (gridContainer && !gridContainer.contains(e.target) && !e.target.closest('.dx-overlay-content') && !e.target.closest('.add-attendee') && !e.target.closest('a.add-attendee')) {
        clearColumnHighlight();
      }
    });

    const gatheringHeaderTemplate = (container, options) => {
      const colMeta = options.column.gatheringMeta || (options.column.name && gatheringsRegistry.get(options.column.name));
      const colIdx = options.column.colIndex !== undefined ? options.column.colIndex : (options.columnIndex - 5);
      const isMultiMeet = filterData && filterData.meets && filterData.meets.length > 1;
      const meetName = (colMeta && colMeta.meet_display_name)
        || (colMeta && colMeta.meet_id && meetsInfoMap.get(colMeta.meet_id))
        || (colMeta && colMeta.meet_id && meetsInfoMap.get(String(colMeta.meet_id)))
        || '';
      const timeStr = formatDate(colMeta ? colMeta.start : '');

      const wrapper = document.createElement('div');
      wrapper.className = 'text-center roster-header-cell';
      wrapper.style.cursor = 'pointer';
      if (isMultiMeet && meetName) {
        wrapper.innerHTML = `<div class="roster-header-meet">${meetName}</div><div class="roster-header-time">${timeStr}</div>`;
      } else {
        wrapper.innerHTML = `<div class="roster-header-time single">${timeStr}</div>`;
      }

      wrapper.addEventListener('click', () => {
        highlightColumn(colIdx, colMeta);
      });

      if (container.jquery) {
        container.empty().append(wrapper);
      } else if (container.length !== undefined && !container.nodeType) {
        const el = container[0];
        if (el) {
          el.innerHTML = '';
          el.appendChild(wrapper);
        }
      } else if (container.innerHTML !== undefined) {
        container.innerHTML = '';
        container.appendChild(wrapper);
      } else if (container.append) {
        container.append(wrapper);
      }
    };


    const attendeeCellTemplate = (container, options) => {
      const data = options.data;
      const wrapper = document.createElement('div');
      wrapper.className = 'attendee-info';

      let photoHtml = '';
      if (filterData.showPhotos && data.photo_url) {
        photoHtml = `<img src="${data.photo_url}" class="attendee-photo" alt="Photo">`;
      } else if (filterData.showPhotos) {
        photoHtml = `<div class="attendee-photo d-flex justify-content-center align-items-center bg-light text-muted"><i class="fas fa-user"></i></div>`;
      }

      const hasSpecialWarning = (data.attendingmeets || []).some(am => am && am.infos && am.infos.special && am.infos.special.check_in);
      let warningHtml = '';
      if (hasSpecialWarning) {
        const specialAm = (data.attendingmeets || []).find(am => am && am.infos && am.infos.special && am.infos.special.check_in);
        const warningMsg = (specialAm && specialAm.infos && specialAm.infos.special && specialAm.infos.special.check_in) || '⚠Missing companion info';
        warningHtml = `<span class="text-danger fw-bold me-1" title="${warningMsg}" style="font-size: 1.1em; cursor: help;">⚠</span>`;
      }

      wrapper.innerHTML = `
        ${photoHtml}
        <span class="attendee-links-container">
          ${warningHtml}<u><a href="/persons/attendee/${data.attendee_id}" target="_blank" class="attendee-info-link" title="Click to open a new page of attendee info">(Info)</a></u>
          <u class="attendee-name-link" role="button" title="Click to edit enrollment details">${data.attendee_name}</u>
        </span>
      `;

      wrapper.querySelector('.attendee-name-link').addEventListener('click', (e) => {
        e.preventDefault();
        if (attendingMeetsEditor) {
          attendingMeetsEditor.openAttendingMeetsPopup(data);
        }
      });

      container.append(wrapper);
    };

    const meetTeamsCache = {};
    const loadTeamsForMeet = async (meetId) => {
      if (meetTeamsCache[meetId]) return meetTeamsCache[meetId];
      try {
        const res = await fetch(`${endpoints.teams}?meets[]=${meetId}`);
        if (!res.ok) throw new Error('Failed to fetch teams');
        const data = await res.json();
        const list = (data.data || data.results || data || []).map(t => ({ id: t.id, display_name: t.display_name }));
        list.unshift({ id: null, display_name: '(None)' });
        meetTeamsCache[meetId] = list;
        return list;
      } catch (err) {
        console.error('Failed to load teams for meet', meetId, err);
        return [{ id: null, display_name: '(None)' }];
      }
    };

    const meetCharactersCache = {};
    const loadCharactersForMeet = async (meetId) => {
      if (meetCharactersCache[meetId]) return meetCharactersCache[meetId];
      try {
        const res = await fetch(`${endpoints.characters}?meetIds[]=${meetId}`);
        if (!res.ok) throw new Error('Failed to fetch characters');
        const data = await res.json();
        const list = (data.data || data.results || data || []).map(c => ({ id: c.id, display_name: c.display_name }));
        meetCharactersCache[meetId] = list;
        return list;
      } catch (err) {
        console.error('Failed to load characters for meet', meetId, err);
        return [];
      }
    };

    const renderInlineEditableLine = (lineContainer, field, am, rowData, isMultiMeet) => {
      lineContainer.innerHTML = '';
      if (isMultiMeet && am.meet_name) {
        const meetLabel = document.createElement('span');
        meetLabel.className = 'roster-meet-label';
        meetLabel.innerText = `${am.meet_name}:`;
        lineContainer.appendChild(meetLabel);
      }

      const valSpan = document.createElement('span');
      const curValName = field === 'team' ? am.team_name : am.character_name;
      if (curValName) {
        valSpan.innerText = curValName;
      } else {
        valSpan.innerText = '(None)';
        valSpan.classList.add('empty-val');
      }

      if (endpoints.userCanWrite) {
        valSpan.className += ' roster-editable-val';
        let isEditing = false;
        valSpan.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (isEditing) return;
          isEditing = true;

          const editorContainer = document.createElement('div');
          editorContainer.className = 'roster-inline-editor-container';

          valSpan.style.display = 'none';
          lineContainer.appendChild(editorContainer);

          const currentId = field === 'team' ? am.team_id : am.character_id;
          const dataSource = field === 'team'
            ? await loadTeamsForMeet(am.meet_id)
            : await loadCharactersForMeet(am.meet_id);

          let selectBoxInstance = null;
          let changeHandled = false;

          const cleanup = () => {
            if (selectBoxInstance) {
              try {
                selectBoxInstance.dispose();
              } catch (ignore) {}
              selectBoxInstance = null;
            }
            if (editorContainer.parentNode) {
              editorContainer.parentNode.removeChild(editorContainer);
            }
            valSpan.style.display = '';
            isEditing = false;
          };

          selectBoxInstance = new DevExpress.ui.dxSelectBox(editorContainer, {
            dataSource: dataSource,
            valueExpr: 'id',
            displayExpr: 'display_name',
            value: currentId || null,
            searchEnabled: true,
            width: '100%',
            dropDownOptions: {
              minWidth: 150,
            },
            onValueChanged: async (event) => {
              if (event.value === currentId) {
                cleanup();
                return;
              }
              changeHandled = true;
              try {
                const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                const payload = {};
                payload[field] = event.value;

                const baseEndpoint = (endpoints.attendingmeets || '').endsWith('/')
                  ? endpoints.attendingmeets
                  : `${endpoints.attendingmeets}/`;
                const patchUrl = `${baseEndpoint}${am.attendingmeet_id}/`;

                const response = await fetch(patchUrl, {
                  method: 'PATCH',
                  headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                    'X-Target-Attendee-Id': rowData.attendee_id,
                  },
                  body: JSON.stringify(payload)
                });

              if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.detail || errJson.error || 'Failed to update ' + field);
              }

              const selectedObj = dataSource.find(item => item.id === event.value);
              const newDisplayName = selectedObj ? selectedObj.display_name : (event.value ? String(event.value) : null);

              if (field === 'team') {
                am.team_id = event.value;
                am.team_name = (newDisplayName === '(None)') ? null : newDisplayName;
                rowData.team__display_name = (rowData.attendingmeets || [])
                  .map(a => a.team_name)
                  .filter(Boolean)
                  .join(', ');
              } else {
                am.character_id = event.value;
                am.character_name = newDisplayName;
                rowData.character__display_name = (rowData.attendingmeets || [])
                  .map(a => a.character_name)
                  .filter(Boolean)
                  .join(', ');
              }

              DevExpress.ui.notify(`${field === 'team' ? 'Team' : 'Character'} updated successfully`, 'success', 2000);
            } catch (err) {
              console.error('Error patching ' + field, err);
              DevExpress.ui.notify('Update failed: ' + err.message, 'error', WARNING_NOTIFY_TIME);
            } finally {
              cleanup();
              renderInlineEditableLine(lineContainer, field, am, rowData, isMultiMeet);
            }
          },
          onClosed: () => {
            setTimeout(() => {
              if (!changeHandled && isEditing) {
                cleanup();
              }
            }, 100);
          }
        });

        setTimeout(() => {
          if (selectBoxInstance) {
            selectBoxInstance.open();
          }
        }, 50);
      });
      }

      lineContainer.appendChild(valSpan);
    };

    const teamCellTemplate = (container, options) => {
      const data = options.data;
      if (!data) return;
      const ams = data.attendingmeets && data.attendingmeets.length ? data.attendingmeets : [];
      const isMultiMeet = filterData.meets && filterData.meets.length > 1;

      if (!ams.length) {
        container.innerHTML = `<span class="text-muted fst-italic">(None)</span>`;
        return;
      }

      const linesWrapper = document.createElement('div');
      linesWrapper.className = 'roster-cell-lines';

      ams.forEach(am => {
        const line = document.createElement('div');
        line.className = 'roster-inline-line';
        renderInlineEditableLine(line, 'team', am, data, isMultiMeet);
        linesWrapper.appendChild(line);
      });

      container.append(linesWrapper);
    };

    const characterCellTemplate = (container, options) => {
      const data = options.data;
      if (!data) return;
      const ams = data.attendingmeets && data.attendingmeets.length ? data.attendingmeets : [];
      const isMultiMeet = filterData.meets && filterData.meets.length > 1;

      if (!ams.length) {
        container.innerHTML = `<span class="text-muted fst-italic">(None)</span>`;
        return;
      }

      const linesWrapper = document.createElement('div');
      linesWrapper.className = 'roster-cell-lines';

      ams.forEach(am => {
        const line = document.createElement('div');
        line.className = 'roster-inline-line';
        renderInlineEditableLine(line, 'character', am, data, isMultiMeet);
        linesWrapper.appendChild(line);
      });

      container.append(linesWrapper);
    };

    const attendanceCellTemplate = (container, options) => {
      const data = options.data;
      const colName = options.column.name;
      const colIdx = options.column.colIndex !== undefined ? options.column.colIndex : (options.columnIndex - 5);
      const colMeta = options.column.gatheringMeta;
      const meetStartKey = (colMeta && colMeta.meet_id && colMeta.start) ? `${colMeta.meet_id}_${colMeta.start}` : '';
      const gatheringMeta = gatheringsRegistry.get(colName) || (meetStartKey && gatheringsRegistry.get(meetStartKey)) || colMeta;
      
      const wrapper = document.createElement('div');
      wrapper.className = 'text-center roster-cell-wrapper';

      const status = attendanceLogic.getAttendingMeetStatus(data, gatheringMeta);
      if (status === 'not_attending') {
        wrapper.innerHTML = `<span class="not-attending-text">Not Attending</span>`;
        container.append(wrapper);
        return;
      }

      const gatheringId = gatheringMeta && gatheringMeta.id;
      const checkedIn = gatheringId ? attendanceLogic.isCheckedIn(data, gatheringId) : false;
      const checkedOut = gatheringId ? attendanceLogic.isCheckedOut(data, gatheringId) : false;

      const checkInBtn = document.createElement('button');
      if (checkedIn) {
        checkInBtn.className = 'roster-btn checked-in';
        checkInBtn.innerText = 'Checked In';
      } else if (status === 'expired') {
        checkInBtn.className = 'roster-btn roster-btn-normal';
        checkInBtn.innerText = 'Check In';
      } else {
        checkInBtn.className = 'roster-btn';
        checkInBtn.innerText = 'Check In';
      }


      const outBtn = document.createElement('button');
      outBtn.className = `roster-btn roster-btn-out ${checkedOut ? 'checked-out' : ''}`;
      outBtn.innerText = checkedOut ? 'Checked Out' : 'Out';
      if (!checkedIn) {
        outBtn.style.display = 'none';
      }

      const domElements = { wrapper, checkInBtn, outBtn };

      checkInBtn.addEventListener('click', () => {
        highlightColumn(colIdx, gatheringMeta);
        attendanceLogic.toggleAttendance(data, gatheringMeta, domElements, options.rowIndex, colName);
      });

      outBtn.addEventListener('click', () => {
        highlightColumn(colIdx, gatheringMeta);
        attendanceLogic.markOut(data, gatheringMeta, domElements, options.rowIndex);
      });

      wrapper.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
          highlightColumn(colIdx, gatheringMeta);
        }
      });

      wrapper.appendChild(checkInBtn);
      wrapper.appendChild(outBtn);
      container.append(wrapper);
    };

    const updateGridColumns = (serverColumns, rows = []) => {
      const currentCols = gridInstanceRef.value.option('columns');
      let colsChanged = false;
      
      const FIXED_PREFIX_COUNT = 5;
      const TOTAL_EXTRA_COLS = FIXED_PREFIX_COUNT + 1; // plus 1 dummy-column

      if (!currentCols || currentCols.length !== serverColumns.length + TOTAL_EXTRA_COLS) {
        colsChanged = true;
      } else {
        for (let i = 0; i < serverColumns.length; i++) {
          const col = currentCols[i + FIXED_PREFIX_COUNT];
          const registered = registerGathering(serverColumns[i]);
          if (col.name !== getColumnIdentifier(registered) || col.caption !== getColumnCaption(registered)) {
            colsChanged = true;
            break;
          }
        }
      }

      if (colsChanged) {
        clearColumnHighlight();
        const columns = [
          {
            dataField: 'attendee_name',
            caption: 'Attendee',
            fixed: true,
            fixedPosition: 'left',
            width: 200,
            cellTemplate: attendeeCellTemplate,
            allowSorting: true,
            allowHiding: false
          },
          {
            dataField: 'team__display_name',
            caption: 'Team',
            fixed: true,
            fixedPosition: 'left',
            width: 80,
            cellTemplate: teamCellTemplate,
            allowSorting: true,
            allowHiding: true
          },
          {
            dataField: 'character__display_name',
            caption: 'Character',
            visible: false,
            allowHiding: true,
            fixed: true,
            fixedPosition: 'left',
            width: 140,
            cellTemplate: characterCellTemplate,
            allowSorting: true
          },
          {
            dataField: 'contacts',
            caption: 'Contacts',
            visible: false,
            allowHiding: true,
            allowSorting: false,
            width: 180
          },
          {
            dataField: 'total_attendances',
            caption: 'Attendances',
            fixed: true,
            fixedPosition: 'left',
            width: 100,
            alignment: 'center',
            allowSorting: true,
            allowHiding: true
          }
        ];

        serverColumns.forEach((gathering, idx) => {
          const registered = registerGathering(gathering);
          const gid = registered.id;
          const hasCheckedIn = gid && rows.some(r => attendanceLogic.isCheckedIn(r, gid));
          const colWidth = hasCheckedIn ? 150 : 100;
          const colId = getColumnIdentifier(registered);

          columns.push({
            name: colId,
            colIndex: idx,
            caption: getColumnCaption(registered),
            alignment: 'center',
            width: colWidth,
            minWidth: colWidth,
            gatheringMeta: registered,
            headerCellTemplate: gatheringHeaderTemplate,
            cellTemplate: attendanceCellTemplate,
            cssClass: `roster-col-idx-${idx}`
          });
        });


        columns.push({
          caption: '',
          cssClass: 'dummy-column',
          allowHiding: false,
          showInColumnChooser: false,
          allowExporting: false
        });

        // Preserve existing column options (groupIndex, sortOrder, sortIndex, visible, width)
        columns.forEach(col => {
          if (gridInstanceRef.value && col.dataField) {
            const groupIndex = gridInstanceRef.value.columnOption(col.dataField, 'groupIndex');
            if (groupIndex !== undefined && groupIndex !== null && groupIndex !== -1) {
              col.groupIndex = groupIndex;
            }
            const sortOrder = gridInstanceRef.value.columnOption(col.dataField, 'sortOrder');
            if (sortOrder) {
              col.sortOrder = sortOrder;
            }
            const sortIndex = gridInstanceRef.value.columnOption(col.dataField, 'sortIndex');
            if (sortIndex !== undefined && sortIndex !== null) {
              col.sortIndex = sortIndex;
            }
            const visible = gridInstanceRef.value.columnOption(col.dataField, 'visible');
            if (visible !== undefined && visible !== null) {
              col.visible = visible;
            }
            const width = gridInstanceRef.value.columnOption(col.dataField, 'width');
            if (width !== undefined && width !== null && !(col.dataField === 'team__display_name' && width > 100)) {
              col.width = width;
            }
          }
        });

        gridInstanceRef.value.option('columns', columns);
      } else if (rows && rows.length) {
        serverColumns.forEach(gathering => {
          const registered = registerGathering(gathering);
          const gid = registered.id;
          const hasCheckedIn = gid && rows.some(r => attendanceLogic.isCheckedIn(r, gid));
          const colId = getColumnIdentifier(registered);
          const targetWidth = hasCheckedIn ? 150 : 100;
          const curWidth = gridInstanceRef.value.columnOption(colId, 'width');
          if (curWidth && curWidth !== targetWidth) {
            gridInstanceRef.value.columnOption(colId, 'width', targetWidth);
            gridInstanceRef.value.columnOption(colId, 'minWidth', targetWidth);
          }
          gridInstanceRef.value.columnOption(colId, 'gatheringMeta', registered);
          const targetCaption = getColumnCaption(registered);
          const curCaption = gridInstanceRef.value.columnOption(colId, 'caption');
          if (curCaption && curCaption !== targetCaption) {
            gridInstanceRef.value.columnOption(colId, 'caption', targetCaption);
          }
        });
      }
    };

    const loadData = (targetAttendeeId, targetGatheringId) => {
      return new Promise(async (resolve) => {
        if (!filterData.meets || !filterData.meets.length) {
          if (gridInstanceRef.value) {
            gridInstanceRef.value.option('dataSource', []);
          }
          resolve();
          return; 
        }

        if (gridInstanceRef.value) {
          try {
            if (typeof gridInstanceRef.value.beginCustomLoading === 'function') {
              gridInstanceRef.value.beginCustomLoading();
            }

            const savedGridState = JSON.parse(window.sessionStorage.getItem(Attendees.utilities.datagridStorageKeys['rostersListView']) || '{}');
            const currentTake = (savedGridState && typeof savedGridState.pageSize === 'number') 
              ? savedGridState.pageSize 
              : (gridInstanceRef.value && typeof gridInstanceRef.value.pageSize === 'function' ? gridInstanceRef.value.pageSize() : 40);

            const queryParams = new URLSearchParams();
            filterData.meets.forEach(meet => queryParams.append('meets[]', meet));
            
            if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
            if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

            queryParams.set('skip', 0);
            queryParams.set('take', currentTake || 40);

            const response = await fetch(`${endpoints.rosters}?${queryParams.toString()}`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const initialData = await response.json();
            let preloadedData = initialData;

            const customStore = new DevExpress.data.CustomStore({
              key: 'attendee_id',
              load: async (loadOptions) => {
                try {
                  // If initial load with skip=0 and no custom sort/search/filter/group, consume preloaded data
                  const isInitialOptions = (!loadOptions.skip || loadOptions.skip === 0) 
                    && !loadOptions.sort 
                    && !loadOptions.searchValue 
                    && !loadOptions.filter
                    && (!loadOptions.group || loadOptions.group.length === 0);

                  if (preloadedData && isInitialOptions) {
                    const cached = preloadedData;
                    preloadedData = null;
                    const rows = cached.data || cached.rows || [];
                    const takeCount = loadOptions.take || currentTake || 40;
                    return {
                      data: (takeCount && rows.length > takeCount) ? rows.slice(0, takeCount) : rows,
                      totalCount: cached.totalCount
                    };
                  }

                  const pageParams = new URLSearchParams();
                  filterData.meets.forEach(meet => pageParams.append('meets[]', meet));
                  
                  if (filterData.startDate) pageParams.set('start', filterData.startDate.toISOString());
                  if (filterData.endDate) pageParams.set('finish', filterData.endDate.toISOString());

                  pageParams.set('skip', loadOptions.skip || 0);
                  pageParams.set('take', loadOptions.take || currentTake || 40);

                  if (loadOptions.sort) {
                    pageParams.set('sort', JSON.stringify(loadOptions.sort));
                  }

                  if (loadOptions.group) {
                    const adjustedGroup = loadOptions.group.map(g => ({ ...g, isExpanded: true }));
                    pageParams.set('group', JSON.stringify(adjustedGroup));
                  }

                  if (loadOptions.searchValue) {
                    pageParams.set('searchValue', loadOptions.searchValue);
                  } else if (loadOptions.filter) {
                    pageParams.set('filter', JSON.stringify(loadOptions.filter));
                  }

                  const pageResponse = await fetch(`${endpoints.rosters}?${pageParams.toString()}`);
                  if (!pageResponse.ok) throw new Error('Network response was not ok');
                  
                  const pageData = await pageResponse.json();
                  
                  return {
                    data: pageData.data || pageData.rows,
                    totalCount: pageData.totalCount
                  };

                } catch (error) {
                  DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', WARNING_NOTIFY_TIME);
                  console.error(error);
                  throw error; 
                }
              }
            });

            const onContentReady = () => {
              gridInstanceRef.value.off('contentReady', onContentReady);
              if (targetAttendeeId) {
                gridInstanceRef.value.selectRows([targetAttendeeId], false);

                const scrollToRowElement = () => {
                  if (!gridInstanceRef.value) return;
                  const rowIndex = gridInstanceRef.value.getRowIndexByKey(targetAttendeeId);
                  if (rowIndex >= 0) {
                    const rowEl = gridInstanceRef.value.getRowElement(rowIndex);
                    const domEl = rowEl && (rowEl[0] || (rowEl.length ? rowEl[0] : rowEl));
                    if (domEl && typeof domEl.scrollIntoView === 'function') {
                      domEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                  }
                };

                const tryNavigateAndScroll = async () => {
                  if (!gridInstanceRef.value) return;
                  const rowIndex = gridInstanceRef.value.getRowIndexByKey(targetAttendeeId);

                  if (rowIndex >= 0) {
                    scrollToRowElement();
                    return;
                  }

                  // If not on current page, check where the attendee is located across the roster
                  try {
                    const findParams = new URLSearchParams();
                    filterData.meets.forEach(meet => findParams.append('meets[]', meet));
                    if (filterData.startDate) findParams.set('start', filterData.startDate.toISOString());
                    if (filterData.endDate) findParams.set('finish', filterData.endDate.toISOString());
                    findParams.set('skip', 0);
                    findParams.set('take', 9999);

                    const allRes = await fetch(`${endpoints.rosters}?${findParams.toString()}`);
                    if (allRes.ok) {
                      const allData = await allRes.json();
                      const allRows = allData.data || allData.rows || [];
                      const foundIdx = allRows.findIndex(r => String(r.attendee_id) === String(targetAttendeeId));
                      if (foundIdx >= 0) {
                        const pageSize = gridInstanceRef.value.pageSize() || 40;
                        const targetPage = Math.floor(foundIdx / pageSize);
                        if (gridInstanceRef.value.pageIndex() !== targetPage) {
                          const onTargetPageReady = () => {
                            gridInstanceRef.value.off('contentReady', onTargetPageReady);
                            gridInstanceRef.value.selectRows([targetAttendeeId], false);
                            setTimeout(scrollToRowElement, 150);
                          };
                          gridInstanceRef.value.on('contentReady', onTargetPageReady);
                          gridInstanceRef.value.pageIndex(targetPage);
                          return;
                        }
                      }
                    }
                  } catch (e) {
                    console.warn('Auto page navigation error:', e);
                  }

                  // Fallback: navigateToRow
                  if (typeof gridInstanceRef.value.navigateToRow === 'function') {
                    gridInstanceRef.value.navigateToRow(targetAttendeeId);
                    setTimeout(scrollToRowElement, 200);
                  }
                };

                setTimeout(tryNavigateAndScroll, 100);
              }
              if (targetGatheringId) {
                highlightGatheringColumn(targetGatheringId);
              }
              resolve();
            };
            gridInstanceRef.value.on('contentReady', onContentReady);

            gridInstanceRef.value.beginUpdate();
            gatheringsRegistry.clear();
            updateGridColumns(initialData.columns, initialData.data || initialData.rows || []);
            const curTeamWidth = gridInstanceRef.value.columnOption('team__display_name', 'width');
            if (curTeamWidth && curTeamWidth > 100) {
              gridInstanceRef.value.columnOption('team__display_name', 'width', 80);
            }
            gridInstanceRef.value.option('dataSource', customStore);
            gridInstanceRef.value.endUpdate();

            const targetPageIndex = (savedGridState && typeof savedGridState.pageIndex === 'number') ? savedGridState.pageIndex : null;
            if (targetPageIndex !== null && targetPageIndex > 0 && gridInstanceRef.value.pageIndex() !== targetPageIndex) {
              gridInstanceRef.value.pageIndex(targetPageIndex);
            }

          } catch (error) {
            DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', WARNING_NOTIFY_TIME);
            console.error(error);
            resolve();
          } finally {
            if (typeof gridInstanceRef.value.endCustomLoading === 'function') {
              gridInstanceRef.value.endCustomLoading();
            }
          }
        } else {
          resolve();
        }
      });
    };

    const initDataGrid = (dataGridEl) => {
      gridInstanceRef.value = new DevExpress.ui.dxDataGrid(dataGridEl, {
        dataSource: [],
        showBorders: true,
        rowAlternationEnabled: true,
        allowColumnResizing: true,
        columnResizingMode: 'widget',
        columnAutoWidth: true,
        hoverStateEnabled: true,
        noDataText: "No data found. Please select a meet to load.",
        remoteOperations: { groupPaging: true },
        paging: {
          enabled: true,
          pageSize: 40,
        },
        pager: {
          visible: true,
          showPageSizeSelector: true,
          allowedPageSizes: [20, 40, 100, 9999],
          showInfo: true,
          showNavigationButtons: true,
        },
        stateStoring: {
          enabled: true,
          type: 'sessionStorage',
          storageKey: Attendees.utilities.datagridStorageKeys['rostersListView'],
        },
        export: {
          enabled: true,
          allowExportSelectedData: true,  // needs selection mode
          texts: {
            exportAll: 'Export data only on viewed pages',
            exportSelectedRows: 'Export selected rows on viewed pages',
            exportTo: 'Export data on viewed pages',
          },
        },
        selection: {
          mode: 'multiple',
          showCheckBoxesMode: 'onLongTap',
        },
        onExporting: async (e) => {
          const loadScript = (src) => new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = src;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
          });

          let excelJs = window.ExcelJS || (typeof ExcelJS !== 'undefined' ? ExcelJS : null);
          if (!excelJs) {
            try {
              await loadScript('https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.3.0/exceljs.min.js');
              excelJs = window.ExcelJS;
            } catch (err) {
              console.error('Failed to dynamically load ExcelJS:', err);
            }
          }

          let fileSaver = window.saveAs || (typeof saveAs !== 'undefined' ? saveAs : null);
          if (!fileSaver) {
            try {
              await loadScript('https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js');
              fileSaver = window.saveAs;
            } catch (err) {
              console.error('Failed to dynamically load FileSaver:', err);
            }
          }

          if (!excelJs || !DevExpress.excelExporter) {
            DevExpress.ui.notify('ExcelJS library is not loaded', 'error', WARNING_NOTIFY_TIME);
            return;
          }

          const workbook = new excelJs.Workbook();
          const worksheet = workbook.addWorksheet('Rosters');

          DevExpress.excelExporter.exportDataGrid({
            component: e.component,
            worksheet,
            selectedRowsOnly: e.selectedRowsOnly,
            autoFilterEnabled: true,
            customizeCell: (options) => {
              const { gridCell, excelCell } = options;
              if (gridCell.rowType === 'data') {
                if (gridCell.column && gridCell.column.gatheringMeta) {
                  const gid = gridCell.column.gatheringMeta.id;
                  if (gid && gridCell.data) {
                    if (attendanceLogic.isCheckedOut(gridCell.data, gid)) {
                      excelCell.value = 'Checked Out';
                    } else if (attendanceLogic.isCheckedIn(gridCell.data, gid)) {
                      excelCell.value = 'Checked In';
                    } else {
                      excelCell.value = '';
                    }
                  }
                } else if (gridCell.column && gridCell.column.dataField === 'team__display_name' && gridCell.data && gridCell.data.attendingmeets) {
                  const isMulti = filterData.meets && filterData.meets.length > 1;
                  if (isMulti) {
                    excelCell.value = gridCell.data.attendingmeets
                      .map(am => `${am.meet_name || 'Meet'}: ${am.team_name || ''}`)
                      .join('\n');
                  }
                } else if (gridCell.column && gridCell.column.dataField === 'character__display_name' && gridCell.data && gridCell.data.attendingmeets) {
                  const isMulti = filterData.meets && filterData.meets.length > 1;
                  if (isMulti) {
                    excelCell.value = gridCell.data.attendingmeets
                      .map(am => `${am.meet_name || 'Meet'}: ${am.character_name || ''}`)
                      .join('\n');
                  }
                }
              }
            }
          }).then(() => {
            workbook.xlsx.writeBuffer().then((buffer) => {
              const brand = document.querySelector('a.navbar-brand');
              const title = (brand ? brand.innerText.trim() : 'Rosters') + `_${new Date().toLocaleDateString('sv-SE')}.xlsx`;
              if (typeof fileSaver === 'function') {
                fileSaver(new Blob([buffer], { type: 'application/octet-stream' }), title);
              }
            }).catch(err => {
              console.error('Error writing workbook buffer:', err);
              DevExpress.ui.notify('Export failed: ' + err.message, 'error', WARNING_NOTIFY_TIME);
            });
          }).catch(err => {
            console.error('Error exporting datagrid:', err);
            DevExpress.ui.notify('Export failed: ' + err.message, 'error', WARNING_NOTIFY_TIME);
          });
          e.cancel = true;
        },
        columns: [
          {
            dataField: 'attendee_name',
            caption: 'Attendee',
            fixed: true,
            fixedPosition: 'left',
            width: 200,
            cellTemplate: attendeeCellTemplate,
            allowSorting: true,
            allowHiding: false
          },
          {
            dataField: 'team__display_name',
            caption: 'Team',
            fixed: true,
            fixedPosition: 'left',
            width: 80,
            cellTemplate: teamCellTemplate,
            allowSorting: true,
            allowHiding: true
          },
          {
            dataField: 'character__display_name',
            caption: 'Character',
            visible: false,
            allowHiding: true,
            fixed: true,
            fixedPosition: 'left',
            width: 140,
            cellTemplate: characterCellTemplate,
            allowSorting: true
          },
          {
            dataField: 'contacts',
            caption: 'Contacts',
            visible: false,
            allowHiding: true,
            allowSorting: false,
            width: 180
          },
          {
            dataField: 'total_attendances',
            caption: 'Attendances',
            fixed: true,
            fixedPosition: 'left',
            width: 100,
            alignment: 'center',
            allowSorting: true,
            allowHiding: true
          }
        ],
        grouping: {
          autoExpandAll: true,
        },
        groupPanel: {
          visible: true,
        },
        searchPanel: {
          visible: true,
          width: 250,
          placeholder: 'Search name, contacts, team, character...',
        },
        columnChooser: {
          enabled: true,
          mode: 'select',
        },
        onToolbarPreparing: (e) => {
          const toolbarItems = e.toolbarOptions.items;
          toolbarItems.unshift({
            location: 'after',
            widget: 'dxButton',
            options: {
              hint: 'Reset Sort/Group/Columns/Meets settings',
              icon: 'clearsquare',
              onClick() {
                if (confirm('Are you sure to reset all settings (Sort/Group/Columns/Meets/Time) in this page?')) {
                  const optsKey = Attendees.utilities.datagridStorageKeys['rostersListViewOpts'];
                  const gridKey = Attendees.utilities.datagridStorageKeys['rostersListView'];
                  window.sessionStorage.removeItem(optsKey);
                  window.sessionStorage.removeItem(gridKey);
                  if (gridInstanceRef.value) {
                    gridInstanceRef.value.state(null);
                  }
                  if (typeof onResetCallback === 'function') {
                    onResetCallback();
                  }
                }
              }
            }
          });
        }
      });
    };

    return {
      initDataGrid,
      loadData,
      getHighlightedGathering: () => activeHighlightedIndex !== null ? lastHighlightedGathering : null,
      clearColumnHighlight,
      highlightGatheringColumn
    };
  }

  // ==========================================================
  // 4. Filters Form Logic
  // ==========================================================
  function useRosterFilter(endpoints, filterData, reloadCallback, gridInstanceRef) {
    let formInstance = null;
    const storageOptsKey = Attendees.utilities.datagridStorageKeys['rostersListViewOpts'];

    const resetFilters = () => {
      const defaultStart = new Date(new Date().setDate(new Date().getDate() - 5));
      const defaultEnd = new Date(new Date().setMonth(new Date().getMonth() + 1));
      filterData.meets = [];
      filterData.startDate = defaultStart;
      filterData.endDate = defaultEnd;
      filterData.showPhotos = false;

      if (formInstance) {
        formInstance.getEditor('startDate').option('value', defaultStart);
        formInstance.getEditor('endDate').option('value', defaultEnd);
        formInstance.getEditor('showPhotos').option('value', false);
        formInstance.getEditor('meets').option('value', []);
      }
      if (gridInstanceRef.value) {
        gridInstanceRef.value.option('dataSource', []);
      }
    };

    const initFilterForm = (filterFormEl) => {
      formInstance = new DevExpress.ui.dxForm(filterFormEl, {
        formData: filterData,
        colCount: 4,
        onFieldDataChanged: (e) => {
          filterData[e.dataField] = e.value;
          
          // Date Validation constraints & saving to sessionStorage
          if (e.dataField === 'startDate') {
            formInstance.getEditor('endDate').option('min', e.value);
            Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'filterFromString', e.value ? e.value.toJSON() : null);
            if (formInstance.getEditor('meets')) {
              formInstance.getEditor('meets').getDataSource().reload();
            }
          }
          if (e.dataField === 'endDate') {
            formInstance.getEditor('startDate').option('max', e.value);
            Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'filterTillString', e.value ? e.value.toJSON() : null);
            if (formInstance.getEditor('meets')) {
              formInstance.getEditor('meets').getDataSource().reload();
            }
          }
          if (e.dataField === 'meets') {
            Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'selectedMeetSlugs', e.value || []);
          }
          if (e.dataField === 'showPhotos') {
            Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'showPhotos', !!e.value);
          }

          if (['meets', 'startDate', 'endDate'].includes(e.dataField)) {
            reloadCallback();
          } else if (e.dataField === 'showPhotos' && gridInstanceRef.value) {
            gridInstanceRef.value.repaint();
          }
        },
        items: [
          {
            dataField: 'startDate',
            editorType: 'dxDateBox',
            label: { text: 'From' },
            editorOptions: { 
              type: 'datetime', 
              displayFormat: 'shortDateShortTime',
              showClearButton: true,
              max: filterData.endDate
            }
          },
          {
            dataField: 'endDate',
            editorType: 'dxDateBox',
            label: { text: 'To' },
            editorOptions: { 
              type: 'datetime', 
              displayFormat: 'shortDateShortTime',
              showClearButton: true,
              min: filterData.startDate
            }
          },
          {
            dataField: 'meets',
            editorType: 'dxTagBox',
            label: { text: 'Meets' },
            editorOptions: {
              grouped: true,
              displayExpr: 'display_name',
              valueExpr: 'slug',
              placeholder: 'Select Meets...',
              showClearButton: true,
              dataSource: new DevExpress.data.DataSource({
                store: new DevExpress.data.CustomStore({
                  key: 'slug',
                  byKey: (key) => {
                    return { slug: key, display_name: meetsInfoMap.get(key) || key };
                  },
                  load: async () => {
                    const queryParams = new URLSearchParams({
                      take: 9999,
                      grouping: 'assembly_name',
                      model: 'attendance'
                    });
                    
                    if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
                    if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

                    const response = await fetch(`${endpoints.meets}?${queryParams.toString()}`);
                    if (!response.ok) throw new Error('Failed to load meets');
                    const json = await response.json();

                    const rawData = json.data || json.results || json;
                    const items = Array.isArray(rawData) ? rawData : [];
                    items.forEach(groupOrMeet => {
                      if (groupOrMeet.items && Array.isArray(groupOrMeet.items)) {
                        groupOrMeet.items.forEach(m => {
                          if (m.id !== undefined) {
                            meetsInfoMap.set(m.id, m.display_name);
                            meetsInfoMap.set(String(m.id), m.display_name);
                            meetsMap.set(m.id, m);
                            meetsMap.set(String(m.id), m);
                          }
                          if (m.slug) {
                            meetsInfoMap.set(m.slug, m.display_name);
                            meetsMap.set(m.slug, m);
                          }
                        });
                      } else {
                        if (groupOrMeet.id !== undefined) {
                          meetsInfoMap.set(groupOrMeet.id, groupOrMeet.display_name);
                          meetsInfoMap.set(String(groupOrMeet.id), groupOrMeet.display_name);
                          meetsMap.set(groupOrMeet.id, groupOrMeet);
                          meetsMap.set(String(groupOrMeet.id), groupOrMeet);
                        }
                        if (groupOrMeet.slug) {
                          meetsInfoMap.set(groupOrMeet.slug, groupOrMeet.display_name);
                          meetsMap.set(groupOrMeet.slug, groupOrMeet);
                        }
                      }
                    });

                    // Backend (Utility.transform_result) already formats groups as { key, items }
                    return rawData;
                  }
                })
              })
            }
          },
          {
            dataField: 'showPhotos',
            editorType: 'dxCheckBox',
            label: { text: 'Show Photos' }
          }
        ]
      });
    };

    return { initFilterForm, resetFilters };
  }

  // ==========================================================
  // 5. Smart Conditional Polling Logic
  // ==========================================================
  function useSmartPolling(gridInstanceRef, filterData) {
    let pollingTimer = null;

    const isAnyGatheringActiveNow = () => {
      const now = Date.now();
      const fifteenMinutesMs = 15 * 60 * 1000;
      for (const g of gatheringsRegistry.values()) {
        if (!g || !g.start) continue;
        const gStart = new Date(g.start).getTime();
        if (isNaN(gStart)) continue;
        let gFinish = g.finish ? new Date(g.finish).getTime() : NaN;
        if (isNaN(gFinish)) {
          gFinish = gStart + 2 * 60 * 60 * 1000;
        }
        const windowStart = gStart - fifteenMinutesMs;
        const windowEnd = gFinish + fifteenMinutesMs;
        if (now >= windowStart && now <= windowEnd) {
          return true;
        }
      }
      return false;
    };

    const poll = async () => {
      if (document.hidden) return;
      if (window.Attendees && window.Attendees.utilities && window.Attendees.utilities.editingEnabled) return;
      if (!filterData.meets || filterData.meets.length === 0) return;
      if (!gridInstanceRef.value) return;
      if (!isAnyGatheringActiveNow()) return;

      try {
        await gridInstanceRef.value.refresh();
      } catch (e) {
        console.warn('Smart polling refresh skipped or failed:', e);
      }
    };

    const startPolling = () => {
      if (pollingTimer) clearInterval(pollingTimer);
      pollingTimer = setInterval(poll, 15000);
    };

    const stopPolling = () => {
      if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
      }
    };

    return {
      startPolling,
      stopPolling,
      poll
    };
  }

  // ==========================================================
  // 6. Add Attendee / Fast Onboarding Logic
  // ==========================================================
  function useAddAttendee(endpoints, filterData, gridInstanceRef, loadData, getHighlightedGathering, highlightGatheringColumn) {
    let popupInstance = null;
    let selectedMeetSlug = '';
    let selectedGatheringId = null;
    let currentSwitchToSearch = null;

    const escapeHtml = (str) => {
      if (!str) return '';
      return String(str).replace(/[&<>"']/g, (m) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      })[m]);
    };

    const getGatheringsForMeet = (meetId) => {
      if (!meetId) return [];
      const seen = new Set();
      const list = [];
      for (const g of gatheringsRegistry.values()) {
        if (g && String(g.meet_id) === String(meetId) && g.id && !seen.has(g.id)) {
          seen.add(g.id);
          list.push(g);
        }
      }
      list.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
      return list;
    };

    const getUpcomingOrOngoingGathering = (gatherings) => {
      if (!gatherings || gatherings.length === 0) return null;
      const now = Date.now();
      const thirtyMinutes = 30 * 60 * 1000;

      // 1. Ongoing gathering: start <= now <= (finish || start + 2 hours)
      const ongoing = gatherings.find(g => {
        const s = new Date(g.start).getTime();
        if (isNaN(s)) return false;
        let f = g.finish ? new Date(g.finish).getTime() : NaN;
        if (isNaN(f)) {
          f = s + 2 * 60 * 60 * 1000;
        }
        return s <= now && now <= f;
      });
      if (ongoing) return ongoing;

      // 2. Gathering starting within 30 minutes: now < start <= now + 30 minutes
      const within30Mins = gatherings
        .filter(g => {
          const s = new Date(g.start).getTime();
          return !isNaN(s) && s > now && s <= (now + thirtyMinutes);
        })
        .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
      if (within30Mins.length > 0) return within30Mins[0];

      // 3. Earliest upcoming gathering in the future: start > now
      const upcomingList = gatherings
        .filter(g => {
          const s = new Date(g.start).getTime();
          return !isNaN(s) && s > now;
        })
        .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
      if (upcomingList.length > 0) return upcomingList[0];

      // 4. Fallback: most recent past gathering (latest start <= now)
      const pastList = gatherings
        .filter(g => {
          const s = new Date(g.start).getTime();
          return !isNaN(s) && s <= now;
        })
        .sort((a, b) => new Date(b.start).getTime() - new Date(a.start).getTime());
      if (pastList.length > 0) return pastList[0];

      return gatherings[0];
    };

    const formatGatheringOption = (g) => {
      const d = new Date(g.start);
      if (isNaN(d.getTime())) return g.display_name || `Gathering #${g.id}`;
      const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const dayName = daysOfWeek[d.getDay()];
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hours = String(d.getHours()).padStart(2, '0');
      const mins = String(d.getMinutes()).padStart(2, '0');
      const label = `${y}-${m}-${day} (${dayName}) ${hours}:${mins}`;
      return g.display_name ? `${label} - ${g.display_name}` : label;
    };

    const getSelectedMeet = () => {
      if (!selectedMeetSlug && filterData.meets && filterData.meets.length > 0) {
        selectedMeetSlug = filterData.meets[0];
      }
      return (selectedMeetSlug ? (meetsMap.get(selectedMeetSlug) || meetsMap.get(String(selectedMeetSlug))) : null) || null;
    };

    const getMeetSettings = () => {
      const meet = getSelectedMeet();
      const showInfos = meet?.show_attendee_infos || (meet?.infos && meet.infos.show_attendee_infos) || {};
      const isKidMeet = Boolean(showInfos['infos-grade'] || showInfos['grade']);
      const showInsurer = Boolean(showInfos['infos-insurer'] || showInfos['insurer']);
      return { meet, isKidMeet, showInsurer };
    };

    const populateGenderSelect = (selectEl, defaultVal = 'UNSPECIFIED') => {
      if (!selectEl) return;
      const enums = (window.Attendees && window.Attendees.utilities && typeof window.Attendees.utilities.genderEnums === 'function')
        ? window.Attendees.utilities.genderEnums()
        : [{ name: 'MALE' }, { name: 'FEMALE' }, { name: 'UNSPECIFIED' }];

      selectEl.innerHTML = '';
      enums.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.name;
        opt.textContent = item.name.charAt(0).toUpperCase() + item.name.slice(1).toLowerCase();
        if (item.name.toUpperCase() === String(defaultVal).toUpperCase()) {
          opt.selected = true;
        }
        selectEl.appendChild(opt);
      });
    };

    const createContactRow = (isCompanion) => {
      const row = document.createElement('div');
      row.className = 'row g-2 mb-2 align-items-end contact-row';
      const typeClass = isCompanion ? 'ob-p-contact-type' : 'ob-contact-type';
      const valClass = isCompanion ? 'ob-p-contact-value' : 'ob-contact-value';
      row.innerHTML = `
        <div class="col-md-4 col-12">
          <select class="form-select form-select-sm ${typeClass}">
            <option value="phone" selected>Phone</option>
            <option value="email">Email</option>
            <option value="wechat">WeChat</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="line">Line</option>
          </select>
        </div>
        <div class="col-md-7 col-9">
          <input type="text" class="form-control form-control-sm ${valClass}" placeholder="Phone number, email, or account">
        </div>
        <div class="col-md-1 col-3 d-flex gap-1 align-items-end justify-content-start">
          <button type="button" class="btn btn-outline-success btn-sm px-2 add-contact-btn" title="Add another contact" style="min-width: 32px;">
            <i class="fas fa-plus"></i>
          </button>
          <button type="button" class="btn btn-outline-danger btn-sm px-2 remove-contact-btn" title="Remove this contact" style="min-width: 32px;">
            <i class="fas fa-minus"></i>
          </button>
        </div>
      `;
      return row;
    };

    const getContactValidationError = (type, val, targetName = 'Contact') => {
      if (!window.Attendees || !window.Attendees.utilities) return null;
      const normType = (type || 'phone').toLowerCase();
      if (normType === 'phone' || normType === 'whatsapp') {
        if (!window.Attendees.utilities.validateFastInputPhoneNumber(val)) {
          return `${targetName} phone number must contain at least 10 digits.`;
        }
      } else if (normType === 'email') {
        if (!window.Attendees.utilities.validateFastInputEmail(val)) {
          return `${targetName} email must be at least 5 characters and contain '@' and '.'.`;
        }
      } else {
        if (!window.Attendees.utilities.validateFastInputContact(type, val)) {
          return `${targetName} account must be at least 2 characters.`;
        }
      }
      return null;
    };

    const renderPopupContent = async (container) => {
      const targetEl = (container && container[0]) ? container[0] : container;
      if (!targetEl) return;
      const { meet, isKidMeet, showInsurer } = getMeetSettings();
      const meetDisplayName = meet ? (meet.display_name || meet.name || selectedMeetSlug) : (selectedMeetSlug || 'Selected Meet');
      const meetGatherings = await loadMeetGatherings(selectedMeetSlug, meet ? meet.id : null, endpoints.gatherings);

      const highlighted = (typeof getHighlightedGathering === 'function') ? getHighlightedGathering() : null;
      if (highlighted && highlighted.id && meetGatherings.some(g => String(g.id) === String(highlighted.id))) {
        selectedGatheringId = highlighted.id;
      } else if (!selectedGatheringId || !meetGatherings.some(g => String(g.id) === String(selectedGatheringId) || String(g.start ? `start_${g.start}` : '') === String(selectedGatheringId))) {
        const upcoming = getUpcomingOrOngoingGathering(meetGatherings);
        selectedGatheringId = upcoming ? (upcoming.id || (upcoming.start ? `start_${upcoming.start}` : null)) : (meetGatherings.length > 0 ? (meetGatherings[0].id || (meetGatherings[0].start ? `start_${meetGatherings[0].start}` : null)) : null);
      }

      targetEl.innerHTML = '';
      const template = document.getElementById('add-attendee-popup-template');
      if (!template || !template.content || !template.content.firstElementChild) {
        console.error('add-attendee-popup-template not found in DOM');
        return;
      }
      const rootDiv = template.content.firstElementChild.cloneNode(true);

      // 1. Target Meet control
      const meetContainer = rootDiv.querySelector('.target-meet-container');
      if (meetContainer) {
        if (filterData.meets && filterData.meets.length > 1) {
          const selectEl = document.createElement('select');
          selectEl.className = 'form-select form-select-sm target-meet-dropdown';
          filterData.meets.forEach(slug => {
            const m = meetsMap.get(slug) || meetsMap.get(String(slug));
            const name = m ? (m.display_name || m.name || slug) : slug;
            const opt = document.createElement('option');
            opt.value = slug;
            opt.textContent = name;
            if (slug === selectedMeetSlug) opt.selected = true;
            selectEl.appendChild(opt);
          });
          meetContainer.appendChild(selectEl);
        } else {
          const strongEl = document.createElement('strong');
          strongEl.className = 'text-truncate d-inline-block';
          strongEl.style.maxWidth = '100%';
          strongEl.title = meetDisplayName;
          strongEl.textContent = meetDisplayName;
          meetContainer.appendChild(strongEl);
        }
      }

      // 2. Target Gathering dropdown
      const gatheringSelectEl = rootDiv.querySelector('.target-gathering-dropdown');
      if (gatheringSelectEl) {
        gatheringSelectEl.innerHTML = meetGatherings.length > 0
          ? meetGatherings.map(g => {
              const val = g.id ? String(g.id) : (g.start ? `start_${g.start}` : '');
              const isSelected = String(val) === String(selectedGatheringId) || String(g.id) === String(selectedGatheringId);
              return `<option value="${val}" ${isSelected ? 'selected' : ''}>${escapeHtml(formatGatheringOption(g))}</option>`;
            }).join('')
          : '<option value="">(No gatherings available)</option>';
      }

      // 3. School Grade dropdown helper & options
      const populateGradeSelect = (selectEl) => {
        if (!selectEl) return;
        if (!gradeConverter || gradeConverter.length === 0) loadGradeConverter();
        if (gradeConverter && gradeConverter.length > 0) {
          selectEl.innerHTML = '<option value="">Select Grade</option>';
          gradeConverter.forEach(g => {
            const opt = document.createElement('option');
            opt.value = g.id;
            opt.textContent = g.label;
            selectEl.appendChild(opt);
          });
        }
      };

      // Helpers for populating Division and Relationship dropdowns
      const populateDivisionSelect = (selectEl, defaultDivisionId) => {
        if (!selectEl) return;
        const doPopulate = (divisions) => {
          if (!divisions || divisions.length === 0) return;
          selectEl.innerHTML = '';
          if (divisions.length > 1) {
            const placeholderOpt = document.createElement('option');
            placeholderOpt.value = '';
            placeholderOpt.textContent = 'Select Division';
            selectEl.appendChild(placeholderOpt);
          }
          divisions.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.display_name;
            if (defaultDivisionId !== undefined && defaultDivisionId !== null && String(d.id) === String(defaultDivisionId)) {
              opt.selected = true;
            } else if (divisions.length === 1) {
              opt.selected = true;
            }
            selectEl.appendChild(opt);
          });
          if (defaultDivisionId !== undefined && defaultDivisionId !== null && divisions.some(d => String(d.id) === String(defaultDivisionId))) {
            selectEl.value = String(defaultDivisionId);
          }
        };
        if (organizationDivisions.length > 0) {
          doPopulate(organizationDivisions);
        } else {
          loadOrganizationDivisions(endpoints.divisions).then(doPopulate);
        }
      };

      const populateRelationSelect = (selectEl, defaultSelected, isAttendee = false) => {
        if (!selectEl) return;
        const doPopulate = () => {
          const list = isAttendee ? allRawRelations : allFamilyRelations;
          if (!list || list.length === 0) return;
          selectEl.innerHTML = '';
          list.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.id;
            const title = (r.title || '').trim();
            opt.textContent = title ? title.charAt(0).toUpperCase() + title.slice(1) : `Relation #${r.id}`;
            if (title.toLowerCase() === (defaultSelected || 'parent').toLowerCase()) opt.selected = true;
            selectEl.appendChild(opt);
          });
          if (!selectEl.value && selectEl.options.length > 0) {
            const matchOpt = Array.from(selectEl.options).find(o => o.textContent.toLowerCase() === (defaultSelected || '').toLowerCase());
            if (matchOpt) {
              matchOpt.selected = true;
            } else {
              selectEl.selectedIndex = 0;
            }
          }
        };
        if (allRawRelations.length > 0) {
          doPopulate();
        } else {
          loadFamilyRelations(endpoints.relations).then(doPopulate);
        }
      };

      const meetDivisionId = meet?.division || meet?.division_id || (meet?.assembly && meet.assembly.division_id) || null;

      // Attendee 1 Division & Relationship dropdowns
      const att1DivSelect = rootDiv.querySelector('.attendee-block-1 .ob-division');
      if (att1DivSelect) {
        populateDivisionSelect(att1DivSelect, meetDivisionId);
      }

      const att1RelSelect = rootDiv.querySelector('.attendee-block-1 .ob-relationship');
      if (att1RelSelect) {
        populateRelationSelect(att1RelSelect, 'self', true);
      }

      const gradeSelectEl = rootDiv.querySelector('.attendee-block-1 .ob-grade');
      if (gradeSelectEl) {
        populateGradeSelect(gradeSelectEl);
      }

      const att1GenderSelect = rootDiv.querySelector('.attendee-block-1 .ob-gender');
      if (att1GenderSelect) {
        populateGenderSelect(att1GenderSelect, 'UNSPECIFIED');
      }

      // Sync birth day options based on chosen year and month
      const setupBirthdayDropdownSync = (block) => {
        if (!block) return;
        const yInp = block.querySelector('.ob-byear');
        const mSel = block.querySelector('.ob-bmonth');
        const dSel = block.querySelector('.ob-bday');
        if (!mSel || !dSel) return;

        const syncDays = () => {
          const yVal = yInp ? yInp.value : '';
          const mVal = mSel ? mSel.value : '';
          if (window.Attendees?.utilities?.adjustBirthdayDayOptions) {
            window.Attendees.utilities.adjustBirthdayDayOptions(yVal, mVal, dSel);
          }
        };

        if (yInp) {
          yInp.addEventListener('input', syncDays);
          yInp.addEventListener('change', syncDays);
        }
        if (mSel) {
          mSel.addEventListener('change', syncDays);
        }
      };
      setupBirthdayDropdownSync(rootDiv.querySelector('.attendee-block-1'));

      // 3b. Additional Attendees setup (Attendee 1, 2, 3...)
      const moreAttendeesBtn = rootDiv.querySelector('.more-attendees-btn');
      const addAttendeesContainer = rootDiv.querySelector('.additional-attendees-container');
      const attendeeTemplate = document.getElementById('attendee-block-template');

      const updateAttendeeLabels = () => {
        const visibleBlocks = Array.from(rootDiv.querySelectorAll('.attendee-block')).filter(b => b.style.display !== 'none');
        visibleBlocks.forEach((block, idx) => {
          const curIndex = idx + 1;
          const headerLabel = block.querySelector('.attendee-label');
          if (headerLabel) {
            headerLabel.textContent = visibleBlocks.length > 1 ? `Attendee ${curIndex} Information` : 'Attendee Information';
          }
          const divLabel = block.querySelector('.att-division-label');
          if (divLabel) divLabel.innerHTML = visibleBlocks.length > 1 ? `Attendee ${curIndex} Division <span class="text-danger">*</span>` : `Division <span class="text-danger">*</span>`;
          const relLabel = block.querySelector('.att-relationship-label');
          if (relLabel) relLabel.textContent = visibleBlocks.length > 1 ? `Attendee ${curIndex} Relationship` : 'Relationship';
          const fnLabel = block.querySelector('.att-firstname-label');
          if (fnLabel) fnLabel.textContent = visibleBlocks.length > 1 ? `Attendee ${curIndex} First Name (English)` : 'First Name (English)';
          const lnLabel = block.querySelector('.att-lastname-label');
          if (lnLabel) lnLabel.textContent = visibleBlocks.length > 1 ? `Attendee ${curIndex} Last Name (English)` : 'Last Name (English)';
          const fn2Label = block.querySelector('.att-firstname2-label');
          if (fn2Label) fn2Label.textContent = visibleBlocks.length > 1 ? `Attendee ${curIndex} First Name 2 (Other language)` : 'First Name 2 (Other language)';
          const ln2Label = block.querySelector('.att-lastname2-label');
          if (ln2Label) ln2Label.textContent = visibleBlocks.length > 1 ? `Attendee ${curIndex} Last Name 2 (Other language)` : 'Last Name 2 (Other language)';
        });
      };

      const appendNewAttendeeBlock = () => {
        if (!addAttendeesContainer || !attendeeTemplate) return;
        const clone = attendeeTemplate.content.firstElementChild.cloneNode(true);

        const attDivSelect = clone.querySelector('.ob-division');
        if (attDivSelect) {
          populateDivisionSelect(attDivSelect, meetDivisionId);
        }

        const attRelSelect = clone.querySelector('.ob-relationship');
        if (attRelSelect) {
          populateRelationSelect(attRelSelect, 'self', true);
        }

        const gradeSelect = clone.querySelector('.ob-grade');
        if (gradeSelect) populateGradeSelect(gradeSelect);

        const attGender = clone.querySelector('.ob-gender');
        if (attGender) populateGenderSelect(attGender, 'UNSPECIFIED');

        const kidFields = clone.querySelector('.kid-specific-fields');
        if (kidFields) kidFields.style.display = isKidMeet ? '' : 'none';

        const insurerGroup = clone.querySelector('.insurer-field-group');
        if (insurerGroup) insurerGroup.style.display = showInsurer ? '' : 'none';

        const birthdayBadge = clone.querySelector('.ob-birthday-badge');
        if (birthdayBadge) {
          birthdayBadge.className = isKidMeet ? 'text-danger' : 'text-muted';
          birthdayBadge.textContent = isKidMeet ? '* (Required)' : '(Optional)';
        }

        const removeBtn = clone.querySelector('.remove-attendee-btn');
        if (removeBtn) {
          removeBtn.addEventListener('click', () => {
            clone.remove();
            updateAttendeeLabels();
          });
        }

        addAttendeesContainer.appendChild(clone);
        setupBirthdayDropdownSync(clone);
        updateAttendeeLabels();

        const newFnInput = clone.querySelector('.ob-first-name');
        if (newFnInput) newFnInput.focus();
      };

      if (moreAttendeesBtn && addAttendeesContainer && attendeeTemplate) {
        moreAttendeesBtn.addEventListener('click', appendNewAttendeeBlock);
      }

      // 4. Companion Section DOM Elements & Initial Setup
      const guardianSection = rootDiv.querySelector('.guardian-section');
      const guardianHeader = rootDiv.querySelector('.guardian-section-header');
      const guardianContent = rootDiv.querySelector('.guardian-section-content');
      const companionCollapseIcon = rootDiv.querySelector('.companion-collapse-icon');
      const unaccompaniedContainer = rootDiv.querySelector('.unaccompanied-minor-container');
      const comp1Block = rootDiv.querySelector('.companion-block-1');
      const removeComp1Btn = rootDiv.querySelector('.remove-companion-1-btn');
      const moreCompanionsBtn = rootDiv.querySelector('.more-companions-btn');
      const addCompanionsContainer = rootDiv.querySelector('.additional-companions-container');
      const compTemplate = document.getElementById('companion-block-template');

      const setGuardianCollapsed = (collapsed) => {
        const content = rootDiv.querySelector('.guardian-section-content');
        if (content) {
          content.style.display = collapsed ? 'none' : '';
        }
        const indicator = rootDiv.querySelector('.companion-toggle-indicator');
        if (indicator) {
          const iconClass = collapsed ? 'fa-caret-right' : 'fa-caret-down';
          indicator.innerHTML = `<i class="fas ${iconClass} companion-collapse-icon" style="font-size: 1.15rem;"></i>`;
        }
      };

      if (guardianHeader) {
        guardianHeader.addEventListener('click', (e) => {
          if (e.target.closest('button, input, select, a')) return;
          const content = rootDiv.querySelector('.guardian-section-content');
          const isCurrentlyCollapsed = content && content.style.display === 'none';
          setGuardianCollapsed(!isCurrentlyCollapsed);
        });
      }

      // Companion 1 Division, Gender & Relationship dropdowns
      const divSelectEl = rootDiv.querySelector('.companion-block-1 .ob-p-division');
      populateDivisionSelect(divSelectEl);

      const comp1GenderEl = rootDiv.querySelector('.companion-block-1 .ob-p-gender');
      if (comp1GenderEl) {
        populateGenderSelect(comp1GenderEl, 'UNSPECIFIED');
      }

      const relSelectEl = rootDiv.querySelector('.companion-block-1 .ob-p-relationship');
      populateRelationSelect(relSelectEl, isKidMeet ? 'parent' : 'spouse');

      // 4b. Dynamic Companion labeling function
      const updateCompanionLabels = () => {
        const visibleBlocks = Array.from(rootDiv.querySelectorAll('.companion-block')).filter(b => b.style.display !== 'none');
        visibleBlocks.forEach((block, idx) => {
          const curIndex = idx + 1;
          const headerLabel = block.querySelector('.companion-label, .companion-1-label');
          if (headerLabel) headerLabel.innerHTML = `<i class="fas fa-user me-1"></i> Companion ${curIndex}`;

          const divLabel = block.querySelector('.comp-division-label');
          if (divLabel) divLabel.innerHTML = `Companion ${curIndex} Division <span class="text-danger">*</span>`;

          const genderLabel = block.querySelector('.comp-gender-label');
          if (genderLabel) genderLabel.textContent = `Companion ${curIndex} Gender`;

          const relLabel = block.querySelector('.comp-relationship-label');
          if (relLabel) relLabel.textContent = `Companion ${curIndex} Relationship`;

          const fnLabel = block.querySelector('.comp-firstname-label');
          if (fnLabel) fnLabel.textContent = `Companion ${curIndex} First Name (English)`;

          const lnLabel = block.querySelector('.comp-lastname-label');
          if (lnLabel) lnLabel.textContent = `Companion ${curIndex} Last Name (English)`;

          const ln2Label = block.querySelector('.comp-lastname2-label');
          if (ln2Label) ln2Label.textContent = `Companion ${curIndex} Last Name 2 (Other language)`;

          const fn2Label = block.querySelector('.comp-firstname2-label');
          if (fn2Label) fn2Label.textContent = `Companion ${curIndex} First Name 2 (Other language)`;

          const ctLabel = block.querySelector('.comp-contacttype-label');
          if (ctLabel) ctLabel.textContent = `Companion ${curIndex} Contact Type`;

          const cvLabel = block.querySelector('.comp-contactval-label');
          if (cvLabel) cvLabel.innerHTML = `Companion ${curIndex} Contact Number / Account <span class="text-danger">*</span>`;
        });

        if (!isKidMeet && visibleBlocks.length === 0) {
          setGuardianCollapsed(true);
        }
      };

      // 4c. Remove Companion 1 (enabled for adult meet)
      if (removeComp1Btn) {
        removeComp1Btn.addEventListener('click', () => {
          const firstExtra = addCompanionsContainer ? addCompanionsContainer.querySelector('.companion-block') : null;
          if (firstExtra) {
            comp1Block.querySelector('.ob-p-division').value = firstExtra.querySelector('.ob-p-division').value;
            const extraGender = firstExtra.querySelector('.ob-p-gender');
            if (extraGender) comp1Block.querySelector('.ob-p-gender').value = extraGender.value;
            comp1Block.querySelector('.ob-p-relationship').value = firstExtra.querySelector('.ob-p-relationship').value;
            comp1Block.querySelector('.ob-p-first-name').value = firstExtra.querySelector('.ob-p-first-name').value;
            comp1Block.querySelector('.ob-p-last-name').value = firstExtra.querySelector('.ob-p-last-name').value;
            comp1Block.querySelector('.ob-p-first-name2').value = firstExtra.querySelector('.ob-p-first-name2').value;
            comp1Block.querySelector('.ob-p-last-name2').value = firstExtra.querySelector('.ob-p-last-name2').value;

            // Replace companion 1 contacts with firstExtra's contacts
            const comp1ContactsContainer = comp1Block.querySelector('.companion-contacts-container');
            const extraContactsContainer = firstExtra.querySelector('.companion-contacts-container');
            if (comp1ContactsContainer && extraContactsContainer) {
              comp1ContactsContainer.innerHTML = extraContactsContainer.innerHTML;
            }
            firstExtra.remove();
          } else {
            comp1Block.querySelectorAll('input').forEach(inp => { inp.value = ''; });
            comp1Block.style.display = 'none';
            setGuardianCollapsed(true);
          }
          updateCompanionLabels();
        });
      }

      // 4d. Companion block append helper (triggered by '+' buttons or legacy 'More Companions' button)
      const appendNewCompanionBlock = () => {
        if (guardianSection && guardianSection.style.display === 'none') {
          guardianSection.style.display = '';
        }
        setGuardianCollapsed(false);

        if (comp1Block && comp1Block.style.display === 'none') {
          comp1Block.style.display = '';
          if (removeComp1Btn && !isKidMeet) removeComp1Btn.classList.remove('d-none');
          updateCompanionLabels();
          const fnInp = comp1Block.querySelector('.ob-p-first-name');
          if (fnInp) fnInp.focus();
          return;
        }

        if (!addCompanionsContainer || !compTemplate) return;

        const clone = compTemplate.content.firstElementChild.cloneNode(true);
        const compDivSelect = clone.querySelector('.ob-p-division');
        populateDivisionSelect(compDivSelect);

        const compGenderSelect = clone.querySelector('.ob-p-gender');
        if (compGenderSelect) {
          populateGenderSelect(compGenderSelect, 'UNSPECIFIED');
        }

        const compRelSelect = clone.querySelector('.ob-p-relationship');
        populateRelationSelect(compRelSelect, isKidMeet ? 'parent' : 'spouse');

        const removeBtn = clone.querySelector('.remove-companion-btn');
        if (removeBtn) {
          removeBtn.addEventListener('click', () => {
            clone.remove();
            updateCompanionLabels();
          });
        }

        addCompanionsContainer.appendChild(clone);
        updateCompanionLabels();

        const newFnInput = clone.querySelector('.ob-p-first-name');
        if (newFnInput) newFnInput.focus();
      };

      if (moreCompanionsBtn) {
        moreCompanionsBtn.addEventListener('click', appendNewCompanionBlock);
      }

      // 5. Birthday badge & Kid/Insurer/Companion section visibility
      const birthdayBadge = rootDiv.querySelector('.ob-birthday-badge');
      if (birthdayBadge) {
        birthdayBadge.className = isKidMeet ? 'text-danger' : 'text-muted';
        birthdayBadge.textContent = isKidMeet ? '* (Required)' : '(Optional)';
      }

      const kidFields = rootDiv.querySelector('.kid-specific-fields');
      if (kidFields) {
        kidFields.style.display = isKidMeet ? '' : 'none';
      }

      if (unaccompaniedContainer) {
        unaccompaniedContainer.style.display = isKidMeet ? '' : 'none';
      }

      if (guardianSection) {
        guardianSection.style.display = '';
      }
      setGuardianCollapsed(!isKidMeet);

      if (comp1Block) {
        comp1Block.style.display = '';
        if (removeComp1Btn) {
          if (!isKidMeet) {
            removeComp1Btn.classList.remove('d-none');
          } else {
            removeComp1Btn.classList.add('d-none');
          }
        }
      }

      const insurerGroup = rootDiv.querySelector('.insurer-field-group');
      if (insurerGroup) {
        insurerGroup.style.display = showInsurer ? '' : 'none';
      }

      targetEl.appendChild(rootDiv);

      // DOM Elements & Views
      const searchViewEl = rootDiv.querySelector('.search-view-container');
      const onboardViewEl = rootDiv.querySelector('.onboard-view-container');

      // A. Target Meet & Gathering dropdowns
      const meetSelectEl = rootDiv.querySelector('.target-meet-dropdown');
      if (meetSelectEl) {
        meetSelectEl.addEventListener('change', async (e) => {
          selectedMeetSlug = e.target.value;
          const newMeet = getSelectedMeet();
          const newGatherings = await loadMeetGatherings(selectedMeetSlug, newMeet ? newMeet.id : null, endpoints.gatherings);
          const upcoming = getUpcomingOrOngoingGathering(newGatherings);
          selectedGatheringId = upcoming ? (upcoming.id || (upcoming.start ? `start_${upcoming.start}` : null)) : (newGatherings.length > 0 ? (newGatherings[0].id || `start_${newGatherings[0].start}`) : null);
          renderPopupContent(container);
        });
      }

      if (gatheringSelectEl) {
        gatheringSelectEl.addEventListener('change', (e) => {
          selectedGatheringId = e.target.value || null;
        });
      }

      // Helper to update popup title bar and back button [←]
      const updatePopupTitle = (isOnboard) => {
        const popupWrapper = document.querySelector('.add-attendee-popup-wrapper');
        if (!popupWrapper) return;
        const backBtn = popupWrapper.querySelector('.popup-title-container .back-to-search-btn');
        const titleText = popupWrapper.querySelector('.popup-title-container .popup-title-text');
        if (isOnboard) {
          if (backBtn) backBtn.classList.remove('d-none');
          if (titleText) titleText.textContent = "Add Attendee to Rosters / New Attendee Registration";
        } else {
          if (backBtn) backBtn.classList.add('d-none');
          if (titleText) titleText.textContent = "Add Attendee to Rosters, Welcome! Let's search first.";
        }
      };

      const switchToSearch = () => {
        onboardViewEl.style.display = 'none';
        searchViewEl.style.display = '';
        updatePopupTitle(false);
        const searchInputEl = rootDiv.querySelector('.omni-search-box');
        if (searchInputEl) {
          searchInputEl.focus();
          searchInputEl.select();
        }
      };
      currentSwitchToSearch = switchToSearch;

      // B. Switch to Onboard function (prefilling names)
      const switchToOnboard = (query) => {
        searchViewEl.style.display = 'none';
        onboardViewEl.style.display = '';
        updatePopupTitle(true);

        if (query && typeof query === 'string') {
          const trimmed = query.trim();
          const isChinese = /[\u4e00-\u9fa5]/.test(trimmed);
          if (isChinese) {
            const fn2Input = rootDiv.querySelector('.ob-first-name2');
            const ln2Input = rootDiv.querySelector('.ob-last-name2');
            if (trimmed.length === 2) {
              if (ln2Input) ln2Input.value = trimmed[0];
              if (fn2Input) fn2Input.value = trimmed[1];
            } else if (trimmed.length === 3) {
              if (ln2Input) ln2Input.value = trimmed[0];
              if (fn2Input) fn2Input.value = trimmed.slice(1);
            } else {
              if (fn2Input) fn2Input.value = trimmed;
            }
          } else {
            const parts = trimmed.split(/\s+/);
            const fnInput = rootDiv.querySelector('.ob-first-name');
            const lnInput = rootDiv.querySelector('.ob-last-name');
            if (parts.length > 1) {
              if (fnInput) fnInput.value = parts.slice(0, -1).join(' ');
              if (lnInput) lnInput.value = parts[parts.length - 1];
            } else {
              if (fnInput) fnInput.value = trimmed;
            }
          }
        }
      };

      // C. Back to Search button
      const backToSearchBtn = rootDiv.querySelector('.back-to-search-btn');
      if (backToSearchBtn) {
        backToSearchBtn.addEventListener('click', () => {
          switchToSearch();
        });
      }

      // D. Unaccompanied Minor Checkbox toggle: collapse/hide all companions when checked
      const unaccompaniedCheck = rootDiv.querySelector('.ob-unaccompanied');
      if (unaccompaniedCheck) {
        unaccompaniedCheck.addEventListener('change', (e) => {
          const isAlone = e.target.checked;
          if (comp1Block) comp1Block.style.display = isAlone ? 'none' : '';
          if (addCompanionsContainer) addCompanionsContainer.style.display = isAlone ? 'none' : '';
          if (moreCompanionsBtn) {
            if (isAlone) {
              moreCompanionsBtn.classList.add('d-none');
            } else {
              moreCompanionsBtn.classList.remove('d-none');
            }
          }
        });
      }

      // E. Dynamic Contact rows (+ / - buttons) for Attendee and Companions & Attendee/Companion Block (+ / X)
      const onboardForm = rootDiv.querySelector('.onboard-form');
      if (onboardForm) {
        onboardForm.addEventListener('click', (e) => {
          const addAttBtn = e.target.closest('.add-more-attendee-btn');
          if (addAttBtn) {
            appendNewAttendeeBlock();
            return;
          }
          const removeAttBtn = e.target.closest('.remove-attendee-btn');
          if (removeAttBtn) {
            const block = removeAttBtn.closest('.attendee-block');
            if (block && !block.classList.contains('attendee-block-1')) {
              block.remove();
              updateAttendeeLabels();
            }
            return;
          }
          const addCompBtn = e.target.closest('.add-more-companion-btn');
          if (addCompBtn) {
            appendNewCompanionBlock();
            return;
          }
          const removeCompBtn = e.target.closest('.remove-companion-btn');
          if (removeCompBtn) {
            if (removeCompBtn.classList.contains('remove-companion-1-btn')) {
              // handled by removeComp1Btn
            } else {
              const block = removeCompBtn.closest('.companion-block');
              if (block) {
                block.remove();
                updateCompanionLabels();
              }
            }
            return;
          }
          const addBtn = e.target.closest('.add-contact-btn');
          if (addBtn) {
            const row = addBtn.closest('.contact-row');
            const container = addBtn.closest('.attendee-contacts-container, .companion-contacts-container');
            const isCompanion = !!addBtn.closest('.companion-contacts-container');
            const newRow = createContactRow(isCompanion);
            if (row) {
              row.after(newRow);
            } else if (container) {
              container.appendChild(newRow);
            }
            const newInput = newRow.querySelector('input');
            if (newInput) newInput.focus();
            return;
          }
          const removeBtn = e.target.closest('.remove-contact-btn');
          if (removeBtn) {
            const row = removeBtn.closest('.contact-row');
            if (row) {
              row.remove();
            }
            return;
          }
        });
      }

      // E. Search Execution
      const searchInput = rootDiv.querySelector('.omni-search-box');
      const searchBtn = rootDiv.querySelector('.search-submit-btn');
      const candidatesListEl = rootDiv.querySelector('.search-candidates-list');

      let debounceTimer = null;
      const doSearch = async () => {
        const query = (searchInput.value || '').trim();
        if (!query) {
          const hintTemplate = document.getElementById('attendee-search-hint-template');
          if (hintTemplate && hintTemplate.content && hintTemplate.content.firstElementChild) {
            candidatesListEl.innerHTML = '';
            candidatesListEl.appendChild(hintTemplate.content.firstElementChild.cloneNode(true));
          } else {
            candidatesListEl.innerHTML = `
              <div class="text-center text-muted p-4 small default-search-hint">
                <div class="mb-2"><i class="fas fa-search fa-2x text-secondary opacity-50"></i></div>
                <strong>Please search for attendee first</strong><br>
                Search by attendee name, phone, email, or guardian to prevent duplicate records. You can register a new attendee if no match is found.
              </div>
            `;
          }
          return;
        }

        candidatesListEl.innerHTML = `
          <div class="text-center p-4 text-secondary">
            <span class="spinner-border spinner-border-sm me-2" role="status"></span> Searching organization directory...
          </div>
        `;

        try {
          const res = await fetch(`${endpoints.searchAttendees}?meet_slug=${selectedMeetSlug}&q=${encodeURIComponent(query)}`);
          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            const errMsg = errData.detail || errData.error || res.statusText || 'Search failed. Please try again.';
            throw new Error(errMsg);
          }
          const results = await res.json();
          renderSearchResults(results, candidatesListEl, query, switchToOnboard);
        } catch (err) {
          candidatesListEl.innerHTML = `
            <div class="text-center text-danger p-3 small">
              <i class="fas fa-exclamation-circle me-1"></i> ${escapeHtml(err.message)}
            </div>
          `;
        }
      };

      if (searchInput) {
        searchInput.addEventListener('input', () => {
          if (debounceTimer) clearTimeout(debounceTimer);
          debounceTimer = setTimeout(doSearch, 400);
        });
        searchInput.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            if (debounceTimer) clearTimeout(debounceTimer);
            doSearch();
          }
        });
      }
      if (searchBtn) searchBtn.addEventListener('click', doSearch);

      // F. Submit Fast Onboard
      const submitBtn = rootDiv.querySelector('.ob-submit-btn');
      if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
          await handleFastOnboardSubmit(rootDiv, submitBtn);
        });
      }
    };

    const renderSearchResults = (results, container, query, onSwitchToOnboard) => {
      if (!results || results.length === 0) {
        container.innerHTML = '';
        const emptyTemplate = document.getElementById('attendee-search-empty-template');
        if (emptyTemplate && emptyTemplate.content && emptyTemplate.content.firstElementChild) {
          const emptyEl = emptyTemplate.content.firstElementChild.cloneNode(true);
          const msgEl = emptyEl.querySelector('.search-empty-message');
          if (msgEl) {
            msgEl.textContent = `No attendee records found matching "${query}" in the organization directory.`;
          }
          const btn = emptyEl.querySelector('.switch-to-onboard-btn');
          if (btn && onSwitchToOnboard) btn.addEventListener('click', () => onSwitchToOnboard(query));
          container.appendChild(emptyEl);
        }
        return;
      }

      container.innerHTML = '';
      const candTemplate = document.getElementById('attendee-search-candidate-template');

      results.forEach(cand => {
        let itemEl;
        if (candTemplate && candTemplate.content && candTemplate.content.firstElementChild) {
          itemEl = candTemplate.content.firstElementChild.cloneNode(true);
        } else {
          itemEl = document.createElement('div');
          itemEl.className = 'search-candidate-item';
        }

        if (cand.meet_status === 'enrolled') {
          itemEl.classList.add('already-enrolled');
        }

        let badgeHtml = '';
        let actionBtnHtml = '';
        let warningNoticeHtml = '';

        if (cand.meet_status === 'enrolled') {
          badgeHtml = '<span class="badge bg-info text-dark me-2"><i class="fas fa-check-circle me-1"></i> Already Enrolled</span>';
          actionBtnHtml = '<button class="btn btn-sm btn-outline-primary locate-cand-btn" title="Close popup and locate attendee in roster"><i class="fas fa-search me-1"></i> Locate in Roster</button>';
          warningNoticeHtml = '<div class="text-primary small mt-1"><i class="fas fa-info-circle me-1"></i> This attendee is already enrolled in this meet (may be on another page). Please check them in directly on the roster table.</div>';
        } else if (cand.meet_status === 'paused') {
          badgeHtml = '<span class="badge bg-warning text-dark me-2">Paused</span>';
          actionBtnHtml = '<span class="text-muted small">Cannot auto-join (Contact administrator)</span>';
        } else if (cand.can_join) {
          badgeHtml = `<span class="badge bg-secondary me-2">${cand.meet_status === 'expired' ? 'Expired' : 'Other Meet'}</span>`;
          actionBtnHtml = '<button class="btn btn-sm btn-primary enroll-cand-btn"><i class="fas fa-user-plus me-1"></i> Join Meet & Check In</button>';
        } else {
          badgeHtml = '<span class="badge bg-secondary">Cannot Join</span>';
        }

        const detailsParts = [];
        if (cand.gender && cand.gender !== 'unspecified') {
          const genderText = cand.gender.charAt(0).toUpperCase() + cand.gender.slice(1);
          detailsParts.push(`Gender: ${genderText}`);
        }
        if (cand.grade_name) detailsParts.push(`Grade: ${cand.grade_name}`);
        if (cand.age !== null && cand.age !== undefined) detailsParts.push(`Age: ${cand.age}`);
        if (cand.masked_phone) detailsParts.push(`Phone: ${cand.masked_phone}`);
        if (cand.guardians) detailsParts.push(`Guardian: ${cand.guardians}`);

        const photoContainer = itemEl.querySelector('.attendee-photo-container');
        if (photoContainer) {
          photoContainer.innerHTML = cand.photo_url 
            ? `<img src="${cand.photo_url}" class="attendee-photo" alt="Photo">`
            : `<div class="attendee-photo d-flex justify-content-center align-items-center bg-light text-muted"><i class="fas fa-user"></i></div>`;
        }

        const titleEl = itemEl.querySelector('.search-candidate-title');
        if (titleEl) titleEl.textContent = cand.name;

        const subtitleEl = itemEl.querySelector('.search-candidate-subtitle');
        if (subtitleEl) subtitleEl.textContent = detailsParts.join(' | ') || 'No additional info';

        const warningEl = itemEl.querySelector('.search-candidate-warning');
        if (warningEl) warningEl.innerHTML = warningNoticeHtml;

        const actionsEl = itemEl.querySelector('.search-candidate-actions');
        if (actionsEl) actionsEl.innerHTML = `${badgeHtml}${actionBtnHtml}`;

        const locateBtn = itemEl.querySelector('.locate-cand-btn');
        if (locateBtn) {
          locateBtn.addEventListener('click', () => {
            if (popupInstance) popupInstance.hide();
            if (gridInstanceRef.value) {
              if (typeof gridInstanceRef.value.searchByText === 'function') {
                gridInstanceRef.value.searchByText(cand.name);
              }
              DevExpress.ui.notify(`Located in roster: ${cand.name}`, 'info', 3000);
            }
          });
        }

        const enrollBtn = itemEl.querySelector('.enroll-cand-btn');
        if (enrollBtn) {
          enrollBtn.addEventListener('click', async () => {
            await handleCandidateEnrollAndCheckIn(cand);
          });
        }

        container.appendChild(itemEl);
      });

      // Bottom section: Only shown after search results are visible
      const footerTemplate = document.getElementById('attendee-search-footer-template');
      if (footerTemplate && footerTemplate.content && footerTemplate.content.firstElementChild) {
        const footerEl = footerTemplate.content.firstElementChild.cloneNode(true);
        const footerBtn = footerEl.querySelector('.switch-to-onboard-btn');
        if (footerBtn && onSwitchToOnboard) footerBtn.addEventListener('click', () => onSwitchToOnboard(query));
        container.appendChild(footerEl);
      }
    };

    const handleCandidateEnrollAndCheckIn = async (cand) => {
      const meetObj = meetsMap.get(selectedMeetSlug) || meetsMap.get(String(selectedMeetSlug));
      if (!meetObj) return;

      if (window.Attendees && window.Attendees.utilities) {
        window.Attendees.utilities.editingEnabled = true;
      }

      try {
        // 1. Create or renew AttendingMeet
        let attendingId = cand.attending_id;
        if (!attendingId) {
          const attgRes = await fetch(endpoints.attendings, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Target-Attendee-Id': String(cand.id),
              'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
              attendee: cand.id,
              registration: null
            })
          });
          if (!attgRes.ok) {
            const attgErr = await attgRes.json().catch(() => ({}));
            throw new Error(attgErr.detail || attgErr.error || 'Failed to initialize attending record');
          }
          const newAttending = await attgRes.json();
          attendingId = newAttending.id;
          cand.attending_id = attendingId;
        }

        const amPayload = {
          attending: attendingId,
          meet: meetObj.id,
          character: meetObj.major_character || 1,
          category: 1, // Scheduled
          finish: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
        };

        const amRes = await fetch(endpoints.attendingmeets, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Target-Attendee-Id': String(cand.id),
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify(amPayload)
        });

        if (!amRes.ok) {
          const amErr = await amRes.json().catch(() => ({}));
          throw new Error(amErr.detail || amErr.error || `Failed to enroll in meet (HTTP ${amRes.status})`);
        }

        // 2. Mark check-in with selected gathering
        const gatheringDropdown = document.querySelector('.target-gathering-dropdown');
        const chosenGatheringVal = (gatheringDropdown && gatheringDropdown.value) || selectedGatheringId || '';

        let targetGatheringId = null;
        let targetGatheringStart = null;

        if (chosenGatheringVal) {
          if (String(chosenGatheringVal).startsWith('start_')) {
            targetGatheringStart = String(chosenGatheringVal).replace(/^start_/, '');
          } else if (/^\d+$/.test(String(chosenGatheringVal))) {
            targetGatheringId = parseInt(chosenGatheringVal, 10);
          }
        }

        if (!targetGatheringId && !targetGatheringStart) {
          const meetGatherings = getGatheringsForMeet(meetObj.id);
          const upcoming = getUpcomingOrOngoingGathering(meetGatherings);
          if (upcoming) {
            if (upcoming.id && /^\d+$/.test(String(upcoming.id))) {
              targetGatheringId = parseInt(upcoming.id, 10);
            } else if (upcoming.start) {
              targetGatheringStart = upcoming.start;
            }
          }
        }

        const attPayload = {
          attending: attendingId,
          character: meetObj.major_character || 1,
          category: 9, // Attended
          start: new Date().toISOString(),
          meet: meetObj.id
        };

        if (targetGatheringId) {
          attPayload.gathering = targetGatheringId;
        } else if (targetGatheringStart) {
          attPayload.gathering = null;
          attPayload.gathering_start = targetGatheringStart;
        }

        const attRes = await fetch(endpoints.attendances, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify(attPayload)
        });

        if (!attRes.ok) {
          const attErr = await attRes.json().catch(() => ({}));
          throw new Error(attErr.detail || attErr.error || `Attendance check-in failed (HTTP ${attRes.status}: ${attRes.statusText})`);
        }

        const attData = await attRes.json().catch(() => ({}));
        const confirmedGatheringId = attData.gathering || targetGatheringId || null;

        DevExpress.ui.notify(`Enrolled and checked in ${cand.name} successfully!`, 'success', 2500);
        if (popupInstance) popupInstance.hide();
        await loadData(cand.id, confirmedGatheringId);
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', WARNING_NOTIFY_TIME);
      } finally {
        if (window.Attendees && window.Attendees.utilities) {
          window.Attendees.utilities.editingEnabled = false;
        }
      }
    };

    const handleFastOnboardSubmit = async (rootDiv, submitBtn) => {
      const { meet, isKidMeet, showInsurer } = getMeetSettings();
      if (!meet) {
        DevExpress.ui.notify('Please select a valid meet.', 'error', WARNING_NOTIFY_TIME);
        return;
      }

      // 1. Collect and validate all Attendee blocks
      const attendeeBlocks = Array.from(rootDiv.querySelectorAll('.attendee-block')).filter(b => b.style.display !== 'none');
      if (attendeeBlocks.length === 0) {
        DevExpress.ui.notify('Please provide at least one attendee.', 'warning', WARNING_NOTIFY_TIME);
        return;
      }

      const isUnaccompanied = isKidMeet && rootDiv.querySelector('.ob-unaccompanied')?.checked;
      const attendeesList = [];

      for (let aIdx = 0; aIdx < attendeeBlocks.length; aIdx++) {
        const block = attendeeBlocks[aIdx];
        const attNum = aIdx + 1;
        const attLabel = attendeeBlocks.length > 1 ? `Attendee ${attNum}` : 'Attendee';

        const divEl = block.querySelector('.ob-division');
        const divVal = divEl ? divEl.value : '';
        const relEl = block.querySelector('.ob-relationship');
        const relVal = relEl ? relEl.value : 'self';

        if (organizationDivisions.length > 0 && !divVal) {
          DevExpress.ui.notify(`Please select a division for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
          divEl?.focus();
          return;
        }

        const firstName = (block.querySelector('.ob-first-name')?.value || '').trim();
        const lastName = (block.querySelector('.ob-last-name')?.value || '').trim();
        const firstName2 = (block.querySelector('.ob-first-name2')?.value || '').trim();
        const lastName2 = (block.querySelector('.ob-last-name2')?.value || '').trim();
        const gender = (block.querySelector('.ob-gender')?.value || 'UNSPECIFIED').toUpperCase();

        const byear = (block.querySelector('.ob-byear')?.value || '').trim();
        const bmonth = (block.querySelector('.ob-bmonth')?.value || '').trim();
        const bday = (block.querySelector('.ob-bday')?.value || '').trim();

        // Validation: at least one name (English or other language) is required
        if (!firstName && !lastName && !firstName2 && !lastName2) {
          DevExpress.ui.notify(`At least one name (English or other language) is required for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
          block.querySelector('.ob-first-name')?.focus();
          return;
        }

        // Birthday validation
        if (isKidMeet) {
          if (!byear || !bmonth || !bday) {
            DevExpress.ui.notify(`Year, Month, and Day of birth are all required for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
            block.querySelector('.ob-byear')?.focus();
            return;
          }
        }

        if (byear || bmonth || bday) {
          const bValid = window.Attendees?.utilities?.validateFastInputBirthday
            ? window.Attendees.utilities.validateFastInputBirthday(byear, bmonth, bday)
            : { valid: true };
          if (!bValid.valid) {
            DevExpress.ui.notify(`${attLabel}: ${bValid.message}`, 'warning', WARNING_NOTIFY_TIME);
            if (byear) {
              block.querySelector('.ob-byear')?.focus();
            } else if (bmonth) {
              block.querySelector('.ob-bmonth')?.focus();
            } else {
              block.querySelector('.ob-bday')?.focus();
            }
            return;
          }
        }

        // Contacts validation & phone normalization
        const attendeeContactRows = Array.from(block.querySelectorAll('.attendee-contacts-container .contact-row'));
        const attendeeContacts = [];
        for (const row of attendeeContactRows) {
          const cType = row.querySelector('.ob-contact-type')?.value || 'phone';
          let cVal = (row.querySelector('.ob-contact-value')?.value || '').trim();
          if (cVal) {
            const vErr = getContactValidationError(cType, cVal, attLabel);
            if (vErr) {
              DevExpress.ui.notify(vErr, 'warning', WARNING_NOTIFY_TIME);
              row.querySelector('.ob-contact-value')?.focus();
              return;
            }
            if ((cType.toLowerCase() === 'phone' || cType.toLowerCase() === 'whatsapp') && window.Attendees?.utilities?.normalizePhoneNumber) {
              cVal = window.Attendees.utilities.normalizePhoneNumber(cVal);
              const valInput = row.querySelector('.ob-contact-value');
              if (valInput) valInput.value = cVal;
            }
            attendeeContacts.push({ type: cType, value: cVal });
          }
        }
        const primaryAttendeeContact = attendeeContacts.length > 0 ? attendeeContacts[0] : null;

        // Kid-specific fields
        const grade = isKidMeet ? (block.querySelector('.ob-grade')?.value ?? '') : '';
        const foodPref = isKidMeet ? (block.querySelector('.ob-food-pref')?.value || '').trim() : '';
        const insurer = (isKidMeet && showInsurer) ? (block.querySelector('.ob-insurer')?.value || '').trim() : '';

        if (isKidMeet) {
          if (grade === '' || grade === undefined || grade === null) {
            DevExpress.ui.notify(`School Grade is required for ${attLabel}.`, 'warning', WARNING_NOTIFY_TIME);
            block.querySelector('.ob-grade')?.focus();
            return;
          }
          if (!foodPref) {
            DevExpress.ui.notify(`Food preference / allergies is required for ${attLabel} (enter "None" if none).`, 'warning', WARNING_NOTIFY_TIME);
            block.querySelector('.ob-food-pref')?.focus();
            return;
          }
        }

        attendeesList.push({
          first_name: firstName || null,
          last_name: lastName || null,
          first_name2: firstName2 || null,
          last_name2: lastName2 || null,
          gender: gender,
          division_id: divVal ? parseInt(divVal, 10) : null,
          relationship: relVal ? (parseInt(relVal, 10) || relVal) : 'self',
          birthday_year: byear ? parseInt(byear, 10) : null,
          birthday_month: bmonth ? parseInt(bmonth, 10) : null,
          birthday_day: bday ? parseInt(bday, 10) : null,
          contact_type: primaryAttendeeContact ? primaryAttendeeContact.type : 'phone',
          contact_value: primaryAttendeeContact ? primaryAttendeeContact.value : null,
          contacts: attendeeContacts,
          grade: grade !== '' ? grade : null,
          food_pref: foodPref || null,
          insurer: insurer || null,
        });
      }

      // 2. Collect and validate Companions
      let companionsList = [];
      const guardianSectionEl = rootDiv.querySelector('.guardian-section');
      const guardianContentEl = rootDiv.querySelector('.guardian-section-content');
      const isGuardianSectionVisible = guardianSectionEl && guardianSectionEl.style.display !== 'none';
      const isGuardianContentVisible = guardianContentEl && guardianContentEl.style.display !== 'none';

      // Find all visible companion blocks
      const allCompBlocks = Array.from(rootDiv.querySelectorAll('.companion-block'));
      const visibleCompBlocks = (isGuardianSectionVisible && isGuardianContentVisible && !isUnaccompanied)
        ? allCompBlocks.filter(b => b.style.display !== 'none')
        : [];

      if (isKidMeet) {
        if (!isUnaccompanied) {
          if (visibleCompBlocks.length === 0) {
            DevExpress.ui.notify('Companion information is required for kids unless "Child arrived alone" is checked.', 'warning', WARNING_NOTIFY_TIME);
            return;
          }
          for (let i = 0; i < visibleCompBlocks.length; i++) {
            const block = visibleCompBlocks[i];
            const compNum = i + 1;
            const pDivisionEl = block.querySelector('.ob-p-division');
            const pDivisionVal = pDivisionEl ? pDivisionEl.value : '';
            const pGenderEl = block.querySelector('.ob-p-gender');
            const pGenderVal = (pGenderEl ? pGenderEl.value : 'UNSPECIFIED').toUpperCase();
            const pRelEl = block.querySelector('.ob-p-relationship');
            const pRelVal = pRelEl ? pRelEl.value : 'parent';

            const pFirst = (block.querySelector('.ob-p-first-name')?.value || '').trim();
            const pLast = (block.querySelector('.ob-p-last-name')?.value || '').trim();
            const pFirst2 = (block.querySelector('.ob-p-first-name2')?.value || '').trim();
            const pLast2 = (block.querySelector('.ob-p-last-name2')?.value || '').trim();

            const compContactRows = Array.from(block.querySelectorAll('.companion-contacts-container .contact-row'));
            const compContacts = [];
            for (const cRow of compContactRows) {
              const ct = cRow.querySelector('.ob-p-contact-type')?.value || 'phone';
              let cv = (cRow.querySelector('.ob-p-contact-value')?.value || '').trim();
              if (cv) {
                const cvErr = getContactValidationError(ct, cv, `Companion ${compNum}`);
                if (cvErr) {
                  DevExpress.ui.notify(cvErr, 'warning', WARNING_NOTIFY_TIME);
                  cRow.querySelector('.ob-p-contact-value')?.focus();
                  return;
                }
                if ((ct.toLowerCase() === 'phone' || ct.toLowerCase() === 'whatsapp') && window.Attendees?.utilities?.normalizePhoneNumber) {
                  cv = window.Attendees.utilities.normalizePhoneNumber(cv);
                  const valInput = cRow.querySelector('.ob-p-contact-value');
                  if (valInput) valInput.value = cv;
                }
                compContacts.push({ type: ct, value: cv });
              }
            }

            const hasAnyName = Boolean(pFirst || pLast || pFirst2 || pLast2);
            const primaryCompContact = compContacts.length > 0 ? compContacts[0] : null;

            if (compNum === 1) {
              if (organizationDivisions.length > 0 && !pDivisionVal) {
                DevExpress.ui.notify('Please select a division for Companion 1.', 'warning', WARNING_NOTIFY_TIME);
                return;
              }
              if (!hasAnyName || compContacts.length === 0) {
                DevExpress.ui.notify('Companion 1 name and contact information are required.', 'warning', WARNING_NOTIFY_TIME);
                return;
              }
            } else {
              if (!hasAnyName && compContacts.length === 0) {
                DevExpress.ui.notify(`Companion ${compNum} name and contact information are required (or remove it).`, 'warning', WARNING_NOTIFY_TIME);
                return;
              }
              if (organizationDivisions.length > 0 && !pDivisionVal) {
                DevExpress.ui.notify(`Please select a division for Companion ${compNum}.`, 'warning', WARNING_NOTIFY_TIME);
                return;
              }
              if (!hasAnyName || compContacts.length === 0) {
                DevExpress.ui.notify(`Companion ${compNum} name and contact information are required.`, 'warning', WARNING_NOTIFY_TIME);
                return;
              }
            }

            companionsList.push({
              first_name: pFirst || null,
              last_name: pLast || null,
              first_name2: pFirst2 || null,
              last_name2: pLast2 || null,
              gender: pGenderVal,
              division_id: pDivisionVal ? parseInt(pDivisionVal, 10) : null,
              relationship: pRelVal ? (parseInt(pRelVal, 10) || pRelVal) : 'parent',
              contact_type: primaryCompContact ? primaryCompContact.type : 'phone',
              contact_value: primaryCompContact ? primaryCompContact.value : null,
              phone: primaryCompContact && primaryCompContact.type === 'phone' ? primaryCompContact.value : null,
              email: primaryCompContact && primaryCompContact.type === 'email' ? primaryCompContact.value : null,
              contacts: compContacts
            });
          }
        }
      } else {
        // Adult meet: companions are optional; contact is NOT mandatory for adult companions
        if (visibleCompBlocks.length > 0) {
          for (let i = 0; i < visibleCompBlocks.length; i++) {
            const block = visibleCompBlocks[i];
            const compNum = i + 1;
            const pDivisionEl = block.querySelector('.ob-p-division');
            const pDivisionVal = pDivisionEl ? pDivisionEl.value : '';
            const pGenderEl = block.querySelector('.ob-p-gender');
            const pGenderVal = (pGenderEl ? pGenderEl.value : 'UNSPECIFIED').toUpperCase();
            const pRelEl = block.querySelector('.ob-p-relationship');
            const pRelVal = pRelEl ? pRelEl.value : 'spouse';

            const pFirst = (block.querySelector('.ob-p-first-name')?.value || '').trim();
            const pLast = (block.querySelector('.ob-p-last-name')?.value || '').trim();
            const pFirst2 = (block.querySelector('.ob-p-first-name2')?.value || '').trim();
            const pLast2 = (block.querySelector('.ob-p-last-name2')?.value || '').trim();

            const compContactRows = Array.from(block.querySelectorAll('.companion-contacts-container .contact-row'));
            const compContacts = [];
            for (const cRow of compContactRows) {
              const ct = cRow.querySelector('.ob-p-contact-type')?.value || 'phone';
              let cv = (cRow.querySelector('.ob-p-contact-value')?.value || '').trim();
              if (cv) {
                const cvErr = getContactValidationError(ct, cv, `Companion ${compNum}`);
                if (cvErr) {
                  DevExpress.ui.notify(cvErr, 'warning', WARNING_NOTIFY_TIME);
                  cRow.querySelector('.ob-p-contact-value')?.focus();
                  return;
                }
                if ((ct.toLowerCase() === 'phone' || ct.toLowerCase() === 'whatsapp') && window.Attendees?.utilities?.normalizePhoneNumber) {
                  cv = window.Attendees.utilities.normalizePhoneNumber(cv);
                  const valInput = cRow.querySelector('.ob-p-contact-value');
                  if (valInput) valInput.value = cv;
                }
                compContacts.push({ type: ct, value: cv });
              }
            }

            const hasAnyName = Boolean(pFirst || pLast || pFirst2 || pLast2);
            const hasAnyContact = compContacts.length > 0;
            const primaryCompContact = compContacts.length > 0 ? compContacts[0] : null;

            // If it's the only companion block (Companion 1) and completely untouched/empty, skip it in adult meet
            if (visibleCompBlocks.length === 1 && !hasAnyName && !hasAnyContact) {
              continue;
            }

            if (!hasAnyName) {
              DevExpress.ui.notify(`Companion ${compNum} name is required (or remove it).`, 'warning', WARNING_NOTIFY_TIME);
              return;
            }
            if (organizationDivisions.length > 0 && !pDivisionVal) {
              DevExpress.ui.notify(`Please select a division for Companion ${compNum}.`, 'warning', WARNING_NOTIFY_TIME);
              return;
            }

            companionsList.push({
              first_name: pFirst || null,
              last_name: pLast || null,
              first_name2: pFirst2 || null,
              last_name2: pLast2 || null,
              gender: pGenderVal,
              division_id: pDivisionVal ? parseInt(pDivisionVal, 10) : null,
              relationship: pRelVal ? (parseInt(pRelVal, 10) || pRelVal) : 'spouse',
              contact_type: primaryCompContact ? primaryCompContact.type : 'phone',
              contact_value: primaryCompContact ? primaryCompContact.value : null,
              phone: primaryCompContact && primaryCompContact.type === 'phone' ? primaryCompContact.value : null,
              email: primaryCompContact && primaryCompContact.type === 'email' ? primaryCompContact.value : null,
              contacts: compContacts
            });
          }
        }
      }

      const gatheringSelect = rootDiv.querySelector('.target-gathering-dropdown');
      const gatheringId = gatheringSelect ? (gatheringSelect.value || selectedGatheringId || null) : (selectedGatheringId || null);

      const payload = {
        meet_slug: meet.slug,
        gathering_id: gatheringId,
        unaccompanied: isUnaccompanied,
        attendees_data: attendeesList,
        companions: companionsList,
      };

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Registering...';

      if (window.Attendees && window.Attendees.utilities) {
        window.Attendees.utilities.editingEnabled = true;
      }

      try {
        const response = await fetch(endpoints.fastOnboard, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
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
        const registeredNames = (result.attendees && result.attendees.length > 1)
          ? result.attendees.map(a => a.attendee_name).join(', ')
          : (result.attendee_name || 'attendee');
        DevExpress.ui.notify(`Registered ${registeredNames} and checked in successfully!`, 'success', 3000);
        if (popupInstance) popupInstance.hide();
        await loadData(result.attendee_id, result.gathering_id || gatheringId);
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', WARNING_NOTIFY_TIME);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Register & Check In';
        if (window.Attendees && window.Attendees.utilities) {
          window.Attendees.utilities.editingEnabled = false;
        }
      }
    };

    const initAddAttendeePopup = () => {
      const popupEl = document.getElementById('add-attendee-popup');
      if (!popupEl) return;

      document.addEventListener('keydown', (e) => {
        if ((e.key === 'Escape' || e.keyCode === 27) && popupInstance && popupInstance.option('visible')) {
          popupInstance.hide();
        }
      });

      const isMobile = window.innerWidth < 768;
      popupInstance = new DevExpress.ui.dxPopup(popupEl, {
        showCloseButton: true,
        dragEnabled: !isMobile,
        wrapperAttr: {
          class: 'add-attendee-popup-wrapper'
        },
        titleTemplate: (titleElement) => {
          const titleEl = (titleElement && titleElement[0]) ? titleElement[0] : titleElement;
          titleEl.innerHTML = `
            <div class="d-flex align-items-center justify-content-between popup-title-container w-100">
              <div class="d-flex align-items-center flex-grow-1 overflow-hidden me-2">
                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 me-2 back-to-search-btn d-none" title="Back to Search">
                  <i class="fas fa-arrow-left"></i>
                </button>
                <span class="popup-title-text fw-bold text-dark text-truncate">Add Attendee to Rosters, Welcome! Let's search first.</span>
              </div>
              <button type="button" class="btn-close popup-close-btn dx-closebutton flex-shrink-0" aria-label="Close" title="Close"></button>
            </div>
          `;
          const backBtn = titleEl.querySelector('.back-to-search-btn');
          if (backBtn) {
            backBtn.addEventListener('click', () => {
              if (typeof currentSwitchToSearch === 'function') {
                currentSwitchToSearch();
              }
            });
          }
          const closeBtn = titleEl.querySelector('.popup-close-btn');
          if (closeBtn) {
            closeBtn.addEventListener('click', () => {
              if (popupInstance) {
                popupInstance.hide();
              }
            });
          }
        },
        onShowing: () => {
          if (window.Attendees && window.Attendees.utilities) {
            window.Attendees.utilities.editingEnabled = true;
          }
        },
        onShown: () => {
          setTimeout(() => {
            const rawContent = popupInstance.content ? popupInstance.content() : null;
            const content = (rawContent && rawContent[0]) ? rawContent[0] : (rawContent || document.getElementById('add-attendee-popup'));
            const searchInput = content ? content.querySelector('.omni-search-box') : null;
            if (searchInput) {
              searchInput.focus();
              searchInput.select();
            }
          }, 50);
        },
        onHiding: () => {
          if (typeof currentSwitchToSearch === 'function') {
            currentSwitchToSearch();
          }
          if (window.Attendees && window.Attendees.utilities) {
            window.Attendees.utilities.editingEnabled = false;
          }
        },
        contentTemplate: (container) => {
          const el = (container && container[0]) ? container[0] : container;
          renderPopupContent(el);
        }
      });
    };

    const openAddAttendeePopup = () => {
      if (!filterData.meets || filterData.meets.length === 0) {
        DevExpress.ui.notify('Please select at least one meet in the filter first.', 'warning', WARNING_NOTIFY_TIME);
        return;
      }

      const highlighted = (typeof getHighlightedGathering === 'function') ? getHighlightedGathering() : null;
      let meetFromHighlight = null;
      if (highlighted && highlighted.meet_id) {
        meetFromHighlight = Array.from(meetsMap.values()).find(m => String(m.id) === String(highlighted.meet_id));
      }

      if (meetFromHighlight && filterData.meets.includes(meetFromHighlight.slug)) {
        selectedMeetSlug = meetFromHighlight.slug;
        selectedGatheringId = highlighted.id || null;
      } else {
        selectedMeetSlug = filterData.meets[0];
        const currentMeet = meetsMap.get(selectedMeetSlug) || meetsMap.get(String(selectedMeetSlug));
        const meetGatherings = currentMeet ? getGatheringsForMeet(currentMeet.id) : [];
        if (highlighted && highlighted.id && meetGatherings.some(g => String(g.id) === String(highlighted.id))) {
          selectedGatheringId = highlighted.id;
        } else {
          const upcoming = getUpcomingOrOngoingGathering(meetGatherings);
          selectedGatheringId = upcoming ? upcoming.id : (meetGatherings.length > 0 ? meetGatherings[0].id : null);
        }
      }

      if (!popupInstance) {
        initAddAttendeePopup();
      } else {
        const rawContent = popupInstance.content ? popupInstance.content() : null;
        const contentEl = (rawContent && rawContent[0]) ? rawContent[0] : rawContent;
        if (contentEl) renderPopupContent(contentEl);
      }
      if (popupInstance) {
        if (typeof currentSwitchToSearch === 'function') {
          currentSwitchToSearch();
        }
        popupInstance.show();
        setTimeout(() => {
          const rawContent = popupInstance.content ? popupInstance.content() : null;
          const content = (rawContent && rawContent[0]) ? rawContent[0] : (rawContent || document.getElementById('add-attendee-popup'));
          const searchInput = content ? content.querySelector('.omni-search-box') : null;
          if (searchInput) {
            searchInput.focus();
            searchInput.select();
          }
        }, 50);
      }
    };

    return {
      initAddAttendeePopup,
      openAddAttendeePopup
    };
  }

  // ==========================================================
  // 7. App Initialization (Main)
  // ==========================================================
  const RostersApp = {
    setup() {
      console.log('static/js/occasions/rosters_list_view.js Composition API loaded!');
      Attendees.utilities.clearGridStatesInSessionStorage(Attendees.utilities.datagridStorageKeys['rostersListView']);

      const storageOptsKey = Attendees.utilities.datagridStorageKeys['rostersListViewOpts'];
      const storedMeets = Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'selectedMeetSlugs');
      const storedFrom = Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'filterFromString');
      const storedTill = Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'filterTillString');
      const storedShowPhotos = Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'showPhotos');

      const defaultStartDate = new Date(new Date().setMonth(new Date().getMonth() - 3));
      const defaultEndDate = new Date(new Date().setMonth(new Date().getMonth() + 1));
      let initialStart = defaultStartDate;
      if (storedFrom) {
        const d = new Date(storedFrom);
        if (!isNaN(d.getTime())) initialStart = d;
      }
      let initialEnd = defaultEndDate;
      if (storedTill) {
        const d = new Date(storedTill);
        if (!isNaN(d.getTime())) initialEnd = d;
      }

      // DOM Refs
      const filterFormRef = ref(null);
      const dataGridRef = ref(null);
      const gridInstanceRef = ref(null); // Keep a ref to the DevExtreme Grid instance

      // Global App State
      const filterData = reactive({
        meets: Array.isArray(storedMeets) ? storedMeets : [],
        startDate: initialStart,
        endDate: initialEnd,
        showPhotos: storedShowPhotos === true || storedShowPhotos === 'true'
      });

      // Composables Hookup
      const { endpoints, initEndpoints } = useEndpoints();
      const attendanceLogic = useAttendanceLogic(endpoints, gridInstanceRef);
      const attendingMeetsEditor = useAttendingMeetsEditor(endpoints, gridInstanceRef, filterData);
      const resetFiltersRef = { current: null };
      const { initDataGrid, loadData, getHighlightedGathering, highlightGatheringColumn } = useRosterGrid(
        endpoints, 
        filterData, 
        gridInstanceRef, 
        attendanceLogic, 
        attendingMeetsEditor,
        () => { if (resetFiltersRef.current) resetFiltersRef.current(); }
      );
      const { initFilterForm, resetFilters } = useRosterFilter(endpoints, filterData, loadData, gridInstanceRef);
      resetFiltersRef.current = resetFilters;

      const { startPolling, stopPolling } = useSmartPolling(gridInstanceRef, filterData);
      const { initAddAttendeePopup, openAddAttendeePopup } = useAddAttendee(endpoints, filterData, gridInstanceRef, loadData, getHighlightedGathering, highlightGatheringColumn);

      // Lifecycle
      onMounted(() => {
        initEndpoints();
        if (attendanceLogic && typeof attendanceLogic.initSignaturePopup === 'function') {
          attendanceLogic.initSignaturePopup();
        }
        if (attendingMeetsEditor && typeof attendingMeetsEditor.preloadLookups === 'function') {
          attendingMeetsEditor.preloadLookups();
        }
        initAddAttendeePopup();

        const addAttendeeBtn = document.querySelector('a.add-attendee');
        if (addAttendeeBtn) {
          addAttendeeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openAddAttendeePopup();
          });
        }

        if (dataGridRef.value) initDataGrid(dataGridRef.value);
        if (filterFormRef.value) initFilterForm(filterFormRef.value);
        if (filterData.meets && filterData.meets.length > 0) {
          loadData();
        }

        startPolling();
      });

      return { 
        filterFormRef, 
        dataGridRef,
        filterData 
      };
    }
  };

  window.addEventListener('load', () => {
    createApp(RostersApp).mount('#app');
  });
})();
