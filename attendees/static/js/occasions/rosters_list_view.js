;(() => {
  const { createApp, ref, reactive, onMounted } = Vue;


  // ==========================================================
  // 1. Endpoints Logic
  // ==========================================================
  function useEndpoints() {
    const endpoints = reactive({
      rosters: '',
      meets: '',
      attendances: '/occasions/api/organization_meet_character_attendances/'
    });

    const initEndpoints = () => {
      const appEl = document.getElementById('app');
      if (appEl) {
        endpoints.rosters = appEl.dataset.rostersEndpoint;
        endpoints.meets = appEl.dataset.meetsEndpointBySlug;
      }
    };

    return { endpoints, initEndpoints };
  }

  // ==========================================================
  // 2. Attendance & API Logic
  // ==========================================================
  function useAttendanceLogic(endpoints, gridInstanceRef) {
    const getAttendanceRecord = (rowData, gatheringId) => {
      return rowData.attendances.find(a => String(a.gathering_id) === String(gatheringId));
    };

    const isCheckedIn = (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      return record && record.category_id !== 1;
    };

    const isCheckedOut = (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      return record && record.finish;
    };

    const isAttendingValid = (rowData, gathering) => {
      if (!rowData.attendingmeets) return true; 
      const am = rowData.attendingmeets.find(m => String(m.meet_id) === String(gathering.meet_id));
      if (!am) return false;
      
      const gStart = new Date(gathering.start);
      const amStart = am.start ? new Date(am.start) : new Date('1970-01-01');
      const amFinish = am.finish ? new Date(am.finish) : new Date('2099-12-31');
      
      return gStart >= amStart && gStart <= amFinish;
    };

    const toggleAttendance = async (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);
      const newCategory = isCurrentlyCheckedIn ? 1 : 9; 

      try {
        const recordId = record ? (record.attendance_id || record.id) : '';
        const response = await fetch(`${endpoints.attendances}${recordId ? recordId + '/' : ''}`, {
          method: record ? 'PATCH' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
          },
          body: JSON.stringify({
            gathering: gatheringId,
            attending: rowData.attending_id,
            character: (rowData.attendingmeets && rowData.attendingmeets.length > 0) ? rowData.attendingmeets[0].character_id : 1, // fallback to 1 if no character found
            category: newCategory
          })
        });

        if (!response.ok) throw new Error('Failed to update attendance');
        const updatedRecord = await response.json();

        const normalizedRecord = {
          attendance_id: updatedRecord.id,
          gathering_id: updatedRecord.gathering,
          category_id: updatedRecord.category,
          start: updatedRecord.start,
          finish: updatedRecord.finish
        };

        if (record) {
          Object.assign(record, normalizedRecord);
        } else {
          rowData.attendances.push(normalizedRecord);
        }

        // Update the total attendances count dynamically
        const newTotal = isCurrentlyCheckedIn 
          ? Math.max(0, (rowData.total_attendances || 0) - 1)
          : (rowData.total_attendances || 0) + 1;
        
        rowData.total_attendances = newTotal;

        if (gridInstanceRef.value) {
          const rowIndex = gridInstanceRef.value.getRowIndexByKey(rowData.attending_id);
          gridInstanceRef.value.cellValue(rowIndex, 'total_attendances', newTotal);
          gridInstanceRef.value.repaintRows([rowIndex]);
        }
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }
    };

    const markOut = async (rowData, gatheringId) => {
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

        if (!response.ok) throw new Error('Failed to mark out');
        const updatedRecord = await response.json();

        const normalizedRecord = {
          attendance_id: updatedRecord.id,
          gathering_id: updatedRecord.gathering,
          category_id: updatedRecord.category,
          start: updatedRecord.start,
          finish: updatedRecord.finish
        };

        Object.assign(record, normalizedRecord);
        
        if (gridInstanceRef.value) {
          const rowIndex = gridInstanceRef.value.getRowIndexByKey(rowData.attending_id);
          gridInstanceRef.value.repaintRows([rowIndex]);
        }
      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }
    };

    return { isAttendingValid, isCheckedIn, isCheckedOut, toggleAttendance, markOut };
  }

  // ==========================================================
  // 3. Grid View Logic
  // ==========================================================
  function useRosterGrid(endpoints, filterData, gridInstanceRef, attendanceLogic) {
    const formatDate = (dateString) => {
      if (!dateString) return '';
      const d = new Date(dateString);
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    };

    const openAttendeeEdit = (attendeeId) => {
      window.open(`/persons/attendee/${attendeeId}`, '_blank');
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
        <span>
          <a href="#" class="attendee-link">${data.attendee_name}</a> 
        </span>
      `;
      
      wrapper.querySelector('.attendee-link').addEventListener('click', (e) => {
        e.preventDefault();
        openAttendeeEdit(data.attendee_id);
      });

      container.append(wrapper);
    };

    const attendanceCellTemplate = (container, options) => {
      const data = options.data;
      const gatheringMeta = options.column.gatheringMeta;
      const gatheringId = options.column.name;
      
      const wrapper = document.createElement('div');
      wrapper.className = 'text-center';

      if (!attendanceLogic.isAttendingValid(data, gatheringMeta)) {
        wrapper.innerHTML = `<span class="not-attending-text">Not Attending</span>`;
        container.append(wrapper);
        return;
      }

      const checkedIn = attendanceLogic.isCheckedIn(data, gatheringId);
      const checkInBtn = document.createElement('button');
      checkInBtn.className = `roster-btn ${checkedIn ? 'checked-in' : ''}`;
      checkInBtn.innerText = checkedIn ? 'Checked In' : 'Check In';
      checkInBtn.addEventListener('click', () => attendanceLogic.toggleAttendance(data, gatheringId));
      wrapper.appendChild(checkInBtn);

      if (checkedIn) {
        const checkedOut = attendanceLogic.isCheckedOut(data, gatheringId);
        const outBtn = document.createElement('button');
        outBtn.className = `roster-btn roster-btn-out ${checkedOut ? 'checked-out' : ''}`;
        outBtn.innerText = checkedOut ? 'Checked Out' : 'Out';
        outBtn.addEventListener('click', () => attendanceLogic.markOut(data, gatheringId));
        wrapper.appendChild(outBtn);
      }

      container.append(wrapper);
    };

    const updateGridColumns = (serverColumns) => {
      const currentCols = gridInstanceRef.value.option('columns');
      let colsChanged = false;
      
      if (!currentCols || currentCols.length !== serverColumns.length + 3) {
        colsChanged = true;
      } else {
        for (let i = 0; i < serverColumns.length; i++) {
          if (currentCols[i + 2].name !== String(serverColumns[i].id)) {
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
            allowSorting: true
          },
          {
            dataField: 'total_attendances',
            caption: 'Attendances',
            fixed: true,
            fixedPosition: 'left',
            width: 100,
            alignment: 'center',
            allowSorting: true
          }
        ];

        serverColumns.forEach(gathering => {
          columns.push({
            name: String(gathering.id),
            caption: formatDate(gathering.start),
            alignment: 'center',
            gatheringMeta: gathering,
            cellTemplate: attendanceCellTemplate
          });
        });

        columns.push({
          caption: '',
          cssClass: 'dummy-column'
        });

        gridInstanceRef.value.option('columns', columns);
      }
    };

    const loadData = () => {
      if (!filterData.meets || !filterData.meets.length) {
        return; 
      }

      if (gridInstanceRef.value) {
        gridInstanceRef.value.option('dataSource', new DevExpress.data.CustomStore({
          key: 'attending_id',
          load: async (loadOptions) => {
            try {
              const queryParams = new URLSearchParams();
              filterData.meets.forEach(meet => queryParams.append('meets[]', meet));
              
              if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
              if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

              queryParams.set('skip', loadOptions.skip || 0);
              queryParams.set('take', loadOptions.take || 40);

              if (loadOptions.sort) {
                queryParams.set('sort', JSON.stringify(loadOptions.sort));
              }

              const response = await fetch(`${endpoints.rosters}?${queryParams.toString()}`);
              if (!response.ok) throw new Error('Network response was not ok');
              
              const data = await response.json();
              
              if (loadOptions.skip === 0 || loadOptions.skip == null) {
                updateGridColumns(data.columns);
              }

              return {
                data: data.rows,
                totalCount: data.totalCount
              };

            } catch (error) {
              DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', 3000);
              console.error(error);
              throw error; 
            }
          }
        }));
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
        remoteOperations: { paging: true, sorting: true },
        paging: { pageSize: 40 },
        pager: {
          showPageSizeSelector: true,
          allowedPageSizes: [20, 40, 80],
          showInfo: true
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
      const { initDataGrid, loadData } = useRosterGrid(endpoints, filterData, gridInstanceRef, attendanceLogic);
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
