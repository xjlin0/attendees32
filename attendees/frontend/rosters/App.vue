<template>
  <div class="rosters-container">
    <div class="d-flex justify-content-between mb-3 align-items-center">
      <div class="d-flex">
        <h3>Rosters Table</h3>
      </div>
      <div v-if="endpoints.userCanWrite" class="d-flex">
        <a
          style="padding: 5px; text-decoration: none; height: 1.6rem;"
          role="button"
          class="btn btn-outline-success btn-sm add-attendee"
          title="add a new attendee"
          aria-label="+ Attendee"
          @click.prevent="openAddAttendee"
        >
          <span class="fas fa-user-plus" aria-hidden="true"></span>
          Attendee
        </a>
      </div>
      <div v-else id="user-cannot-write">
        Editing forbidden
      </div>
    </div>

    <!-- DevExtreme Filters Form Container -->
    <div id="rosters-filter-form-container" ref="filterFormRef"></div>

    <!-- DevExtreme DataGrid Container -->
    <div id="rosters-datagrid-container" ref="dataGridRef" class="mt-3"></div>

    <!-- Add Attendee Modal (Vue 3 SFC) -->
    <AddAttendeeModal
      ref="addAttendeeModalRef"
      :endpoints="endpoints"
      :filter-data="filterData"
      :grid-instance-ref="gridInstanceRef"
      :load-data="loadData"
      :get-highlighted-gathering="getHighlightedGathering"
      :highlight-gathering-column="highlightGatheringColumn"
      :set-last-newcomer="setLastNewcomer"
      :locate-attendee-in-grid="locateAttendeeInGrid"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { FilterState } from './types';
import { addYears, MAX_DATE_RANGE_YEARS } from './composables/useLookups';
import { useEndpoints } from './composables/useEndpoints';
import { useAttendanceLogic } from './composables/useAttendanceLogic';
import { useAttendingMeetsEditor } from './composables/useAttendingMeetsEditor';
import { useRosterGrid } from './composables/useRosterGrid';
import { useRosterFilter } from './composables/useRosterFilter';
import { useSmartPolling } from './composables/useSmartPolling';
import AddAttendeeModal from './components/AddAttendeeModal.vue';

console.log('Attendees App.vue (Vue 3 SFC) loaded!');

if ((window as any).Attendees?.utilities?.clearGridStatesInSessionStorage) {
  (window as any).Attendees.utilities.clearGridStatesInSessionStorage(
    (window as any).Attendees.utilities.datagridStorageKeys?.['rostersListView']
  );
}

const storageOptsKey = (window as any).Attendees?.utilities?.datagridStorageKeys?.['rostersListViewOpts'];
const storedMeets = (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'selectedMeetSlugs');
const storedFrom = (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'filterFromString');
const storedTill = (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'filterTillString');
const storedShowPhotos = (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'showPhotos');
const storedShowSiblings = (window as any).Attendees?.utilities?.accessItemFromSessionStorage(storageOptsKey, 'showSiblings');

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

if (initialStart && initialEnd) {
  const maxAllowedEnd = addYears(initialStart, MAX_DATE_RANGE_YEARS);
  if (maxAllowedEnd && initialEnd > maxAllowedEnd) {
    initialEnd = maxAllowedEnd;
  }
}

// DOM Refs
const filterFormRef = ref<HTMLElement | null>(null);
const dataGridRef = ref<HTMLElement | null>(null);
const gridInstanceRef = ref<any>(null);

// Global App State
const filterData = reactive<FilterState>({
  meets: Array.isArray(storedMeets) ? storedMeets : [],
  startDate: initialStart,
  endDate: initialEnd,
  showPhotos: storedShowPhotos === true || storedShowPhotos === 'true',
  showSiblings: storedShowSiblings === undefined || storedShowSiblings === null ? true : (storedShowSiblings === true || storedShowSiblings === 'true')
});

// Composables Hookup
const { endpoints, initEndpoints } = useEndpoints();
initEndpoints();

const attendanceLogic = useAttendanceLogic(endpoints, gridInstanceRef);
const reloadDataRef: { current: ((targetAttendeeId?: any) => Promise<any> | void) | null } = { current: null };

const attendingMeetsEditor = useAttendingMeetsEditor(
  endpoints,
  gridInstanceRef,
  filterData,
  (targetAttendeeId) => {
    if (reloadDataRef.current) {
      return reloadDataRef.current(targetAttendeeId);
    }
  }
);

const resetFiltersRef: { current: (() => void) | null } = { current: null };

const {
  initDataGrid,
  loadData,
  getHighlightedGathering,
  highlightGatheringColumn,
  setLastNewcomer,
  clearLastNewcomer,
  getLastNewcomer,
  locateAttendeeInGrid
} = useRosterGrid(
  endpoints,
  filterData,
  gridInstanceRef,
  attendanceLogic,
  attendingMeetsEditor,
  () => { if (resetFiltersRef.current) resetFiltersRef.current(); }
);

const { initFilterForm, resetFilters } = useRosterFilter(
  endpoints,
  filterData,
  loadData,
  gridInstanceRef,
  clearLastNewcomer,
  getLastNewcomer
);

resetFiltersRef.current = resetFilters;
reloadDataRef.current = loadData;

const { startPolling } = useSmartPolling(gridInstanceRef, filterData);

const addAttendeeModalRef = ref<any>(null);

/**
 * Opens the Add Attendee modal dialog.
 */
const openAddAttendee = () => {
  addAttendeeModalRef.value?.open();
};

onMounted(() => {
  initEndpoints();
  if (attendanceLogic && typeof (attendanceLogic as any).initSignaturePopup === 'function') {
    (attendanceLogic as any).initSignaturePopup();
  }
  if (attendingMeetsEditor && typeof attendingMeetsEditor.preloadLookups === 'function') {
    attendingMeetsEditor.preloadLookups();
  }

  if (dataGridRef.value) {
    initDataGrid(dataGridRef.value);
  }
  if (filterFormRef.value) {
    initFilterForm(filterFormRef.value);
  }
  if (filterData.meets && filterData.meets.length > 0) {
    loadData();
  }

  startPolling();
});
</script>
