<template>
  <DxPopup
    v-model:visible="visible"
    :drag-enabled="!isMobile"
    :show-close-button="false"
    :wrapper-attr="{ class: 'add-attendee-popup-wrapper' }"
    @showing="onShowing"
    @shown="onShown"
    @hiding="onHiding"
  >
    <template #title>
      <div class="d-flex align-items-center justify-content-between popup-title-container w-100">
        <div class="d-flex align-items-center flex-grow-1 overflow-hidden me-2">
          <button
            type="button"
            class="btn btn-sm btn-outline-secondary py-0 px-2 me-2 back-to-search-btn"
            :class="{ 'd-none': currentStep !== 'onboard' }"
            title="Back to Search"
            @click="switchToSearch"
          >
            <i class="fas fa-arrow-left"></i>
          </button>
          <span class="popup-title-text fw-bold text-dark text-truncate">
            {{ currentStep === 'onboard' ? 'Add Attendee to Rosters / New Attendee Registration' : "Add Attendee to Rosters, Welcome! Let's search first." }}
          </span>
        </div>
        <button
          type="button"
          class="btn-close popup-close-btn dx-closebutton flex-shrink-0"
          aria-label="Close"
          title="Close"
          @click="close"
        ></button>
      </div>
    </template>

    <div class="add-attendee-modal-content">
      <!-- 1. Target Meet & Gathering side-by-side header -->
      <div class="row g-2 align-items-center mb-3 p-2 bg-light rounded border meet-gathering-header">
        <div class="col-md-6 col-12 d-flex align-items-center">
          <label class="form-label mb-0 me-2 fw-semibold text-secondary target-meet-label flex-shrink-0">Target Meet:</label>
          <div class="flex-grow-1 overflow-hidden target-meet-container">
            <select
              v-if="filterData.meets && filterData.meets.length > 1"
              v-model="selectedMeetSlug"
              class="form-select form-select-sm target-meet-dropdown"
              @change="onMeetChange"
            >
              <option v-for="slug in filterData.meets" :key="slug" :value="slug">
                {{ getMeetDisplayName(slug) }}
              </option>
            </select>
            <strong v-else class="text-truncate d-inline-block" style="max-width: 100%;" :title="currentMeetDisplayName">
              {{ currentMeetDisplayName }}
            </strong>
          </div>
        </div>
        <div class="col-md-6 col-12 d-flex align-items-center">
          <label class="form-label mb-0 me-2 fw-semibold text-secondary target-gathering-label flex-shrink-0">Gathering:</label>
          <div class="flex-grow-1">
            <select v-model="selectedGatheringId" class="form-select form-select-sm target-gathering-dropdown">
              <option v-if="meetGatherings.length === 0" value="">(No gatherings available)</option>
              <option
                v-for="g in meetGatherings"
                :key="g.id || g.start"
                :value="g.id ? String(g.id) : (g.start ? `start_${g.start}` : '')"
              >
                {{ formatGatheringOption(g) }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- 2. Search View Container (Step 1) -->
      <AttendeeSearchStep
        v-show="currentStep === 'search'"
        ref="searchStepRef"
        :endpoints="endpoints"
        :search-endpoint="endpoints.searchAttendees"
        :selected-meet-slug="selectedMeetSlug"
        :show-photos="filterData.showPhotos"
        @switch-to-onboard="switchToOnboard"
        @locate-candidate="locateCandidateInRoster"
        @enroll-candidate="handleCandidateEnrollAndCheckIn"
        @adopt-candidate="onAdoptFromSearch"
      />

      <!-- 3. Fast Onboard Form Container (Step 2) -->
      <div v-show="currentStep === 'onboard'" class="onboard-view-container">
        <!-- Attendee Form Cards -->
        <div class="mb-3">
          <AttendeeFormCard
            v-for="(att, aIdx) in attendees"
            :key="att.id"
            :attendee="att"
            :index="aIdx"
            :attendees-count="attendees.length"
            :is-kid-meet="isKidMeet"
            :show-insurer="showInsurer"
            :divisions-list="divisionsList"
            :attendee-relations-list="attendeeRelationsList"
            :available-families="availableFamilies"
            :has-other-linked-family="hasOtherLinkedFamilyForAttendee(aIdx)"
            :linked-family-id="linkedFamilyId"
            :linked-family-name="linkedFamilyName"
            :grades-list="gradesList"
            :search-endpoint="endpoints.searchAttendees"
            :selected-meet-slug="selectedMeetSlug"
            @remove-attendee="removeAttendee"
            @add-attendee="onAddAttendee"
            @add-contact="(cIdx) => addAttendeeContact(att, cIdx)"
            @remove-contact="(cIdx) => removeAttendeeContact(att, cIdx)"
            @adopt-candidate="(cand) => adoptCandidateIntoFormItem(att, cand, false, rawRelationsList)"
            @unlink-candidate="() => unlinkCandidate(att)"
          />
        </div>

        <!-- Guardian / Companion Section -->
        <div class="mb-3 border rounded p-2 bg-white guardian-section">
          <!-- Unaccompanied minor check for kids -->
          <div v-if="isKidMeet" class="form-check mb-2 unaccompanied-minor-check">
            <input
              id="unaccompaniedCheck"
              v-model="unaccompaniedMinor"
              type="checkbox"
              class="form-check-input ob-unaccompanied"
            />
            <label class="form-check-label small fw-semibold text-danger" for="unaccompaniedCheck">
              Child arrived alone (no accompanying guardian)
            </label>
          </div>

          <!-- Section header toggle -->
          <div
            v-if="!unaccompaniedMinor"
            class="d-flex justify-content-between align-items-center cursor-pointer p-1 rounded bg-light guardian-section-header"
            style="cursor: pointer;"
            @click="toggleGuardianSection(isKidMeet)"
          >
            <div class="d-flex align-items-center">
              <span class="me-2 text-secondary companion-toggle-indicator" v-html="companionCollapseIconHtml"></span>
              <strong class="text-dark small">
                <i class="fas fa-user-friends me-1 text-secondary"></i>
                Companion Information {{ isKidMeet ? '(Required for kids)' : '(Optional for adults)' }}
              </strong>
            </div>
            <span class="badge bg-secondary opacity-75" style="font-size: 0.72rem;">
              {{ guardianCollapsed ? 'Click to Expand' : 'Click to Collapse' }}
            </span>
          </div>

          <!-- Companion Cards Content -->
          <div v-show="!guardianCollapsed && !unaccompaniedMinor" class="mt-2 guardian-section-content">
            <template v-for="(comp, cIdx) in companions" :key="comp.id">
              <CompanionFormCard
                v-if="isCompanionVisible(cIdx)"
                :companion="comp"
                :index="cIdx"
                :companions-count="companions.length"
                :is-kid-meet="isKidMeet"
                :divisions-list="divisionsList"
                :companion-relations-list="companionRelationsList"
                :available-families="availableFamilies"
                :has-other-linked-family="hasOtherLinkedFamily(cIdx)"
                :linked-family-id="linkedFamilyId"
                :linked-family-name="linkedFamilyName"
                :search-endpoint="endpoints.searchAttendees"
                :selected-meet-slug="selectedMeetSlug"
                @remove-companion="onRemoveCompanion"
                @add-companion="onAddCompanion"
                @add-contact="(ctIdx) => addCompanionContact(comp, ctIdx)"
                @remove-contact="(ctIdx) => removeCompanionContact(comp, ctIdx)"
                @adopt-candidate="(cand) => adoptCandidateIntoFormItem(comp, cand, true, familyRelationsList)"
                @unlink-candidate="() => unlinkCandidate(comp)"
              />
            </template>
          </div>
        </div>

        <!-- Bottom Action Bar -->
        <div class="d-flex justify-content-end gap-2 mt-3 pt-2 border-top">
          <button
            type="button"
            class="btn btn-sm btn-secondary cancel-onboard-btn"
            :disabled="isSubmitting"
            @click="switchToSearch"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-sm btn-success submit-fast-onboard-btn ob-submit-btn"
            :disabled="isSubmitting"
            @click="submitForm"
          >
            <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-1" role="status"></span>
            <i v-else class="fas fa-check-circle me-1"></i>
            Register & Check In
          </button>
        </div>
      </div>
    </div>
  </DxPopup>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { DxPopup } from 'devextreme-vue/popup';
import notify from 'devextreme/ui/notify';
import { Endpoints, FilterState, Gathering } from '../types';
import {
  sharedGradeConverter,
  sharedOrganizationDivisions,
  sharedFamilyRelations,
  sharedRawRelations,
  loadGradeConverter,
  loadOrganizationDivisions,
  loadFamilyRelations,
  loadMeetGatherings,
  gatheringsRegistry,
  meetsMap,
  meetsInfoMap,
  ensureMeetsLoaded,
  charactersMap,
  WARNING_NOTIFY_TIME,
  SUCCESS_NOTIFY_TIME
} from '../composables/useLookups';
import {
  useFastOnboardForm,
  adoptCandidateIntoFormItem
} from '../composables/useFastOnboardForm';
import AttendeeSearchStep from './AttendeeSearchStep.vue';
import AttendeeFormCard from './AttendeeFormCard.vue';
import CompanionFormCard from './CompanionFormCard.vue';

const props = defineProps<{
  endpoints: Endpoints;
  filterData: FilterState;
  gridInstanceRef: any;
  loadData: (targetAttendeeId?: any, gatheringId?: any) => Promise<any> | void;
  getHighlightedGathering?: () => any;
  highlightGatheringColumn?: (colIndex: number) => void;
  setLastNewcomer?: (newcomer: any) => void;
}>();

// Form management composable
const {
  attendees,
  companions,
  guardianCollapsed,
  unaccompaniedMinor,
  isSubmitting,
  availableFamilies,
  linkedFamilyId,
  linkedFamilyName,
  addAttendee,
  removeAttendee,
  addAttendeeContact,
  removeAttendeeContact,
  addCompanion,
  removeCompanion,
  removeCompanion1,
  addCompanionContact,
  removeCompanionContact,
  toggleGuardianSection,
  isCompanionVisible,
  resetForm,
  submitFastOnboard
} = useFastOnboardForm(props.endpoints);

// Modal state
const visible = ref(false);
const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false);
const currentStep = ref<'search' | 'onboard'>('search');
const selectedMeetSlug = ref('');
const selectedGatheringId = ref<string | null>(null);
const meetGatherings = ref<Gathering[]>([]);

