import { Ref } from 'vue';
import { Endpoints, FilterState, Gathering } from '../types';
import {
  escapeHtml,
  isValidDate,
  isProgrammaticGradeChange,
  setIsProgrammaticGradeChange,
  setUserGradeVisiblePreference,
  resolveGradeVisible,
  getColumnIdentifier,
  formatAttendanceDisplay,
  registerGathering,
  loadGradeConverter,
  sharedGradeConverter,
  gatheringsRegistry,
  meetsInfoMap,
  WARNING_NOTIFY_TIME
} from './useLookups';
import dxDataGrid from 'devextreme/ui/data_grid';
import dxSelectBox from 'devextreme/ui/select_box';
import dxPopup from 'devextreme/ui/popup';
import dxButton from 'devextreme/ui/button';
import notify from 'devextreme/ui/notify';
import { exportDataGrid } from 'devextreme/excel_exporter';

export function useRosterGrid(endpoints, filterData, gridInstanceRef, attendanceLogic, attendingMeetsEditor, onResetCallback) {
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
    let lastNewcomer = null;
    let newcomerPopupInstance = null;

    const setLastNewcomer = (info) => {
      lastNewcomer = info;
      renderFooterNewcomer();
    };

    const clearLastNewcomer = () => {
      lastNewcomer = null;
      renderFooterNewcomer();
    };

    const locateAttendeeInGrid = (newcomer) => {
      if (!gridInstanceRef.value || !newcomer) return;
      if (!filterData.meets || filterData.meets.length === 0) {
        DevExpress.ui.notify({
          message: 'Please select a meet first to locate attendee in roster.',
          type: 'warning',
          displayTime: 3500
        });
        return;
      }
      if (newcomer.meetSlug && !filterData.meets.includes(newcomer.meetSlug)) {
        DevExpress.ui.notify({
          message: `Cannot locate attendee because "${newcomer.meetName || newcomer.meetSlug}" is not selected in the filter.`,
          type: 'warning',
          displayTime: 3500
        });
        return;
      }
      const rawId = newcomer.id != null ? newcomer.id : newcomer.attendee_id;
      const numId = Number(rawId);
      const targetId = !isNaN(numId) ? numId : rawId;

      const getRowIndex = () => {
        let idx = gridInstanceRef.value.getRowIndexByKey(targetId);
        if (idx < 0 && typeof targetId === 'number') idx = gridInstanceRef.value.getRowIndexByKey(String(targetId));
        if (idx < 0 && !isNaN(numId)) idx = gridInstanceRef.value.getRowIndexByKey(numId);
        return idx;
      };

      const applySelectionAndVisuals = () => {
        try {
          const keysToSelect = [targetId];
          if (typeof targetId === 'number') keysToSelect.push(String(targetId));
          gridInstanceRef.value.selectRows(keysToSelect, false);
          const rIdx = getRowIndex();
          if (rIdx >= 0) {
            const rowEl = gridInstanceRef.value.getRowElement(rIdx);
            const domEl = rowEl && (rowEl[0] || (rowEl.length ? rowEl[0] : rowEl));
            if (domEl) {
              if (typeof domEl.scrollIntoView === 'function') {
                domEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
              domEl.classList.add('roster-row-newly-added');
              setTimeout(() => domEl.classList.remove('roster-row-newly-added'), 3500);
            }
          }
        } catch (e) {
          console.warn('Error applying row selection:', e);
        }
      };

      // 1. Check if the attendee is already on the current visible page
      const rowIndex = getRowIndex();
      if (rowIndex >= 0) {
        applySelectionAndVisuals();
        DevExpress.ui.notify(`Located: ${newcomer.name}. Clear search bar to show all attendees.`, 'success', 2000);
        return;
      }

      // 2. If not on current page, filter grid to this newcomer
      if (typeof gridInstanceRef.value.searchByText === 'function') {
        const onContentReady = () => {
          gridInstanceRef.value.off('contentReady', onContentReady);
          applySelectionAndVisuals();
        };
        gridInstanceRef.value.on('contentReady', onContentReady);
        gridInstanceRef.value.searchByText(newcomer.name);
        DevExpress.ui.notify(`Filtered roster for: ${newcomer.name}`, 'info', 2500);
      }
    };

    const showNewcomerCard = (newcomer) => {
      if (!newcomer) return;
      let container = document.getElementById('roster-newcomer-popup');
      if (!container) {
        container = document.createElement('div');
        container.id = 'roster-newcomer-popup';
        document.body.appendChild(container);
      }

      if (newcomerPopupInstance) {
        newcomerPopupInstance.dispose();
      }

      const gradeText = (newcomer.grade !== '' && newcomer.grade !== undefined && newcomer.grade !== null)
        ? (window.Attendees?.utilities?.gradeNames ? window.Attendees.utilities.gradeNames[newcomer.grade] || `Grade ${newcomer.grade}` : `Grade ${newcomer.grade}`)
        : '';

      newcomerPopupInstance = new DevExpress.ui.dxPopup(container, {
        width: window.innerWidth < 768 ? '80%' : '30%',
        minWidth: 320,
        height: 'auto',
        showTitle: true,
        title: 'Newcomer Added',
        showCloseButton: true,
        dragEnabled: true,
        wrapperAttr: {
          class: 'newcomer-card-popup'
        },
        onShowing: (e) => {
          const updateWidth = () => {
            if (e.component) {
              e.component.option('width', window.innerWidth < 768 ? '80%' : '30%');
            }
          };
          window.addEventListener('resize', updateWidth);
          e.component.on('hiding', () => window.removeEventListener('resize', updateWidth));
          e.component.on('disposing', () => window.removeEventListener('resize', updateWidth));
        },
        contentTemplate: (contentEl) => {
          contentEl.innerHTML = `
            <div class="newcomer-card-body p-2">
              <div class="d-flex align-items-center mb-3">
                <div class="avatar-circle bg-success-subtle text-success border border-success-subtle rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 42px; height: 42px; font-weight: bold; font-size: 1.1em;">
                  <i class="fas fa-user-check"></i>
                </div>
                <div class="flex-grow-1 overflow-hidden">
                  <div class="fw-bold text-truncate fs-6" title="${escapeHtml(newcomer.name)}">${escapeHtml(newcomer.name)}</div>
                  <div class="text-muted small">${escapeHtml(newcomer.gender || '')}${gradeText ? ` · ${escapeHtml(gradeText)}` : ''}</div>
                </div>
              </div>
              
              <div class="mb-3 p-2 bg-light rounded border">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="text-secondary small"><i class="fas fa-calendar-check me-1"></i>Meet:</span>
                  <span class="fw-semibold small">${escapeHtml(newcomer.meetName || newcomer.meetSlug || 'Unknown')}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="text-secondary small"><i class="fas fa-user-tag me-1"></i>Character:</span>
                  <span class="fw-semibold small">${escapeHtml(newcomer.character || 'Attendee')}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="text-secondary small"><i class="fas fa-users me-1"></i>Team:</span>
                  <span class="fw-semibold small">${escapeHtml(newcomer.team || 'Unassigned')}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                  <span class="text-secondary small"><i class="fas fa-check-circle me-1 text-success"></i>Status:</span>
                  <span class="badge bg-success-subtle text-success border border-success"><i class="fas fa-check me-1"></i>Checked In</span>
                </div>
              </div>

              <div class="d-grid gap-2">
                <button type="button" class="btn btn-outline-primary btn-sm btn-locate-in-roster">
                  <i class="fas fa-search me-1"></i>Locate in Roster
                </button>
                <button type="button" class="btn btn-secondary btn-sm btn-close-newcomer-card">
                  Close
                </button>
              </div>
            </div>
          `;

          contentEl.querySelector('.btn-close-newcomer-card')?.addEventListener('click', () => {
            newcomerPopupInstance.hide();
          });

          contentEl.querySelector('.btn-locate-in-roster')?.addEventListener('click', () => {
            newcomerPopupInstance.hide();
            locateAttendeeInGrid(newcomer);
          });
        }
      });

      newcomerPopupInstance.show();
    };

    const renderFooterNewcomer = () => {
      const cells = document.querySelectorAll('.roster-footer-newcomer-cell');
      if (!cells || cells.length === 0) return;

      cells.forEach(cell => {
        const targetEl = cell.querySelector('.dx-datagrid-summary-item') || cell;
        if (!lastNewcomer) {
          targetEl.innerHTML = '';
          return;
        }

        targetEl.innerHTML = `
          <div class="roster-footer-newcomer-pill" title="Last added record, click to view details">
            <i class="fas fa-address-card text-warning me-1"></i>
            <span class="roster-footer-newcomer-name">${escapeHtml(lastNewcomer.name || 'New Attendee')}</span>
            <span class="badge bg-success text-white ms-1 px-1 py-0" style="font-size: 0.7em;" title="Checked in"><i class="fas fa-check"></i></span>
            <button type="button" class="roster-footer-newcomer-close ms-2" aria-label="Dismiss" title="Dismiss">&times;</button>
          </div>
        `;

        const closeBtn = targetEl.querySelector('.roster-footer-newcomer-close');
        if (closeBtn) {
          closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            clearLastNewcomer();
          });
        }

        const pill = targetEl.querySelector('.roster-footer-newcomer-pill');
        if (pill) {
          pill.addEventListener('click', (e) => {
            if (e.target.closest('.roster-footer-newcomer-close')) return;
            showNewcomerCard(lastNewcomer);
          });
        }
      });
    };

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
      const regMeta = (options.column.name && gatheringsRegistry.get(options.column.name))
        || (options.column.gatheringMeta && options.column.gatheringMeta.id && gatheringsRegistry.get(String(options.column.gatheringMeta.id)))
        || options.column.gatheringMeta;
      const colMeta = regMeta || options.column.gatheringMeta;
      const colIdx = options.column.colIndex !== undefined ? options.column.colIndex : (options.columnIndex - 5);
      const isMultiMeet = filterData && filterData.meets && filterData.meets.length > 1;
      const meetName = (colMeta && colMeta.meet_display_name)
        || (colMeta && colMeta.meet_id && meetsInfoMap.get(colMeta.meet_id))
        || (colMeta && colMeta.meet_id && meetsInfoMap.get(String(colMeta.meet_id)))
        || '';
      const timeStr = formatDate(colMeta ? colMeta.start : '');
      const count = (colMeta && colMeta.attendances_count !== undefined) ? colMeta.attendances_count : 0;
      const enrolled = (colMeta && colMeta.enrolled_count !== undefined) ? colMeta.enrolled_count : null;
      const displayCount = formatAttendanceDisplay(count, enrolled);
      const colId = options.column.name || (colMeta ? getColumnIdentifier(colMeta) : '');

      const wrapper = document.createElement('div');
      wrapper.className = 'text-center roster-header-cell';
      wrapper.style.cursor = 'pointer';
      if (isMultiMeet && meetName) {
        wrapper.innerHTML = `<div class="roster-header-meet">${meetName}</div><div class="roster-header-time">${timeStr}</div><div class="roster-header-count" data-col-id="${colId}">(${displayCount})</div>`;
      } else {
        wrapper.innerHTML = `<div class="roster-header-time single">${timeStr}</div><div class="roster-header-count" data-col-id="${colId}">(${displayCount})</div>`;
      }

      wrapper.addEventListener('click', () => {
        highlightColumn(colIdx, colMeta);
      });

      container.innerHTML = '';
      container.appendChild(wrapper);
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

      let siblingsHtml = '';
      if (filterData.showSiblings && Array.isArray(data.siblings) && data.siblings.length > 0) {
        const siblingLines = data.siblings.map(s => {
          const colorClass = s.attending ? 'text-success fw-semibold' : 'text-muted';
          return `<div class="attendee-sibling-item text-truncate" title="${s.name} (${s.attending ? 'Attending' : 'Not attending'})"><span class="text-secondary me-1" style="font-size: 0.85em;">👥</span><u class="sibling-search-link ${colorClass}" role="button" data-name="${s.name}" title="Click to search this sibling in the roster">${s.name}</u></div>`;
        }).join('');
        siblingsHtml = `<div class="attendee-siblings">${siblingLines}</div>`;
      }

      wrapper.innerHTML = `
        ${photoHtml}
        <div class="attendee-links-container" style="min-width: 0;">
          <div class="attendee-primary-line text-truncate">
            ${warningHtml}<u><a href="/persons/attendee/${data.attendee_id}" target="_blank" class="attendee-info-link" title="Click to open a new page of attendee info">(Info)</a></u>
            <u class="attendee-name-link" role="button" title="Click to edit enrollment details">${data.attendee_name}</u>
          </div>
          ${siblingsHtml}
        </div>
      `;

      wrapper.querySelector('.attendee-name-link').addEventListener('click', (e) => {
        e.preventDefault();
        if (attendingMeetsEditor) {
          attendingMeetsEditor.openAttendingMeetsPopup(data);
        }
      });

      wrapper.querySelectorAll('.sibling-search-link').forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          const name = link.getAttribute('data-name');
          if (name && gridInstanceRef && gridInstanceRef.value) {
            gridInstanceRef.value.searchByText(name);
          }
        });
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

    const gradeCellTemplate = (container, options) => {
      const data = options.data;
      if (!data) return;
      const attendeeId = data.attendee_id;
      if (!attendeeId) return;

      loadGradeConverter();
      const gradeOptions = [
        { id: null, label: '(None)' },
        ...sharedGradeConverter
      ];

      const rawGrade = data.grade !== undefined ? data.grade : null;
      const currentGrade = (rawGrade !== null && rawGrade !== '') ? Number(rawGrade) : null;
      const currentGradeObj = gradeOptions.find(g => g.id === currentGrade);
      const displayLabel = currentGradeObj ? currentGradeObj.label : (currentGrade !== null ? String(currentGrade) : '(None)');

      const lineContainer = document.createElement('div');
      lineContainer.className = 'roster-inline-cell-line';

      const valSpan = document.createElement('span');
      valSpan.innerText = displayLabel;
      if (!currentGradeObj || currentGradeObj.id === null) {
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
            dataSource: gradeOptions,
            valueExpr: 'id',
            displayExpr: 'label',
            value: currentGrade,
            searchEnabled: true,
            width: '100%',
            dropDownOptions: {
              minWidth: 140,
            },
            onValueChanged: async (event) => {
              if (event.value === currentGrade) {
                cleanup();
                return;
              }
              changeHandled = true;
              try {
                const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                const newGrade = (event.value !== null && event.value !== undefined) ? Number(event.value) : null;
                const payload = {
                  infos: {
                    fixed: {
                      grade: newGrade
                    }
                  }
                };

                const patchUrl = `/persons/api/datagrid_data_attendee/${attendeeId}/`;
                const response = await fetch(patchUrl, {
                  method: 'PATCH',
                  headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                    'X-Target-Attendee-Id': String(attendeeId),
                  },
                  body: JSON.stringify(payload)
                });

                if (!response.ok) {
                  const errJson = await response.json().catch(() => ({}));
                  throw new Error(errJson.detail || errJson.error || 'Failed to update grade');
                }

                data.grade = newGrade;
                const updatedObj = gradeOptions.find(item => item.id === newGrade);
                valSpan.innerText = updatedObj ? updatedObj.label : '(None)';
                if (updatedObj && updatedObj.id !== null) {
                  valSpan.classList.remove('empty-val');
                } else {
                  valSpan.classList.add('empty-val');
                }

                DevExpress.ui.notify('Grade updated successfully', 'success', 2000);
              } catch (err) {
                console.error('Error patching grade', err);
                DevExpress.ui.notify('Update failed: ' + err.message, 'error', WARNING_NOTIFY_TIME);
              } finally {
                cleanup();
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
      container.append(lineContainer);
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

      const gatheringId = gatheringMeta && gatheringMeta.id;
      const gatheringStart = gatheringMeta && gatheringMeta.start;
      const checkedIn = attendanceLogic.isCheckedIn(data, gatheringId, gatheringStart);
      const checkedOut = attendanceLogic.isCheckedOut(data, gatheringId, gatheringStart);

      const status = attendanceLogic.getAttendingMeetStatus(data, gatheringMeta);
      if (!checkedIn && status === 'not_attending') {
        wrapper.innerHTML = `<span class="not-attending-text">Not Attending</span>`;
        container.append(wrapper);
        return;
      }

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
        attendanceLogic.toggleAttendance(data, gatheringMeta, domElements, options.rowIndex, colName, colIdx);
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
      
      const FIXED_PREFIX_COUNT = 6;
      const TOTAL_EXTRA_COLS = FIXED_PREFIX_COUNT + 1; // plus 1 dummy-column

      const expectedGradeVisible = resolveGradeVisible(filterData.meets);
      const currentGradeVisible = (gridInstanceRef.value && typeof gridInstanceRef.value.columnOption === 'function')
        ? gridInstanceRef.value.columnOption('grade', 'visible')
        : false;
      if (currentGradeVisible !== expectedGradeVisible) {
        colsChanged = true;
      }

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
            width: 220,
            minWidth: 200,
            cellTemplate: attendeeCellTemplate,
            allowSorting: true,
            allowHiding: false
          },
          {
            dataField: 'grade',
            caption: 'Grade',
            visible: resolveGradeVisible(filterData.meets),
            allowHiding: true,
            fixed: true,
            fixedPosition: 'left',
            width: 85,
            cellTemplate: gradeCellTemplate,
            allowSorting: true
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

        const summaryTotalItems = [
          {
            column: 'attendee_name',
            summaryType: 'custom',
            alignment: 'left',
            cssClass: 'roster-footer-newcomer-cell',
            customizeText: () => ''
          },
          {
            column: 'total_attendances',
            summaryType: 'custom',
            alignment: 'right',
            cssClass: 'roster-footer-label-cell',
            customizeText: () => 'Attendance:'
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

          summaryTotalItems.push({
            column: colId,
            name: 'summary_' + colId,
            summaryType: 'custom',
            alignment: 'center',
            cssClass: `roster-footer-cell roster-col-idx-${idx}`,
            customizeText: (itemInfo) => {
              const reg = gatheringsRegistry.get(colId);
              const count = (reg && reg.attendances_count !== undefined) ? reg.attendances_count : (itemInfo && itemInfo.value !== undefined ? itemInfo.value : 0);
              const enrolled = (reg && reg.enrolled_count !== undefined) ? reg.enrolled_count : null;
              return formatAttendanceDisplay(count, enrolled);
            }
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
            if (col.dataField === 'grade') {
              col.visible = resolveGradeVisible(filterData.meets);
            } else {
              const visible = gridInstanceRef.value.columnOption(col.dataField, 'visible');
              if (visible !== undefined && visible !== null) {
                col.visible = visible;
              }
            }
            const width = gridInstanceRef.value.columnOption(col.dataField, 'width');
            if (width !== undefined && width !== null && !(col.dataField === 'team__display_name' && width > 100)) {
              col.width = width;
            }
          }
        });

        gridInstanceRef.value.option('columns', columns);
        gridInstanceRef.value.option('summary', {
          totalItems: summaryTotalItems,
          calculateCustomSummary: (options) => {
            if (options.summaryProcess === 'finalize') {
              const colId = options.name ? options.name.replace(/^summary_/, '') : null;
              if (colId) {
                const reg = gatheringsRegistry.get(colId);
                options.totalValue = (reg && reg.attendances_count !== undefined) ? reg.attendances_count : 0;
              }
            }
          }
        });
      } else if (serverColumns && serverColumns.length) {
        serverColumns.forEach(gathering => {
          const registered = registerGathering(gathering);
          const gid = registered.id;
          const hasCheckedIn = gid && rows && rows.length && rows.some(r => attendanceLogic.isCheckedIn(r, gid));
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
          const count = (registered && registered.attendances_count !== undefined) ? registered.attendances_count : 0;
          const enrolled = (registered && registered.enrolled_count !== undefined) ? registered.enrolled_count : null;
          const displayCount = formatAttendanceDisplay(count, enrolled);
          const headerEls = document.querySelectorAll(`.roster-header-count[data-col-id="${colId}"]`);
          headerEls.forEach(el => {
            el.textContent = `(${displayCount})`;
          });
        });
        if (gridInstanceRef.value && typeof gridInstanceRef.value.repaint === 'function') {
          gridInstanceRef.value.repaint();
        }
      }
    };

    const loadData = (targetAttendeeId, targetGatheringId) => {
      return new Promise(async (resolve) => {
        if (!filterData.meets || !filterData.meets.length || !isValidDate(filterData.startDate) || !isValidDate(filterData.endDate)) {
          gatheringsRegistry.clear();
          updateGridColumns([], []);
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
            
            if (isValidDate(filterData.startDate)) queryParams.set('start', new Date(filterData.startDate).toISOString());
            if (isValidDate(filterData.endDate)) queryParams.set('finish', new Date(filterData.endDate).toISOString());

            queryParams.set('skip', 0);
            queryParams.set('take', currentTake || 40);

            const response = await fetch(`${endpoints.rosters}?${queryParams.toString()}`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const initialData = await response.json();
            let preloadedData = initialData;

            let isStoreLoadCompleted = false;

            const customStore = new DevExpress.data.CustomStore({
              key: 'attendee_id',
              load: async (loadOptions) => {
                try {
                  if (!isValidDate(filterData.startDate) || !isValidDate(filterData.endDate) || !filterData.meets || !filterData.meets.length) {
                    return { data: [], totalCount: 0 };
                  }

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
                    isStoreLoadCompleted = true;
                    return {
                      data: (takeCount && rows.length > takeCount) ? rows.slice(0, takeCount) : rows,
                      totalCount: cached.totalCount
                    };
                  }

                  const pageParams = new URLSearchParams();
                  filterData.meets.forEach(meet => pageParams.append('meets[]', meet));
                  
                  if (isValidDate(filterData.startDate)) pageParams.set('start', new Date(filterData.startDate).toISOString());
                  if (isValidDate(filterData.endDate)) pageParams.set('finish', new Date(filterData.endDate).toISOString());

                  pageParams.set('skip', loadOptions.skip || 0);
                  pageParams.set('take', loadOptions.take || currentTake || 40);

                  if (loadOptions.requireTotalCount !== undefined) {
                    pageParams.set('requireTotalCount', loadOptions.requireTotalCount);
                  }
                  if (loadOptions.requireGroupCount !== undefined) {
                    pageParams.set('requireGroupCount', loadOptions.requireGroupCount);
                  }

                  if (loadOptions.sort) {
                    pageParams.set('sort', JSON.stringify(loadOptions.sort));
                  }

                  if (loadOptions.group) {
                    pageParams.set('group', JSON.stringify(loadOptions.group));
                  }

                  if (loadOptions.searchValue) {
                    pageParams.set('searchValue', loadOptions.searchValue);
                  }
                  if (loadOptions.filter) {
                    pageParams.set('filter', JSON.stringify(loadOptions.filter));
                  }

                  const pageResponse = await fetch(`${endpoints.rosters}?${pageParams.toString()}`);
                  if (!pageResponse.ok) throw new Error('Network response was not ok');
                  
                  const pageData = await pageResponse.json();
                  isStoreLoadCompleted = true;
                  return {
                    data: pageData.data || pageData.rows,
                    totalCount: pageData.totalCount,
                    groupCount: pageData.groupCount,
                  };

                } catch (error) {
                  DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', WARNING_NOTIFY_TIME);
                  console.error(error);
                  throw error; 
                }
              }
            });

            const highlightAndScrollTarget = async () => {
              if (!gridInstanceRef.value || !targetAttendeeId) return;
              const targetIds = (Array.isArray(targetAttendeeId) ? targetAttendeeId : [targetAttendeeId])
                .map(id => String(id))
                .filter(Boolean);
              if (targetIds.length === 0) return;

              const primaryId = targetIds[0];

              if (gridInstanceRef.value.option('searchPanel.text')) {
                gridInstanceRef.value.searchByText('');
              }

              const applySelectionAndVisuals = async () => {
                try {
                  await gridInstanceRef.value.selectRows(targetIds, false);
                  const rIdx = gridInstanceRef.value.getRowIndexByKey(primaryId);
                  if (rIdx >= 0) {
                    const rowEl = gridInstanceRef.value.getRowElement(rIdx);
                    const domEl = rowEl && (rowEl[0] || (rowEl.length ? rowEl[0] : rowEl));
                    if (domEl) {
                      if (typeof domEl.scrollIntoView === 'function') {
                        domEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }
                      domEl.classList.add('roster-row-newly-added');
                      setTimeout(() => domEl.classList.remove('roster-row-newly-added'), 3500);
                    }
                  }
                } catch (e) {
                  console.warn('Error applying row selection:', e);
                }
              };

              let rowIndex = gridInstanceRef.value.getRowIndexByKey(primaryId);
              if (rowIndex >= 0) {
                await applySelectionAndVisuals();
                return;
              }
              // If not on the current page, do NOT force page change away from Page 1!
              // The newcomer status is safely and prominently shown in the footer before 'Attendance:'.
            };

            let safetyTimer = null;
            const onContentReady = async () => {
              if (!isStoreLoadCompleted) return;
              if (safetyTimer) clearTimeout(safetyTimer);
              gridInstanceRef.value.off('contentReady', onContentReady);

              if (targetAttendeeId) {
                await highlightAndScrollTarget();
              }
              if (targetGatheringId) {
                highlightGatheringColumn(targetGatheringId);
              }
              renderFooterNewcomer();
              resolve();
            };

            safetyTimer = setTimeout(async () => {
              if (gridInstanceRef.value) {
                gridInstanceRef.value.off('contentReady', onContentReady);
                if (targetAttendeeId) {
                  await highlightAndScrollTarget();
                }
                if (targetGatheringId) {
                  highlightGatheringColumn(targetGatheringId);
                }
                renderFooterNewcomer();
              }
              resolve();
            }, 1000);

            gridInstanceRef.value.on('contentReady', onContentReady);

            gridInstanceRef.value.beginUpdate();
            gatheringsRegistry.clear();
            updateGridColumns(initialData.columns, initialData.data || initialData.rows || []);
            const curTeamWidth = gridInstanceRef.value.columnOption('team__display_name', 'width');
            if (curTeamWidth && curTeamWidth > 100) {
              gridInstanceRef.value.columnOption('team__display_name', 'width', 80);
            }
            const targetGradeVis = resolveGradeVisible(filterData.meets);
            if (gridInstanceRef.value.columnOption('grade', 'visible') !== targetGradeVis) {
              setIsProgrammaticGradeChange(true);
              try {
                gridInstanceRef.value.columnOption('grade', 'visible', targetGradeVis);
              } finally {
                setIsProgrammaticGradeChange(false);
              }
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
        repaintChangesOnly: true,
        showBorders: true,
        rowAlternationEnabled: true,
        allowColumnResizing: true,
        columnResizingMode: 'widget',
        columnAutoWidth: true,
        hoverStateEnabled: true,
        noDataText: "No data found. Please select a meet to load.",
        remoteOperations: {
          groupPaging: true
        },
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
            width: 220,
            minWidth: 200,
            cellTemplate: attendeeCellTemplate,
            allowSorting: true,
            allowHiding: false
          },
          {
            dataField: 'grade',
            caption: 'Grade',
            visible: resolveGradeVisible(filterData.meets),
            allowHiding: true,
            fixed: true,
            fixedPosition: 'left',
            width: 85,
            cellTemplate: gradeCellTemplate,
            allowSorting: true
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
        summary: {
          totalItems: [],
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
          placeholder: 'Search name, contacts, team, character...',
        },
        columnChooser: {
          enabled: true,
          mode: 'select',
        },
        onOptionChanged: (e) => {
          if (e.name === 'columns' && typeof e.fullName === 'string' && e.fullName.endsWith('.visible')) {
            if (isProgrammaticGradeChange) return;

            let targetField = null;
            const match = e.fullName.match(/columns\[(\d+)\]\.visible/);
            if (match) {
              const index = parseInt(match[1], 10);
              const col = e.component.columnOption(index) || e.component.option('columns')?.[index];
              targetField = col?.dataField;
            } else {
              targetField = e.fullName.slice(0, -8).replace(/^columns\./, '');
            }

            if (targetField === 'grade') {
              setUserGradeVisiblePreference(Boolean(e.value));
            }
          }
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
                  setUserGradeVisiblePreference(null);
                  clearLastNewcomer();
                  gatheringsRegistry.clear();
                  updateGridColumns([], []);
                  if (gridInstanceRef.value) {
                    gridInstanceRef.value.clearGrouping();
                    gridInstanceRef.value.clearSorting();
                    gridInstanceRef.value.state(null);
                  }
                  if (typeof onResetCallback === 'function') {
                    onResetCallback();
                  }
                }
              }
            }
          });
        },
        onContentReady: () => {
          renderFooterNewcomer();
        }
      });
    };

    return {
      initDataGrid,
      loadData,
      getHighlightedGathering: () => activeHighlightedIndex !== null ? lastHighlightedGathering : null,
      clearColumnHighlight,
      highlightGatheringColumn,
      setLastNewcomer,
      clearLastNewcomer,
      getLastNewcomer: () => lastNewcomer
    };
  }
