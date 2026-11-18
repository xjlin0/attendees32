import { Ref } from 'vue';
import { Endpoints, Gathering, AttendeeRow, AttendanceRecord, AttendingMeet } from '../types';
import { gatheringsRegistry, meetsMap } from './useLookups';
import notify from 'devextreme/ui/notify';
import { confirm } from 'devextreme/ui/dialog';
import dxPopup from 'devextreme/ui/popup';
import dxButton from 'devextreme/ui/button';
import SignaturePad from 'signature_pad';

const WARNING_NOTIFY_TIME = 5000;

export function useAttendanceLogic(
  endpoints: Endpoints,
  gridInstanceRef: Ref<any>,
  openSignaturePopup?: (opts: { title?: string; onSign: (encodedFile: string) => Promise<void> }) => void,
) {
  const getAttendanceRecord = (rowData: any, gatheringId: number | string | null, gatheringStart?: string | null): AttendanceRecord | null => {
    if (!rowData || !rowData.attendances) return null;
    if (gatheringId) {
      const match = rowData.attendances.find((a: any) => a && String(a.gathering_id) === String(gatheringId));
      if (match) return match;
    }
    if (gatheringStart) {
      const gStartMs = new Date(gatheringStart).getTime();
      if (!isNaN(gStartMs)) {
        return rowData.attendances.find((a: any) => {
          if (!a) return false;
          if (a.gathering_start && Math.abs(new Date(a.gathering_start).getTime() - gStartMs) < 60000) return true;
          if (a.start && Math.abs(new Date(a.start).getTime() - gStartMs) < 60000) return true;
          return false;
        }) || null;
      }
    }
    return null;
  };

  const isCheckedIn = (rowData: any, gatheringId: number | string | null, gatheringStart?: string | null): boolean => {
    const record = getAttendanceRecord(rowData, gatheringId, gatheringStart);
    return !!(record && (record.category_id as any) !== 1 && record.category !== 1);
  };

  const isCheckedOut = (rowData: any, gatheringId: number | string | null, gatheringStart?: string | null): boolean => {
    const record = getAttendanceRecord(rowData, gatheringId, gatheringStart);
    return !!(record && record.finish);
  };

  const getAttendingMeetForGathering = (rowData: AttendeeRow, gathering: Gathering | null): AttendingMeet | null => {
    if (!rowData.attendingmeets || !rowData.attendingmeets.length) return null;
    if (!gathering || !gathering.meet_id) return rowData.attendingmeets[0];
    return rowData.attendingmeets.find((am: any) => String(am.meet_id != null ? am.meet_id : am.meet) === String(gathering.meet_id)) || null;
  };

  const getActiveAttendingMeet = (rowData: AttendeeRow, gathering: Gathering | null): AttendingMeet | null => {
    if (!rowData.attendingmeets || !rowData.attendingmeets.length) return null;
    if (!gathering || !gathering.start) {
      return rowData.attendingmeets[0];
    }
    const gStart = new Date(gathering.start);
    return rowData.attendingmeets.find((am: any) => {
      const amMeetId = am.meet_id != null ? am.meet_id : am.meet;
      if (gathering.meet_id && String(amMeetId) !== String(gathering.meet_id)) {
        return false;
      }
      const amStart = am.start ? new Date(am.start) : new Date('1970-01-01');
      const amFinish = am.finish ? new Date(am.finish) : new Date('2099-12-31');
      return gStart >= amStart && gStart <= amFinish;
    }) || null;
  };

  const getAttendingMeetStatus = (rowData: AttendeeRow, gathering: Gathering | null): 'active' | 'expired' | 'not_attending' => {
    if (!rowData || !rowData.attendingmeets || !rowData.attendingmeets.length) return 'expired';
    const am = getAttendingMeetForGathering(rowData, gathering);
    if (!am) return 'expired';
    if (!gathering || !gathering.start) return 'active';

    const gStart = new Date(gathering.start);
    const amStart = am.start ? new Date(am.start) : new Date('1970-01-01');
    const amFinish = am.finish ? new Date(am.finish) : new Date('2099-12-31');

    if (gStart >= amStart && gStart <= amFinish) {
      return 'active';
    }
    return 'expired';
  };

  const isAttendingValid = (rowData: AttendeeRow, gathering: Gathering | null): boolean => {
    return getAttendingMeetStatus(rowData, gathering) !== 'not_attending';
  };

  const getMeetSignatureRequiredAt = (meetId?: number | string | null) => {
    if (!meetId) return null;
    const m = meetsMap.get(meetId) || meetsMap.get(String(meetId));
    return (m && m.infos) ? m.infos.signature_required_at : null;
  };

  const formatAttendanceDisplay = (count: number, enrolled?: number | null) => {
    if (enrolled !== undefined && enrolled !== null && enrolled > 0) {
      return `${count}/${enrolled}`;
    }
    return String(count);
  };

  const updateGatheringCheckInCount = (gathering: Gathering | null, delta: number, colIdx?: number, colName?: string) => {
    const targetGathering = gathering || (colName && gatheringsRegistry.get(colName)) || null;
    if (!targetGathering) return;

    const currentCount = targetGathering.attendances_count !== undefined ? targetGathering.attendances_count : 0;
    const newCount = Math.max(0, currentCount + delta);
    targetGathering.attendances_count = newCount;

    const colId = colName || (targetGathering.id ? String(targetGathering.id) : '');
    if (targetGathering.id) {
      const reg = gatheringsRegistry.get(String(targetGathering.id));
      if (reg) reg.attendances_count = newCount;
    }
    if (colId) {
      const regCol = gatheringsRegistry.get(colId);
      if (regCol) regCol.attendances_count = newCount;
    }

    const enrolled = targetGathering.enrolled_count !== undefined && targetGathering.enrolled_count !== null
      ? targetGathering.enrolled_count
      : (targetGathering.id ? gatheringsRegistry.get(String(targetGathering.id))?.enrolled_count : undefined);
    const displayCount = formatAttendanceDisplay(newCount, enrolled);

    if (gridInstanceRef.value && colId) {
      const colMeta = gridInstanceRef.value.columnOption(colId, 'gatheringMeta');
      if (colMeta) {
        colMeta.attendances_count = newCount;
        colMeta.enrolled_count = enrolled;
      }
    }

    // 1. Update Header count in DOM
    const targetIds = [colId, targetGathering.id ? String(targetGathering.id) : null].filter(Boolean);
    const headerSelector = targetIds.map((id) => `.roster-header-count[data-col-id="${id}"]`).join(', ');
    const headerEls = document.querySelectorAll(headerSelector);
    headerEls.forEach((el) => {
      el.textContent = `(${displayCount})`;
    });

    // 2. Update Footer count in DOM
    let targetColIdx = colIdx;
    if ((targetColIdx === undefined || targetColIdx === null) && gridInstanceRef.value && colId) {
      const col = gridInstanceRef.value.columnOption(colId);
      if (col && col.colIndex !== undefined) {
        targetColIdx = col.colIndex;
      }
    }

    if (targetColIdx !== undefined && targetColIdx !== null) {
      const footerCells = document.querySelectorAll(`.dx-datagrid-total-footer td.roster-col-idx-${targetColIdx}, .dx-datagrid-total-footer .roster-col-idx-${targetColIdx}`);
      footerCells.forEach((cell) => {
        const item = cell.querySelector('.dx-datagrid-summary-item') || cell;
        item.textContent = displayCount;
      });
    }
  };

  const updateGridRowAttendance = (rowData: any, gatheringId: any, normalizedRecord: any, rowIndex?: number) => {
    if (!rowData.attendances) rowData.attendances = [];
    let rec = getAttendanceRecord(rowData, gatheringId);
    if (rec) {
      Object.assign(rec, normalizedRecord);
    } else {
      rowData.attendances.push(normalizedRecord);
    }

    if (gridInstanceRef.value) {
      const key = gridInstanceRef.value.keyOf(rowData);
      if (key !== undefined) {
        const store = gridInstanceRef.value.getDataSource()?.store();
        if (store && store._array) {
          const item = store._array.find((r: any) => gridInstanceRef.value.keyOf(r) === key);
          if (item) {
            item.attendances = rowData.attendances;
          }
        }
      }
    }
  };

  /**
   * Dynamically updates the total attendances counter and grid cell for the specified attendee row.
   * @param rowData Row data object for the attendee.
   * @param rowIndex Optional visual row index in DataGrid.
   * @param newTotal Calculated new total attendances number.
   */
  const updateTotalAttendancesCell = (rowData: any, rowIndex?: number, newTotal?: number) => {
    if (!gridInstanceRef.value || newTotal === undefined) return;
    try {
      const rowKey = gridInstanceRef.value.keyOf(rowData) ?? (rowData.attendee_id || rowData.attending_id);
      let rIndex = (typeof rowIndex === 'number' && rowIndex >= 0) ? rowIndex : -1;
      if (rIndex < 0 && rowKey !== undefined) {
        rIndex = gridInstanceRef.value.getRowIndexByKey(rowKey);
      }
      if (rIndex >= 0) {
        const cellEl = gridInstanceRef.value.getCellElement(rIndex, 'total_attendances');
        if (cellEl) {
          const domEl = (cellEl as any).get ? (cellEl as any).get(0) : cellEl;
          if (domEl) {
            domEl.textContent = String(newTotal);
          }
        }
        const visibleRows = typeof gridInstanceRef.value.getVisibleRows === 'function' ? gridInstanceRef.value.getVisibleRows() : null;
        if (visibleRows && visibleRows[rIndex] && visibleRows[rIndex].data) {
          visibleRows[rIndex].data.total_attendances = newTotal;
        }
      }
      const store = gridInstanceRef.value.getDataSource()?.store();
      if (store && store._array) {
        const item = store._array.find((r: any) => gridInstanceRef.value.keyOf(r) === rowKey);
        if (item) {
          item.total_attendances = newTotal;
        }
      }
    } catch {
      // silently handle DOM cell update errors
    }
  };

  const executeAttendanceToggle = async (
    rowData: any,
    gathering: Gathering,
    domElements: any,
    rowIndex: number,
    colName: string,
    colIdx: number,
    newCategory: number,
    encodedFile?: string | null,
    clearFile?: boolean,
  ) => {
    const gatheringId = gathering ? gathering.id : null;
    let record = getAttendanceRecord(rowData, gatheringId);
    const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);

    const targetAm = getActiveAttendingMeet(rowData, gathering) || getAttendingMeetForGathering(rowData, gathering);
    const attendingId = targetAm ? (targetAm.attending_id || (targetAm as any).attending) : (rowData.attending_id || (rowData.attendingmeets?.[0]?.attending_id || (rowData.attendingmeets?.[0] as any)?.attending));
    const characterId = targetAm ? (targetAm.character_id || (targetAm as any).character) : (rowData.attendingmeets?.[0]?.character_id || (rowData.attendingmeets?.[0] as any)?.character || 1);

    if ((window as any).Attendees?.utilities) {
      (window as any).Attendees.utilities.editingEnabled = true;
    }

    try {
      const recordId = record ? ((record as any).attendance_id || record.id) : '';
      const payload: any = {
        gathering: gatheringId || null,
        attending: attendingId,
        character: characterId,
        category: newCategory,
      };
      if (!gatheringId && gathering) {
        payload.meet = gathering.meet_id;
        payload.gathering_start = gathering.start;
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

      const csrfEl = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
      const csrfToken = csrfEl ? csrfEl.value : '';

      const response = await fetch(`${endpoints.attendances}${recordId ? recordId + '/' : ''}`, {
        method: record ? 'PATCH' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(payload),
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
        file: clearFile ? null : (updatedRecord.file_path || null),
      };

      if (gathering && updatedRecord.gathering) {
        gathering.id = updatedRecord.gathering;
        gatheringsRegistry.set(String(updatedRecord.gathering), gathering);
        if (gathering.meet_id && gathering.start) {
          gatheringsRegistry.set(`${gathering.meet_id}_${gathering.start}`, gathering);
        }
      }

      updateGridRowAttendance(rowData, updatedRecord.gathering, normalizedRecord, rowIndex);

      // Mutate button DOM if provided
      if (domElements?.checkInBtn) {
        if (newCategory === 1) {
          domElements.checkInBtn.className = 'roster-btn';
          domElements.checkInBtn.innerText = 'Check In';
          if (domElements.outBtn) {
            domElements.outBtn.style.display = 'none';
          }
        } else {
          domElements.checkInBtn.className = 'roster-btn checked-in';
          domElements.checkInBtn.innerText = 'Checked In';
          if (domElements.outBtn) {
            domElements.outBtn.style.display = '';
            domElements.outBtn.className = 'roster-btn roster-btn-out';
            domElements.outBtn.innerText = 'Out';
          }
        }
      }

      // Delta count for column and row
      if (!isCurrentlyCheckedIn && newCategory !== 1) {
        updateGatheringCheckInCount(gathering, 1, colIdx, colName);
        const newTotal = (rowData.total_attendances || 0) + 1;
        rowData.total_attendances = newTotal;
        updateTotalAttendancesCell(rowData, rowIndex, newTotal);
      } else if (isCurrentlyCheckedIn && newCategory === 1) {
        updateGatheringCheckInCount(gathering, -1, colIdx, colName);
        const newTotal = Math.max(0, (rowData.total_attendances || 0) - 1);
        rowData.total_attendances = newTotal;
        updateTotalAttendancesCell(rowData, rowIndex, newTotal);
      }

      notify(newCategory === 1 ? 'Check-in cleared' : 'Checked in successfully', newCategory === 1 ? 'info' : 'success', 2000);
    } catch (err: any) {
      notify(err.message, 'error', WARNING_NOTIFY_TIME);
    } finally {
      if ((window as any).Attendees?.utilities) {
        (window as any).Attendees.utilities.editingEnabled = false;
      }
    }
  };

  let signaturePopupInstance: any = null;
  let signaturePadInstance: any = null;
  let currentSignatureCallback: ((encodedFile: string) => Promise<void>) | null = null;

  const ensureSignaturePadLoaded = async (): Promise<any> => {
    if (typeof (window as any).SignaturePad !== 'undefined') {
      return (window as any).SignaturePad;
    }
    return SignaturePad;
  };

  const initSignatureCanvas = () => {
    const canvas = document.querySelector('canvas.signature') as HTMLCanvasElement | null;
    const SigPad = (window as any).SignaturePad || SignaturePad;
    if (canvas && SigPad) {
      canvas.style.width = '100%';
      canvas.style.height = '100px';
      const width = canvas.offsetWidth || 378;
      const height = canvas.offsetHeight || 100;
      canvas.width = width;
      canvas.height = height;

      if (signaturePadInstance) {
        try { signaturePadInstance.off(); } catch (e) {}
      }
      signaturePadInstance = new SigPad(canvas, {
        maxWidth: 2,
        backgroundColor: 'rgb(255,255,255)',
      });
      signaturePadInstance.clear();
    }
  };

  const getSignaturePopup = () => {
    if (signaturePopupInstance) return signaturePopupInstance;

    let popupEl = document.getElementById('signature-canvas-popup');
    if (!popupEl) {
      popupEl = document.createElement('div');
      popupEl.id = 'signature-canvas-popup';
      document.body.appendChild(popupEl);
    }

    const DevExpressUI = (window as any).DevExpress?.ui || {};
    const DxPopup = DevExpressUI.dxPopup || dxPopup;

    signaturePopupInstance = new DxPopup(popupEl, {
      visible: false,
      contentTemplate: () => {
        const t = document.getElementById('signature-popup-template') as HTMLTemplateElement | null;
        if (t && t.content && t.content.firstElementChild) {
          return t.content.firstElementChild.cloneNode(true);
        }
        const div = document.createElement('div');
        div.style.width = '100%';
        div.style.height = '100px';
        div.innerHTML = '<canvas class="signature" style="width: 100%; height: 100px;"></canvas>';
        return div;
      },
      maxWidth: 400,
      width: '95%',
      height: 200,
      showTitle: true,
      title: 'Sign here',
      dragEnabled: false,
      hideOnOutsideClick: false,
      showCloseButton: false,
      position: { at: 'center', my: 'center' },
      onShown: () => {
        if ((window as any).Attendees?.utilities) {
          (window as any).Attendees.utilities.editingEnabled = true;
        }
        const canvas = document.querySelector('canvas.signature') as HTMLCanvasElement | null;
        if (canvas && (!signaturePadInstance || canvas.width === 0 || canvas.height === 0)) {
          initSignatureCanvas();
        }
      },
      onHiding: () => {
        if ((window as any).Attendees?.utilities) {
          (window as any).Attendees.utilities.editingEnabled = false;
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
                notify({
                  message: 'Signing requires signature!',
                  position: { my: 'center', at: 'center', of: window },
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
    });

    return signaturePopupInstance;
  };

  const internalOpenSignaturePopup = async (opts: { title?: string; onSign: (encodedFile: string) => Promise<void> }) => {
    try {
      await ensureSignaturePadLoaded();
      const popup = getSignaturePopup();
      popup.option('title', opts.title || 'Sign here');
      currentSignatureCallback = opts.onSign;
      popup.show();
      initSignatureCanvas();
    } catch (e: any) {
      notify(e.message, 'error', WARNING_NOTIFY_TIME);
    }
  };

  const triggerOpenSignaturePopup = openSignaturePopup || internalOpenSignaturePopup;

  const toggleAttendance = async (rowData: any, gathering: Gathering, domElements: any, rowIndex: number, colName: string, colIdx: number) => {
    const gatheringId = gathering ? gathering.id : null;
    const record = getAttendanceRecord(rowData, gatheringId);
    const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);
    const meetId = gathering?.meet_id || null;
    const signatureRequiredAt = getMeetSignatureRequiredAt(meetId);

    if (!isCurrentlyCheckedIn) {
      if (signatureRequiredAt === 'check_in') {
        const attendeeName = rowData.attendee_name || 'Attendee';
        triggerOpenSignaturePopup({
          title: `Checking in ${attendeeName}`,
          onSign: async (encodedFile) => {
            await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, colIdx, 9, encodedFile, false);
          },
        });
      } else {
        await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, colIdx, 9, null, false);
      }
    } else {
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
        const resultPromise = confirm(
          `<strong>Clear check-in record of ${attendeeName} and REMOVE signature?</strong>${fileImgTag}`,
          'UNDO check-in record?',
        );
        (resultPromise as any).done(async (dialogResult: boolean) => {
          if (dialogResult) {
            await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, colIdx, 1, null, true);
          }
        });
      } else {
        await executeAttendanceToggle(rowData, gathering, domElements, rowIndex, colName, colIdx, 1, null, false);
      }
    }
  };

  const executeCheckOut = async (rowData: any, record: any, domElements: any, rowIndex: number, newFinish: string | null, encodedFile?: string | null, clearFile?: boolean) => {
    try {
      const recordId = record.attendance_id || record.id;
      const payload: any = { finish: newFinish };
      if (encodedFile !== undefined && encodedFile !== null) payload.encoded_file = encodedFile;
      if (clearFile) payload.file = null;

      const csrfEl = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
      const csrfToken = csrfEl ? csrfEl.value : '';

      const response = await fetch(`${endpoints.attendances}${recordId}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(payload),
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
        file: clearFile ? null : (updatedRecord.file_path || record.file || null),
      };

      Object.assign(record, normalizedRecord);

      if (domElements?.outBtn) {
        if (newFinish) {
          domElements.outBtn.className = 'roster-btn roster-btn-out checked-out';
          domElements.outBtn.innerText = 'Checked Out';
        } else {
          domElements.outBtn.className = 'roster-btn roster-btn-out';
          domElements.outBtn.innerText = 'Out';
        }
      }

      updateGridRowAttendance(rowData, updatedRecord.gathering, normalizedRecord, rowIndex);
      notify(newFinish ? 'Checked out successfully' : 'Check-out undone', newFinish ? 'success' : 'info', 2000);
    } catch (err: any) {
      notify(err.message, 'error', WARNING_NOTIFY_TIME);
    }
  };

  const markOut = async (rowData: any, gathering: Gathering, domElements: any, rowIndex: number) => {
    let gatheringId = gathering ? gathering.id : null;
    const record = getAttendanceRecord(rowData, gatheringId, gathering?.start);
    if (!record) return;

    if (!gatheringId && record.gathering_id) {
      gatheringId = record.gathering_id;
      if (gathering) {
        gathering.id = record.gathering_id;
        gatheringsRegistry.set(String(record.gathering_id), gathering);
        if (gathering.meet_id && gathering.start) {
          gatheringsRegistry.set(`${gathering.meet_id}_${gathering.start}`, gathering);
        }
      }
    }

    const isCurrentlyCheckedOut = !!record.finish;
    const meetId = gathering?.meet_id || null;
    const signatureRequiredAt = getMeetSignatureRequiredAt(meetId);

    if (!isCurrentlyCheckedOut) {
      if (signatureRequiredAt === 'check_out') {
        const attendeeName = rowData.attendee_name || 'Attendee';
        triggerOpenSignaturePopup({
          title: `Checking out ${attendeeName}`,
          onSign: async (encodedFile) => {
            const nowIso = new Date().toISOString();
            await executeCheckOut(rowData, record, domElements, rowIndex, nowIso, encodedFile, false);
          },
        });
      } else {
        const nowIso = new Date().toISOString();
        await executeCheckOut(rowData, record, domElements, rowIndex, nowIso, null, false);
      }
    } else {
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

        const resultPromise = confirm(
          `<strong>Clear the time-out record of ${attendeeName} and REMOVE signature?</strong>${fileImgTag}`,
          'UNDO check-out record?',
        );

        (resultPromise as any).done(async (dialogResult: boolean) => {
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
    getAttendanceRecord,
    isCheckedIn,
    isCheckedOut,
    getAttendingMeetForGathering,
    getActiveAttendingMeet,
    getAttendingMeetStatus,
    isAttendingValid,
    updateGatheringCheckInCount,
    updateGridRowAttendance,
    updateTotalAttendancesCell,
    executeAttendanceToggle,
    toggleAttendance,
    executeCheckOut,
    markOut,
    initSignaturePopup: getSignaturePopup,
    openSignaturePopup: triggerOpenSignaturePopup,
  };
}