// Lookup lists
const divisionsList = ref<any[]>([]);
const gradesList = ref<any[]>([]);
const rawRelationsList = ref<any[]>([]);
const familyRelationsList = ref<any[]>([]);

const searchStepRef = ref<InstanceType<typeof AttendeeSearchStep> | null>(null);

/**
 * Computes current Meet definition object from meetsMap.
 */
const currentMeet = computed(() => {
  if (!selectedMeetSlug.value && props.filterData.meets && props.filterData.meets.length > 0) {
    selectedMeetSlug.value = props.filterData.meets[0];
  }
  const slug = selectedMeetSlug.value;
  return slug ? (meetsMap.get(slug) || meetsMap.get(String(slug))) : null;
});

/**
 * Computes display name for currently selected meet.
 */
const currentMeetDisplayName = computed(() => {
  const slug = selectedMeetSlug.value;
  const m = currentMeet.value;
  if (m && (m.display_name || m.name)) return m.display_name || m.name;
  if (slug) {
    const fromInfo = meetsInfoMap.get(slug) || meetsInfoMap.get(String(slug));
    if (fromInfo) return typeof fromInfo === 'string' ? fromInfo : (fromInfo.display_name || fromInfo.name);
  }
  return slug || 'Selected Meet';
});

/**
 * Retrieves display name for a specific meet slug.
 * @param slug Meet slug string.
 */
