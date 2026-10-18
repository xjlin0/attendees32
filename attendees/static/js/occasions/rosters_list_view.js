;(() => {
  const { createApp, ref, reactive, onMounted } = Vue;

  // Shared registry of gatherings for columns:
  const gatheringsRegistry = new Map();

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
        start: gathering.start,
        finish: gathering.finish
      };
      if (meetStartKey) gatheringsRegistry.set(meetStartKey, existing);
    } else {
      if (gathering.id && !existing.id) {
        existing.id = gathering.id;
      }
      if (gathering.meet_id && !existing.meet_id) existing.meet_id = gathering.meet_id;
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

  // ==========================================================
  // 1. Endpoints Logic
  // ==========================================================
  function useEndpoints() {
    const endpoints = reactive({
      rosters: '',
      meets: '',
      attendances: '/occasions/api/organization_meet_character_attendances/',
      assemblies: '',
      categories: '',
      attendingmeets: '',
      attendings: '',
      characters: '',
      teams: ''
    });

    const initEndpoints = () => {
      const appEl = document.getElementById('app');
      if (appEl) {
        endpoints.rosters = appEl.dataset.rostersEndpoint || '';
        endpoints.meets = appEl.dataset.meetsEndpointBySlug || '';
        endpoints.assemblies = appEl.dataset.assembliesEndpoint || '';
        endpoints.categories = appEl.dataset.categoriesEndpoint || '';
        endpoints.attendingmeets = appEl.dataset.attendingmeetsEndpoint || '';
        endpoints.attendings = appEl.dataset.attendingsEndpoint || '';
        endpoints.characters = appEl.dataset.charactersEndpoint || '';
        endpoints.teams = appEl.dataset.teamsEndpoint || '';
      }
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

    const isAttendingValid = (rowData, gathering) => {
      if (!rowData.attendingmeets || !rowData.attendingmeets.length) return true; 
      return !!getActiveAttendingMeet(rowData, gathering);
    };

    const toggleAttendance = async (rowData, gathering, domElements, rowIndex, colName) => {
      const gatheringMeta = (gathering && typeof gathering === 'object') ? gathering : null;
      let gatheringId = gatheringMeta ? gatheringMeta.id : gathering;
      let record = getAttendanceRecord(rowData, gatheringId);
      const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);
      const newCategory = isCurrentlyCheckedIn ? 1 : 9; 

      const activeAm = getActiveAttendingMeet(rowData, gatheringMeta || gathering);
      const attendingId = activeAm ? activeAm.attending_id : (rowData.attending_id || (rowData.attendingmeets && rowData.attendingmeets[0] ? rowData.attendingmeets[0].attending_id : null));
      const characterId = activeAm ? activeAm.character_id : (rowData.attendingmeets && rowData.attendingmeets[0] ? rowData.attendingmeets[0].character_id : 1);

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
          start: updatedRecord.start,
          finish: updatedRecord.finish
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
            if (domElements.checkInBtn) {
              domElements.checkInBtn.className = 'roster-btn checked-in';
              domElements.checkInBtn.innerText = 'Checked In';
            }
            if (domElements.outBtn) {
              domElements.outBtn.style.display = 'inline-block';
              domElements.outBtn.className = 'roster-btn roster-btn-out';
              domElements.outBtn.innerText = 'Out';
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
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }
    };

    const markOut = async (rowData, gathering, domElements, rowIndex) => {
      const gatheringMeta = (gathering && typeof gathering === 'object') ? gathering : null;
      const gatheringId = gatheringMeta ? gatheringMeta.id : gathering;
      const record = getAttendanceRecord(rowData, gatheringId);
      if (!record) return;

      const isCurrentlyCheckedOut = !!record.finish;
      const newFinish = isCurrentlyCheckedOut ? null : new Date().toISOString();

      try {
        const recordId = record.attendance_id || record.id;
        const response = await fetch(`${endpoints.attendances}${recordId}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify({
            finish: newFinish
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || errData.error || 'Failed to mark out');
        }
        const updatedRecord = await response.json();

        const normalizedRecord = {
          attendance_id: updatedRecord.id,
          gathering_id: updatedRecord.gathering,
          category_id: updatedRecord.category,
          start: updatedRecord.start,
          finish: updatedRecord.finish
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

        if (gridInstanceRef.value) {
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
              const existingRec = gridRowData.attendances.find(a => a && String(a.gathering_id) === String(updatedRecord.gathering));
              if (existingRec) {
                Object.assign(existingRec, normalizedRecord);
              } else {
                gridRowData.attendances.push(normalizedRecord);
              }
            }
          }
        }
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }
    };

    return { isAttendingValid, isCheckedIn, isCheckedOut, toggleAttendance, markOut };
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
            if (m.id !== undefined && m.id !== null && m.display_name) {
              lookupsCache.meetNames[m.id] = m.display_name;
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
        DevExpress.ui.notify('Please check required fields', 'warning', 2500);
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
        DevExpress.ui.notify(`Save failed: ${saveErr.message}`, 'error', 3000);
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
        DevExpress.ui.notify(`Error loading enrollments: ${err.message}`, 'error', 3000);
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
          width: popupWidth,
          height: popupHeight,
          maxHeight: '90vh',
          fullScreen: false,
          wrapperAttr: {
            class: 'attendingmeets-popup-wrapper'
          },
          showCloseButton: true,
          dragEnabled: !isMobile,
          toolbarItems: toolbarItems,
          contentTemplate: (container) => {
            renderPopupContent(container[0]);
          }
        });
      } else {
        popupInstance.option({
          title: popupTitle,
          width: popupWidth,
          height: popupHeight,
          maxHeight: '90vh',
          fullScreen: false,
          wrapperAttr: {
            class: 'attendingmeets-popup-wrapper'
          },
          dragEnabled: !isMobile,
          toolbarItems: toolbarItems
        });
        const contentEl = popupInstance.content ? popupInstance.content()[0] : null;
        if (contentEl) {
          renderPopupContent(contentEl);
        }
      }

      popupInstance.show();
    };

    return { openAttendingMeetsPopup };
  }

  // ==========================================================
  // 4. Grid View Logic
  // ==========================================================
  function useRosterGrid(endpoints, filterData, gridInstanceRef, attendanceLogic, attendingMeetsEditor) {
    const formatDate = (dateString) => {
      if (!dateString) return '';
      const d = new Date(dateString);
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
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

      wrapper.innerHTML = `
        ${photoHtml}
        <span class="attendee-links-container">
          <u><a href="/persons/attendee/${data.attendee_id}" target="_blank" class="attendee-info-link" title="Click to open a new page of attendee info">(Info)</a></u>
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

    const attendanceCellTemplate = (container, options) => {
      const data = options.data;
      const colName = options.column.name;
      const colMeta = options.column.gatheringMeta;
      const meetStartKey = (colMeta && colMeta.meet_id && colMeta.start) ? `${colMeta.meet_id}_${colMeta.start}` : '';
      const gatheringMeta = gatheringsRegistry.get(colName) || (meetStartKey && gatheringsRegistry.get(meetStartKey)) || colMeta;
      
      const wrapper = document.createElement('div');
      wrapper.className = 'text-center roster-cell-wrapper';

      if (!attendanceLogic.isAttendingValid(data, gatheringMeta)) {
        wrapper.innerHTML = `<span class="not-attending-text">Not Attending</span>`;
        container.append(wrapper);
        return;
      }

      const gatheringId = gatheringMeta && gatheringMeta.id;
      const checkedIn = gatheringId ? attendanceLogic.isCheckedIn(data, gatheringId) : false;
      const checkedOut = gatheringId ? attendanceLogic.isCheckedOut(data, gatheringId) : false;

      const checkInBtn = document.createElement('button');
      checkInBtn.className = `roster-btn ${checkedIn ? 'checked-in' : ''}`;
      checkInBtn.innerText = checkedIn ? 'Checked In' : 'Check In';

      const outBtn = document.createElement('button');
      outBtn.className = `roster-btn roster-btn-out ${checkedOut ? 'checked-out' : ''}`;
      outBtn.innerText = checkedOut ? 'Checked Out' : 'Out';
      if (!checkedIn) {
        outBtn.style.display = 'none';
      }

      const domElements = { wrapper, checkInBtn, outBtn };

      checkInBtn.addEventListener('click', () => {
        attendanceLogic.toggleAttendance(data, gatheringMeta, domElements, options.rowIndex, colName);
      });

      outBtn.addEventListener('click', () => {
        attendanceLogic.markOut(data, gatheringMeta, domElements, options.rowIndex);
      });

      wrapper.appendChild(checkInBtn);
      wrapper.appendChild(outBtn);
      container.append(wrapper);
    };

    const updateGridColumns = (serverColumns, rows = []) => {
      const currentCols = gridInstanceRef.value.option('columns');
      let colsChanged = false;
      
      const FIXED_PREFIX_COUNT = 4;
      const TOTAL_EXTRA_COLS = FIXED_PREFIX_COUNT + 1; // plus 1 dummy-column

      if (!currentCols || currentCols.length !== serverColumns.length + TOTAL_EXTRA_COLS) {
        colsChanged = true;
      } else {
        for (let i = 0; i < serverColumns.length; i++) {
          if (currentCols[i + FIXED_PREFIX_COUNT].name !== getColumnIdentifier(serverColumns[i])) {
            colsChanged = true;
            break;
          }
        }
      }

      if (colsChanged) {
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
            width: 140,
            allowSorting: true,
            allowHiding: true
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

        serverColumns.forEach(gathering => {
          const registered = registerGathering(gathering);
          const gid = registered.id;
          const hasCheckedIn = gid && rows.some(r => attendanceLogic.isCheckedIn(r, gid));
          const colWidth = hasCheckedIn ? 150 : 100;

          columns.push({
            name: getColumnIdentifier(registered),
            caption: formatDate(registered.start),
            alignment: 'center',
            width: colWidth,
            minWidth: colWidth,
            gatheringMeta: registered,
            cellTemplate: attendanceCellTemplate
          });
        });

        columns.push({
          caption: '',
          cssClass: 'dummy-column',
          allowHiding: false,
          showInColumnChooser: false
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
        });
      }
    };

    const loadData = async () => {
      if (!filterData.meets || !filterData.meets.length) {
        if (gridInstanceRef.value) {
          gridInstanceRef.value.option('dataSource', []);
        }
        return; 
      }

      if (gridInstanceRef.value) {
        try {
          if (typeof gridInstanceRef.value.beginCustomLoading === 'function') {
            gridInstanceRef.value.beginCustomLoading();
          }

          const queryParams = new URLSearchParams();
          filterData.meets.forEach(meet => queryParams.append('meets[]', meet));
          
          if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
          if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

          queryParams.set('skip', 0);
          queryParams.set('take', 40);

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
                  return {
                    data: cached.data || cached.rows,
                    totalCount: cached.totalCount
                  };
                }

                const pageParams = new URLSearchParams();
                filterData.meets.forEach(meet => pageParams.append('meets[]', meet));
                
                if (filterData.startDate) pageParams.set('start', filterData.startDate.toISOString());
                if (filterData.endDate) pageParams.set('finish', filterData.endDate.toISOString());

                pageParams.set('skip', loadOptions.skip || 0);
                pageParams.set('take', loadOptions.take || 40);

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
                DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', 3000);
                console.error(error);
                throw error; 
              }
            }
          });

          gridInstanceRef.value.beginUpdate();
          gatheringsRegistry.clear();
          updateGridColumns(initialData.columns, initialData.data || initialData.rows || []);
          gridInstanceRef.value.option('dataSource', customStore);
          gridInstanceRef.value.endUpdate();

        } catch (error) {
          DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', 3000);
          console.error(error);
        } finally {
          if (typeof gridInstanceRef.value.endCustomLoading === 'function') {
            gridInstanceRef.value.endCustomLoading();
          }
        }
      }
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
        grouping: {
          autoExpandAll: true,
        },
        groupPanel: {
          visible: true,
        },
        searchPanel: {
          visible: true,
          width: 250,
          placeholder: 'Search name, contacts, team...',
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
              hint: 'Reset Sort/Group/Columns settings',
              icon: 'clearsquare',
              onClick() {
                if (gridInstanceRef.value) {
                  gridInstanceRef.value.state(null);
                }
              }
            }
          });
        }
      });
    };

    return { initDataGrid, loadData };
  }

  // ==========================================================
  // 4. Filters Form Logic
  // ==========================================================
  function useRosterFilter(endpoints, filterData, reloadCallback, gridInstanceRef) {
    let formInstance = null;

    const initFilterForm = (filterFormEl) => {
      formInstance = new DevExpress.ui.dxForm(filterFormEl, {
        formData: filterData,
        colCount: 4,
        onFieldDataChanged: (e) => {
          filterData[e.dataField] = e.value;
          
          // Date Validation constraints
          if (e.dataField === 'startDate') {
            formInstance.getEditor('endDate').option('min', e.value);
          }
          if (e.dataField === 'endDate') {
            formInstance.getEditor('startDate').option('max', e.value);
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
              dataSource: new DevExpress.data.DataSource({
                store: new DevExpress.data.CustomStore({
                  key: 'slug',
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

                    // Backend (Utility.transform_result) already formats groups as { key, items }
                    return json.data || json.results || json;
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

    return { initFilterForm };
  }

  // ==========================================================
  // 5. App Initialization (Main)
  // ==========================================================
  const RostersApp = {
    setup() {
      console.log('static/js/occasions/rosters_list_view.js Composition API loaded!');

      // DOM Refs
      const filterFormRef = ref(null);
      const dataGridRef = ref(null);
      const gridInstanceRef = ref(null); // Keep a ref to the DevExtreme Grid instance

      // Global App State
      const filterData = reactive({
        meets: [],
        startDate: new Date(new Date().setMonth(new Date().getMonth() - 3)),
        endDate: new Date(new Date().setMonth(new Date().getMonth() + 1)),
        showPhotos: false
      });

      // Composables Hookup
      const { endpoints, initEndpoints } = useEndpoints();
      const attendanceLogic = useAttendanceLogic(endpoints, gridInstanceRef);
      const attendingMeetsEditor = useAttendingMeetsEditor(endpoints, gridInstanceRef, filterData);
      const { initDataGrid, loadData } = useRosterGrid(endpoints, filterData, gridInstanceRef, attendanceLogic, attendingMeetsEditor);
      const { initFilterForm } = useRosterFilter(endpoints, filterData, loadData, gridInstanceRef);

      // Lifecycle
      onMounted(() => {
        initEndpoints();
        if (filterFormRef.value) initFilterForm(filterFormRef.value);
        if (dataGridRef.value) initDataGrid(dataGridRef.value);
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