const getMeetDisplayName = (slug: string): string => {
  if (!slug) return '';
  const m = meetsMap.get(slug) || meetsMap.get(String(slug));
  if (m && (m.display_name || m.name)) return m.display_name || m.name;
  const fromInfo = meetsInfoMap.get(slug) || meetsInfoMap.get(String(slug));
  if (fromInfo) return typeof fromInfo === 'string' ? fromInfo : (fromInfo.display_name || fromInfo.name);
  return slug;
};

/**
 * Determines whether current meet is for children based on show_attendee_infos configuration.
 */
const isKidMeet = computed(() => {
  const m = currentMeet.value;
  const showInfos = m?.show_attendee_infos || (m?.infos && m.infos.show_attendee_infos) || {};
  return Boolean(showInfos['infos-grade'] || showInfos['grade']);
});

/**
 * Determines whether medical insurer field should be displayed.
 */
const showInsurer = computed(() => {
  const m = currentMeet.value;
  const showInfos = m?.show_attendee_infos || (m?.infos && m.infos.show_attendee_infos) || {};
  return Boolean(showInfos['infos-insurer'] || showInfos['insurer']);
});

/**
 * Resolves division ID associated with current meet.
 */
const meetDivisionId = computed(() => {
  const m = currentMeet.value;
  return m?.division || m?.division_id || (m?.assembly && m.assembly.division_id) || null;
});

/**
 * Builds formatted option label for raw relations dropdown list.
 */
const attendeeRelationsList = computed(() => {
  return rawRelationsList.value.map(r => ({
    id: r.id,
    label: (r.title || '').trim() ? (r.title.trim().charAt(0).toUpperCase() + r.title.trim().slice(1)) : `Relation #${r.id}`
  }));
});

/**
 * Builds formatted option label for family relations dropdown list.
 */
const companionRelationsList = computed(() => {
  return familyRelationsList.value.map(r => ({
    id: r.id,
    label: (r.title || '').trim() ? (r.title.trim().charAt(0).toUpperCase() + r.title.trim().slice(1)) : `Relation #${r.id}`
  }));
});

/**
 * Synchronizes default relationship for attendees when raw relations list updates.
 */
watch(rawRelationsList, (newRelations) => {
  if (newRelations && newRelations.length > 0) {
    const selfRel = newRelations.find(r => (r.title || '').trim().toLowerCase() === 'self');
    if (selfRel) {
      attendees.value.forEach(att => {
        if (!att.relationship || att.relationship === 'self' || !newRelations.some(r => String(r.id) === String(att.relationship))) {
          att.relationship = String(selfRel.id);
        }
      });
    }
  }
});

/**
 * Computes companion section toggle indicator icon HTML to prevent FontAwesome SVG duplication.
 */
const companionCollapseIconHtml = computed(() => {
  const iconClass = guardianCollapsed.value ? 'fa-caret-right' : 'fa-caret-down';
  return `<i class="fas ${iconClass} companion-collapse-icon" style="font-size: 1.15rem;"></i>`;
});

/**
 * Retrieves list of gatherings registered for the specified meet ID.
 * @param meetId Meet ID number or string.
 */
const getGatheringsForMeet = (meetId: any): Gathering[] => {
  if (!meetId) return [];
  const seen = new Set();
  const list: Gathering[] = [];
  for (const g of gatheringsRegistry.values()) {
    if (g && String(g.meet_id) === String(meetId) && g.id && !seen.has(g.id)) {
      seen.add(g.id);
      list.push(g);
    }
  }
  list.sort((a, b) => new Date(a.start || 0).getTime() - new Date(b.start || 0).getTime());
  return list;
};

/**
 * Resolves the most relevant upcoming or ongoing gathering from gatherings list.
 * @param gatherings List of gatherings for meet.
 */
const getUpcomingOrOngoingGathering = (gatherings: Gathering[]): Gathering | null => {
  if (!gatherings || gatherings.length === 0) return null;
  const now = Date.now();
  const thirtyMinutes = 30 * 60 * 1000;

  const ongoing = gatherings.find(g => {
    if (!g.start) return false;
    const s = new Date(g.start).getTime();
    if (isNaN(s)) return false;
    let f = g.finish ? new Date(g.finish).getTime() : NaN;
    if (isNaN(f)) f = s + 2 * 60 * 60 * 1000;
    return s <= now && now <= f;
  });
  if (ongoing) return ongoing;

  const within30Mins = gatherings
    .filter(g => {
      if (!g.start) return false;
      const s = new Date(g.start).getTime();
      return !isNaN(s) && s > now && s <= (now + thirtyMinutes);
    })
    .sort((a, b) => new Date(a.start || 0).getTime() - new Date(b.start || 0).getTime());
  if (within30Mins.length > 0) return within30Mins[0];

  const upcomingList = gatherings
    .filter(g => {
      if (!g.start) return false;
      const s = new Date(g.start).getTime();
      return !isNaN(s) && s > now;
    })
    .sort((a, b) => new Date(a.start || 0).getTime() - new Date(b.start || 0).getTime());
  if (upcomingList.length > 0) return upcomingList[0];

  const pastList = gatherings
    .filter(g => {
      if (!g.start) return false;
      const s = new Date(g.start).getTime();
      return !isNaN(s) && s <= now;
    })
    .sort((a, b) => new Date(b.start || 0).getTime() - new Date(a.start || 0).getTime());
  if (pastList.length > 0) return pastList[0];

  return gatherings[0];
};

/**
 * Formats a gathering entity into a human-readable dropdown option text.
 * @param g Gathering object.
 */
const formatGatheringOption = (g: Gathering): string => {
  const meetName = g.meet_display_name || (g.meet_id ? (meetsInfoMap.get(g.meet_id) || meetsInfoMap.get(String(g.meet_id))) : '');
  const nameSuffix = meetName ? ` - ${meetName}` : (g.id ? ` - Gathering #${g.id}` : '');
  if (!g.start) return (meetName as string) || `Gathering #${g.id}`;
  const d = new Date(g.start);
  if (isNaN(d.getTime())) return (meetName as string) || `Gathering #${g.id}`;
  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const dayName = daysOfWeek[d.getDay()];
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const mins = String(d.getMinutes()).padStart(2, '0');
  const timeStr = `${hours}:${mins}`;
  return `${dayName} ${m}/${day}/${y} ${timeStr}${nameSuffix}`;
};

/**
 * Handles target meet selection change, refreshing gatherings and resetting form state.
 */
const onMeetChange = async () => {
  const m = currentMeet.value;
  const gatherings = await loadMeetGatherings(selectedMeetSlug.value, m ? m.id : null, props.endpoints.gatherings);
  meetGatherings.value = gatherings;
  const upcoming = getUpcomingOrOngoingGathering(gatherings);
  selectedGatheringId.value = upcoming ? (upcoming.id ? String(upcoming.id) : (upcoming.start ? `start_${upcoming.start}` : null)) : (gatherings.length > 0 ? (gatherings[0].id ? String(gatherings[0].id) : (gatherings[0].start ? `start_${gatherings[0].start}` : null)) : null);

  guardianCollapsed.value = !isKidMeet.value;
  if (attendees.value[0]) {
    attendees.value[0].division_id = meetDivisionId.value ? String(meetDivisionId.value) : attendees.value[0].division_id;
  }
};

/**
 * Switches modal view to Step 1 search and resets form candidate linkages.
 */
const switchToSearch = () => {
  currentStep.value = 'search';
  attendees.value.forEach(a => {
    a.attendee_id = null;
    a.linkedCandidate = null;
    a.candidateMatches = [];
  });
  companions.value.forEach(c => {
    c.attendee_id = null;
    c.linkedCandidate = null;
    c.candidateMatches = [];
  });
  searchStepRef.value?.focusInput();
};

/**
 * Switches modal view to Step 2 onboarding form, optionally prefilling parsed names.
 * @param query Optional search query to parse into first and last names.
 */
const switchToOnboard = (query?: any) => {
  const queryStr = (typeof query === 'string' ? query : (searchStepRef.value?.getSearchQuery?.() || '')).trim();
  currentStep.value = 'onboard';
  guardianCollapsed.value = !isKidMeet.value;

  if (attendees.value.length === 0) {
    addAttendee(meetDivisionId.value, divisionsList.value, rawRelationsList.value);
  } else if (rawRelationsList.value.length > 0 && attendees.value[0]) {
    const selfRel = rawRelationsList.value.find(r => (r.title || '').trim().toLowerCase() === 'self');
    if (selfRel && (!attendees.value[0].relationship || attendees.value[0].relationship === 'self' || !rawRelationsList.value.some(r => String(r.id) === String(attendees.value[0].relationship)))) {
      attendees.value[0].relationship = String(selfRel.id);
    }
  }
  if (companions.value.length === 0) {
    addCompanion(divisionsList.value, isKidMeet.value, familyRelationsList.value);
  }

  if (queryStr && attendees.value[0]) {
    const isChinese = /[\u4e00-\u9fa5]/.test(queryStr);
    if (isChinese) {
      if (queryStr.length === 2) {
        attendees.value[0].last_name2 = queryStr[0];
        attendees.value[0].first_name2 = queryStr[1];
      } else if (queryStr.length === 3) {
        attendees.value[0].last_name2 = queryStr[0];
        attendees.value[0].first_name2 = queryStr.slice(1);
      } else {
        attendees.value[0].first_name2 = queryStr;
      }
    } else {
      const parts = queryStr.split(/\s+/);
      if (parts.length > 1) {
        attendees.value[0].first_name = parts.slice(0, -1).join(' ');
        attendees.value[0].last_name = parts[parts.length - 1];
      } else {
        attendees.value[0].first_name = queryStr;
      }
    }
  }
};

/**
 * Adopts a candidate chosen from Step 1 search cards into the onboarding form.
 * @param cand Matched candidate record.
 */
const onAdoptFromSearch = (cand: any) => {
  switchToOnboard();
  if (attendees.value[0]) {
    adoptCandidateIntoFormItem(attendees.value[0], cand, false, rawRelationsList.value);
  }
};

/**
 * Handles adding an additional Attendee card with current defaults.
 */
const onAddAttendee = () => {
  addAttendee(meetDivisionId.value, divisionsList.value, rawRelationsList.value);
};

/**
 * Handles adding an additional Companion card with current defaults.
 */
const onAddCompanion = () => {
  addCompanion(divisionsList.value, isKidMeet.value, familyRelationsList.value);
};

/**
 * Handles removing a companion card by index.
 * @param idx Index of companion to remove.
 */
const onRemoveCompanion = (idx: number) => {
  if (idx === 0) {
    removeCompanion1();
  } else {
    removeCompanion(idx);
  }
};

/**
 * Checks whether any other companion or attendee in the modal already has a linked candidate/family.
 * Only one family can be linked per registration session.
 * @param compIdx Current companion card index.
 */
const hasOtherLinkedFamily = (compIdx: number): boolean => {
  const otherCompLinked = companions.value.some((c, idx) =>
    idx !== compIdx && Boolean(c.attendee_id && (c.family_id || c.linkedCandidate))
  );
  if (otherCompLinked) return true;

  const attendeeLinked = attendees.value.some(a =>
    Boolean(a.attendee_id && (a.family_id || a.linkedCandidate))
  );
  return attendeeLinked;
};

/**
 * Checks whether any other attendee or companion in the modal already has a linked candidate/family.
 * @param attIdx Current attendee card index.
 */
const hasOtherLinkedFamilyForAttendee = (attIdx: number): boolean => {
  const otherAttLinked = attendees.value.some((a, idx) =>
    idx !== attIdx && Boolean(a.attendee_id && (a.family_id || a.linkedCandidate))
  );
  if (otherAttLinked) return true;

  const compLinked = companions.value.some(c =>
    Boolean(c.attendee_id && (c.family_id || c.linkedCandidate))
  );
  return compLinked;
};

/**
 * Unlinks an adopted candidate from a form item, resetting to a clean new record.
 * @param item Form item to unlink.
 */
const unlinkCandidate = async (item: any) => {
  item.attendee_id = null;
  item.linkedCandidate = null;
  item.candidateMatches = [];
  item.family_id = '';
  item.contacts = [{ type: 'phone', value: '' }];
  item.gender = 'UNSPECIFIED';
  if ('byear' in item) {
    item.byear = '';
    item.bmonth = '';
    item.bday = '';
    item.grade = '';
    item.food_pref = '';
    item.insurer = '';
  }

  // Refresh candidate duplicate matches so user can pick another candidate
  const parts = [
    item.first_name || '',
    item.last_name || '',
    item.first_name2 || '',
    item.last_name2 || ''
  ].map((s: string) => s.trim()).filter(Boolean);
  const q = parts.join(' ').replace(/\s+/g, ' ').trim();
  if (q.length >= 2) {
    const endpointUrl = props.endpoints?.searchAttendees || '/persons/api/search_attendees_for_roster/';
    try {
      const meetSlug = encodeURIComponent(selectedMeetSlug.value || '');
      const res = await fetch(`${endpointUrl}?meet_slug=${meetSlug}&q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        if (!item.attendee_id) {
          item.candidateMatches = Array.isArray(data) ? data : [];
        }
      }
    } catch {
      // Ignore background candidate search errors
    }
  }
};

/**
 * Locates and searches for a candidate attendee inside the main DataGrid.
 * @param cand Candidate object.
 */
const locateCandidateInRoster = async (cand: any) => {
  close();
  const grid = (props.gridInstanceRef && typeof props.gridInstanceRef.searchByText === 'function')
    ? props.gridInstanceRef
    : (props.gridInstanceRef?.value && typeof props.gridInstanceRef.value.searchByText === 'function')
      ? props.gridInstanceRef.value
      : (window as any).DevExpress?.ui?.dxDataGrid?.getInstance(document.getElementById('rosters-datagrid-container'));

  const targetName = (cand.name || `${cand.first_name || ''} ${cand.last_name || ''}`).replace(/\s+/g, ' ').trim();

  if (grid && typeof grid.searchByText === 'function') {
    grid.searchByText(targetName);

    const candId = cand.attending_id || cand.id;
    if (candId && typeof grid.selectRows === 'function') {
      try {
        await grid.selectRows([candId], false);
        if (typeof grid.getRowIndexByKey === 'function') {
          const rIdx = grid.getRowIndexByKey(candId);
          if (rIdx >= 0 && typeof grid.getRowElement === 'function') {
            const rowEl = grid.getRowElement(rIdx);
            const domEl = rowEl && (rowEl[0] || (rowEl.length ? rowEl[0] : rowEl));
            if (domEl) {
              if (typeof domEl.scrollIntoView === 'function') {
                domEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
              domEl.classList.add('roster-row-newly-added');
              setTimeout(() => domEl.classList.remove('roster-row-newly-added'), 3500);
            }
          }
        }
      } catch (e) {
        console.warn('Error selecting located candidate row:', e);
      }
    }
  }

  notify(`Located in roster: ${targetName}. Clear search bar to show all attendees.`, 'info', SUCCESS_NOTIFY_TIME);
};

/**
 * Directly enrolls an existing candidate into the target meet/gathering from search view.
 * @param cand Candidate object.
 */
const handleCandidateEnrollAndCheckIn = async (cand: any) => {
  const meetObj = meetsMap.get(selectedMeetSlug.value) || meetsMap.get(String(selectedMeetSlug.value));
  if (!meetObj) return;

  if ((window as any).Attendees?.utilities) {
    (window as any).Attendees.utilities.editingEnabled = true;
  }

  try {
    let attendingId = cand.attending_id;
    if (!attendingId) {
      const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value;
      const attgRes = await fetch(props.endpoints.attendings, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Target-Attendee-Id': String(cand.id),
          'X-CSRFToken': csrfToken
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

    let targetGatheringId: number | null = null;
    let targetGatheringStart: string | null = null;
    const chosenVal = selectedGatheringId.value;

    if (chosenVal) {
      if (chosenVal.startsWith('start_')) {
        targetGatheringStart = chosenVal.replace(/^start_/, '');
      } else if (/^\d+$/.test(chosenVal)) {
        targetGatheringId = parseInt(chosenVal, 10);
      }
    }

    if (!targetGatheringId && !targetGatheringStart) {
      const meetGatheringsList = getGatheringsForMeet(meetObj.id);
      const upcoming = getUpcomingOrOngoingGathering(meetGatheringsList);
      if (upcoming) {
        if (upcoming.id && /^\d+$/.test(String(upcoming.id))) {
          targetGatheringId = parseInt(String(upcoming.id), 10);
        } else if (upcoming.start) {
          targetGatheringStart = upcoming.start;
        }
      }
    }

    const scheduledCategory = props.endpoints.scheduledCategory
      || (document.getElementById('app')?.dataset?.scheduledCategory ? parseInt(document.getElementById('app')!.dataset.scheduledCategory!, 10) : 1);

    const nowTime = Date.now();
    const defaultWeeks = (meetObj && meetObj.infos && meetObj.infos.default_attendingmeet_in_weeks)
      ? Number(meetObj.infos.default_attendingmeet_in_weeks)
      : 53;

    let baseStartMs = nowTime;
    if (targetGatheringStart) {
      baseStartMs = new Date(targetGatheringStart).getTime();
    } else if (props.filterData && props.filterData.startDate && props.filterData.endDate) {
      const filterStartMs = new Date(props.filterData.startDate).getTime();
      const filterEndMs = new Date(props.filterData.endDate).getTime();
      if (nowTime < filterStartMs || nowTime > filterEndMs) {
        baseStartMs = filterStartMs;
      }
    }

    const effectiveStartMs = baseStartMs;
    const effectiveFinishMs = effectiveStartMs + defaultWeeks * 7 * 24 * 60 * 60 * 1000;

    const amPayload = {
      attending: attendingId,
      meet: meetObj.id,
      character: meetObj.major_character || 1,
      category: (meetObj && meetObj.infos && meetObj.infos.active_category) || scheduledCategory,
      start: new Date(effectiveStartMs).toISOString(),
      finish: new Date(effectiveFinishMs).toISOString()
    };

    const isUpdateAm = Boolean(cand.attendingmeet_id);
    const amEndpoint = (props.endpoints.attendingmeets || '').endsWith('/')
      ? props.endpoints.attendingmeets
      : `${props.endpoints.attendingmeets}/`;
    const amUrl = isUpdateAm ? `${amEndpoint}${cand.attendingmeet_id}/` : amEndpoint;
    const amMethod = isUpdateAm ? 'PATCH' : 'POST';

    const csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value;
    const amRes = await fetch(amUrl, {
      method: amMethod,
      headers: {
        'Content-Type': 'application/json',
        'X-Target-Attendee-Id': String(cand.id),
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(amPayload)
    });

    if (!amRes.ok) {
      const amErr = await amRes.json().catch(() => ({}));
      throw new Error(amErr.detail || amErr.error || `Failed to enroll in meet (HTTP ${amRes.status})`);
    }

    const attPayload: any = {
      attending: attendingId,
      character: meetObj.major_character || 1,
      category: 9,
      start: targetGatheringStart || new Date().toISOString(),
      meet: meetObj.id
    };
    if (targetGatheringId) {
      attPayload.gathering = targetGatheringId;
    } else if (targetGatheringStart) {
      attPayload.gathering = null;
      attPayload.gathering_start = targetGatheringStart;
    }

    const attRes = await fetch(props.endpoints.attendances, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(attPayload)
    });

    if (!attRes.ok) {
      const attErr = await attRes.json().catch(() => ({}));
      throw new Error(attErr.detail || attErr.error || `Attendance check-in failed (HTTP ${attRes.status})`);
    }

    const attData = await attRes.json().catch(() => ({}));
    const confirmedGatheringId = attData.gathering || targetGatheringId || null;

    if (typeof props.setLastNewcomer === 'function') {
      const candChar = (meetObj?.major_character ? (charactersMap.get(meetObj.major_character)?.display_name || charactersMap.get(String(meetObj.major_character))?.display_name) : null)
        || cand.character_name
        || 'Attendee';
      props.setLastNewcomer({
        id: cand.id,
        name: cand.name || `${cand.first_name || ''} ${cand.last_name || ''}`.trim(),
        grade: cand.infos?.grade ?? cand.grade ?? '',
        team: cand.team_name || cand.team || '',
        gender: cand.gender || '',
        character: candChar,
        meetSlug: selectedMeetSlug.value,
        meetName: meetObj?.display_name || selectedMeetSlug.value || '',
        gatheringId: confirmedGatheringId,
        checkedIn: true
      });
    }

    notify(`Enrolled and checked in ${cand.name} successfully!`, 'success', 2500);
    close();
    await props.loadData(cand.id, confirmedGatheringId);
  } catch (err: any) {
    notify(err.message, 'error', WARNING_NOTIFY_TIME);
  } finally {
    if ((window as any).Attendees?.utilities) {
      (window as any).Attendees.utilities.editingEnabled = false;
    }
  }
};

/**
 * Handles onboard form submission and post-creation UI updates.
 */
const submitForm = async () => {
  await submitFastOnboard({
    currentMeet: currentMeet.value,
    selectedMeetSlug: selectedMeetSlug.value,
    selectedGatheringId: selectedGatheringId.value,
    isKidMeet: isKidMeet.value,
    showInsurer: showInsurer.value,
    divisionsList: divisionsList.value,
    onSuccess: async (result: any) => {
      const registeredNames = (result.attendees && result.attendees.length > 1)
        ? result.attendees.map((a: any) => a.attendee_name).join(', ')
        : (result.attendee_name || 'attendee');

      if (typeof props.setLastNewcomer === 'function') {
        const m = currentMeet.value;
        const currentMeetName = m?.display_name || selectedMeetSlug.value || '';
        const createdList = (result.attendees && result.attendees.length > 0) ? result.attendees : [result];
        const lastCreated = createdList[createdList.length - 1];
        const createdChar = lastCreated.character_name
          || result.character_name
          || (m?.major_character ? (charactersMap.get(m.major_character)?.display_name || charactersMap.get(String(m.major_character))?.display_name) : null)
          || 'Attendee';

        props.setLastNewcomer({
          id: lastCreated.attendee_id || result.attendee_id,
          name: lastCreated.attendee_name || result.attendee_name,
          grade: lastCreated.grade ?? '',
          team: lastCreated.team_name ?? '',
          gender: lastCreated.gender ?? result.gender ?? '',
          character: createdChar,
          meetSlug: selectedMeetSlug.value,
          meetName: currentMeetName,
          gatheringId: result.gathering_id || selectedGatheringId.value,
          checkedIn: true
        });
      }

      notify(`Registered ${registeredNames} and checked in successfully!`, 'success', SUCCESS_NOTIFY_TIME);
      close();
      const targetAttendeeIds = (result.attendees && result.attendees.length > 0)
        ? result.attendees.map((a: any) => a.attendee_id)
        : (result.attendee_id ? [result.attendee_id] : null);
      await props.loadData(targetAttendeeIds, result.gathering_id || selectedGatheringId.value);
    }
  });
};

/**
 * Lifecycle hook called when DxPopup is about to show.
 */
const onShowing = () => {
  if ((window as any).Attendees?.utilities) {
    (window as any).Attendees.utilities.editingEnabled = true;
  }
};

/**
 * Lifecycle hook called when DxPopup is fully shown, focusing search input.
 */
const onShown = () => {
  setTimeout(() => {
    searchStepRef.value?.focusInput();
  }, 50);
};

/**
 * Lifecycle hook called when DxPopup is hidden, resetting views.
 */
const onHiding = () => {
  switchToSearch();
  if ((window as any).Attendees?.utilities) {
    (window as any).Attendees.utilities.editingEnabled = false;
  }
};

/**
 * Closes the modal popup.
 */
const close = () => {
  visible.value = false;
};

/**
 * Opens the modal popup, initializes lookups, meet gatherings, and form state.
 */
const open = async () => {
  if (!props.filterData.meets || props.filterData.meets.length === 0) {
    notify('Please select at least one meet in the filter first.', 'warning', WARNING_NOTIFY_TIME);
    return;
  }

  await ensureMeetsLoaded(props.endpoints.meets, props.filterData.meets);

  if (sharedOrganizationDivisions.length > 0) {
    divisionsList.value = sharedOrganizationDivisions;
  } else {
    divisionsList.value = await loadOrganizationDivisions(props.endpoints.divisions);
  }

  if (sharedRawRelations.length > 0) {
    rawRelationsList.value = sharedRawRelations;
    familyRelationsList.value = sharedFamilyRelations;
  } else {
    await loadFamilyRelations(props.endpoints.relations);
    rawRelationsList.value = sharedRawRelations;
    familyRelationsList.value = sharedFamilyRelations;
  }

  if (sharedGradeConverter.length > 0) {
    gradesList.value = sharedGradeConverter;
  } else {
    loadGradeConverter();
    gradesList.value = sharedGradeConverter;
  }

  const highlighted = (typeof props.getHighlightedGathering === 'function') ? props.getHighlightedGathering() : null;
  let meetFromHighlight = null;
  if (highlighted && highlighted.meet_id) {
    meetFromHighlight = Array.from(meetsMap.values()).find(m => String(m.id) === String(highlighted.meet_id));
  }

  if (meetFromHighlight && props.filterData.meets.includes(meetFromHighlight.slug)) {
    selectedMeetSlug.value = meetFromHighlight.slug;
  } else {
    selectedMeetSlug.value = props.filterData.meets[0];
  }

  const m = currentMeet.value;
  const gatherings = await loadMeetGatherings(selectedMeetSlug.value, m ? m.id : null, props.endpoints.gatherings);
  meetGatherings.value = gatherings;

  if (highlighted && highlighted.id && gatherings.some(g => String(g.id) === String(highlighted.id))) {
    selectedGatheringId.value = String(highlighted.id);
  } else {
    const upcoming = getUpcomingOrOngoingGathering(gatherings);
    selectedGatheringId.value = upcoming ? (upcoming.id ? String(upcoming.id) : (upcoming.start ? `start_${upcoming.start}` : null)) : (gatherings.length > 0 ? (gatherings[0].id ? String(gatherings[0].id) : (gatherings[0].start ? `start_${gatherings[0].start}` : null)) : null);
  }

  searchStepRef.value?.resetSearch();
  currentStep.value = 'search';
  resetForm(meetDivisionId.value, divisionsList.value, rawRelationsList.value, familyRelationsList.value, isKidMeet.value);

  visible.value = true;
};

/**
 * Synchronizes selected meet slug and ensures meet lookups are loaded when filter meets update.
 */
watch(
  () => props.filterData.meets,
  async (newMeets) => {
    if (newMeets && newMeets.length > 0) {
      await ensureMeetsLoaded(props.endpoints.meets, newMeets);
      if (!selectedMeetSlug.value || !newMeets.includes(selectedMeetSlug.value)) {
        selectedMeetSlug.value = newMeets[0];
      }
    }
  },
  { deep: true, immediate: true }
);

/**
 * Handles global Escape key to close popup when visible.
 * @param e KeyboardEvent
 */
const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.key === 'Escape' || e.keyCode === 27) && visible.value) {
    e.stopPropagation();
    close();
  }
};

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown, true);
  if (props.filterData?.meets && props.filterData.meets.length > 0) {
    await ensureMeetsLoaded(props.endpoints.meets, props.filterData.meets);
  } else {
    await ensureMeetsLoaded(props.endpoints.meets);
  }
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown, true);
});

defineExpose({
  open,
  close
});
</script>
