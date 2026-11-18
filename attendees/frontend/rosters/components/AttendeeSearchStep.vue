<template>
  <div class="search-view-container">
    <div class="input-group input-group-sm mb-3">
      <input
        ref="searchInputRef"
        v-model="searchQuery"
        type="search"
        class="form-control omni-search-box"
        placeholder="Search by attendee name, contacts, or families/chaperons name..."
        autocomplete="off"
        @input="onSearchInput"
        @keydown.enter.prevent="executeSearch"
      />
      <button class="btn btn-primary search-submit-btn" type="button" @click="executeSearch">
        <i class="fas fa-search me-1"></i> Search
      </button>
    </div>
    <div class="search-candidates-list" style="max-height: 380px; overflow-y: auto;">
      <!-- Default search hint when no query has been searched -->
      <div v-if="!hasSearched" class="text-center text-muted p-4 small default-search-hint">
        <div class="mb-2"><i class="fas fa-search fa-2x text-secondary opacity-50"></i></div>
        <strong>Please search for attendee first</strong><br>
        Search by attendee name, phone, email, or guardian to prevent duplicate records. You can register a new attendee if no match is found.
      </div>

      <!-- Loading indicator -->
      <div v-else-if="isSearching" class="text-center p-4">
        <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
        <span class="text-muted small">Searching attendees...</span>
      </div>

      <!-- Error message -->
      <div v-else-if="searchError" class="alert alert-danger p-2 small text-center">
        <div class="mb-2"><i class="fas fa-exclamation-triangle me-1"></i> {{ searchError }}</div>
        <button
          type="button"
          class="btn btn-sm btn-outline-danger switch-to-onboard-btn"
          @click="emitSwitchToOnboard(searchQuery)"
        >
          <i class="fas fa-user-plus me-1"></i> Register "{{ searchQuery }}" as New Attendee
        </button>
      </div>

      <!-- Empty results: prompt to switch to onboarding -->
      <div v-else-if="searchResults.length === 0" class="p-3 text-center bg-light rounded border">
        <div class="mb-2 text-muted small">No attendee records found matching "{{ searchQuery }}" in the organization directory.</div>
        <button
          type="button"
          class="btn btn-sm btn-success switch-to-onboard-btn"
          @click="emitSwitchToOnboard(searchQuery)"
        >
          <i class="fas fa-user-plus me-1"></i> Register "{{ searchQuery }}" as New Attendee
        </button>
      </div>

      <!-- Candidate result cards -->
      <div v-else class="candidates-results-container">
        <div class="d-flex justify-content-between align-items-center mb-2 px-1">
          <span class="text-muted small">Matching candidates ({{ searchResults.length }}):</span>
          <button
            type="button"
            class="btn btn-sm btn-success switch-to-onboard-btn"
            @click="emitSwitchToOnboard(searchQuery)"
          >
            <i class="fas fa-user-plus me-1"></i> Register as New Attendee
          </button>
        </div>

        <div
          v-for="cand in searchResults"
          :key="cand.id"
          class="search-candidate-item"
          :class="{ 'already-enrolled': isCandidateEnrolled(cand) }"
        >
          <div class="d-flex align-items-center flex-grow-1 overflow-hidden me-3">
            <!-- Attendee photo (visible only when showPhotos filter option is enabled) -->
            <div v-if="showPhotos" class="attendee-photo-container flex-shrink-0">
              <img
                v-if="cand.photo_url"
                :src="cand.photo_url"
                class="attendee-photo"
                alt="Photo"
              />
              <div
                v-else
                class="attendee-photo d-flex justify-content-center align-items-center bg-light text-muted"
              >
                <i class="fas fa-user"></i>
              </div>
            </div>

            <!-- Candidate details -->
            <div class="attendee-links-container flex-grow-1 overflow-hidden">
              <div class="search-candidate-title text-truncate">
                {{ cand.name }}
              </div>
              <div class="search-candidate-subtitle text-truncate">
                {{ getCandidateSubtitle(cand) }}
              </div>
              <div
                v-if="isCandidateEnrolled(cand)"
                class="search-candidate-warning text-primary small mt-1"
              >
                <i class="fas fa-info-circle me-1"></i>
                This attendee is already enrolled in this meet (may be on another page). Please check them in directly on the roster table.
              </div>
            </div>
          </div>

          <!-- Actions & Badges aligned with rosters_list_view.js -->
          <div class="search-candidate-actions d-flex align-items-center flex-shrink-0 ms-2">
            <!-- 1. Enrolled in this meet -->
            <template v-if="isCandidateEnrolled(cand)">
              <span class="badge bg-info text-dark me-2">
                <i class="fas fa-check-circle me-1"></i> Already Enrolled
              </span>
              <button
                type="button"
                class="btn btn-sm btn-outline-primary locate-cand-btn"
                title="Close popup and locate attendee in roster"
                @click="emitLocateCandidate(cand)"
              >
                <i class="fas fa-search me-1"></i> Locate in Roster
              </button>
            </template>

            <!-- 2. Paused membership -->
            <template v-else-if="cand.meet_status === 'paused'">
              <span class="badge bg-warning text-dark me-2">Paused</span>
              <span class="text-muted small">Cannot auto-join (Contact administrator)</span>
            </template>

            <!-- 3. Can join meet (Other meet or expired) -->
            <template v-else-if="cand.can_join !== false">
              <span class="badge bg-secondary me-2">
                {{ cand.meet_status === 'expired' ? 'Expired' : 'Other Meet' }}
              </span>
              <button
                type="button"
                class="btn btn-sm btn-primary enroll-cand-btn"
                title="Join Meet & Check In"
                @click="emitEnrollCandidate(cand)"
              >
                <i class="fas fa-user-plus me-1"></i> Join Meet & Check In
              </button>
            </template>

            <!-- 4. Cannot join -->
            <template v-else>
              <span class="badge bg-secondary">Cannot Join</span>
            </template>
          </div>
        </div>

        <!-- Bottom register prompt -->
        <div class="text-center mt-3 pt-2 border-top">
          <button
            type="button"
            class="btn btn-sm btn-outline-success switch-to-onboard-btn"
            @click="emitSwitchToOnboard(searchQuery)"
          >
            <i class="fas fa-user-plus me-1"></i> None of the above? Register "{{ searchQuery }}" as New Attendee
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { getCandidateSubtitle } from '../composables/useFastOnboardForm';

const props = withDefaults(defineProps<{
  endpoints?: any;
  searchEndpoint?: string;
  selectedMeetSlug: string;
  showPhotos?: boolean;
}>(), {
  endpoints: () => ({}),
  searchEndpoint: '',
  showPhotos: false,
});

const emit = defineEmits<{
  (e: 'switchToOnboard', query?: string): void;
  (e: 'locateCandidate', cand: any): void;
  (e: 'enrollCandidate', cand: any): void;
  (e: 'adoptCandidate', cand: any): void;
}>();

const searchQuery = ref('');
const isSearching = ref(false);
const hasSearched = ref(false);
const searchResults = ref<any[]>([]);
const searchError = ref('');
const searchInputRef = ref<HTMLInputElement | null>(null);

let debounceTimer: any = null;

/**
 * Determines whether candidate is already enrolled in target meet.
 * @param cand Candidate object.
 */
const isCandidateEnrolled = (cand: any): boolean => {
  return cand?.meet_status === 'enrolled' || Boolean(cand?.is_enrolled_in_current_meet);
};

/**
 * Handles input change with debouncing to execute search automatically while typing.
 */
const onSearchInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(executeSearch, 400);
};

/**
 * Executes search request to attendee search REST API endpoint.
 */
const executeSearch = async () => {
  const q = searchQuery.value.trim();
  if (!q) {
    hasSearched.value = false;
    searchResults.value = [];
    searchError.value = '';
    return;
  }

  hasSearched.value = true;
  isSearching.value = true;
  searchError.value = '';

  const endpointUrl = props.endpoints?.searchAttendees || props.searchEndpoint || '/persons/api/search_attendees_for_roster/';

  try {
    const res = await fetch(`${endpointUrl}?meet_slug=${encodeURIComponent(props.selectedMeetSlug)}&q=${encodeURIComponent(q)}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || errData.error || res.statusText || 'Search failed. Please try again.');
    }
    const data = await res.json();
    searchResults.value = data;
  } catch (err: any) {
    searchError.value = err.message || 'Search failed';
  } finally {
    isSearching.value = false;
  }
};

/**
 * Emits event to switch modal to onboarding step with current search query.
 * @param query Optional search query string to prefill names.
 */
const emitSwitchToOnboard = (query?: any) => {
  const finalQuery = typeof query === 'string' ? query : searchQuery.value;
  emit('switchToOnboard', finalQuery);
};

/**
 * Emits event to locate candidate in the main roster datagrid.
 * @param cand Candidate object.
 */
const emitLocateCandidate = (cand: any) => {
  emit('locateCandidate', cand);
};

/**
 * Emits event to directly enroll candidate and mark check-in.
 * @param cand Candidate object.
 */
const emitEnrollCandidate = (cand: any) => {
  emit('enrollCandidate', cand);
};

/**
 * Emits event to adopt candidate information into the onboarding form.
 * @param cand Candidate object.
 */
const emitAdoptCandidate = (cand: any) => {
  emit('adoptCandidate', cand);
};

/**
 * Focuses and selects the search input field.
 */
const focusInput = () => {
  nextTick(() => {
    searchInputRef.value?.focus();
    searchInputRef.value?.select();
  });
};

/**
 * Resets search query and results state back to initial default view.
 */
const resetSearch = () => {
  searchQuery.value = '';
  hasSearched.value = false;
  searchResults.value = [];
  searchError.value = '';
};

/**
 * Returns the current search query string.
 */
const getSearchQuery = (): string => {
  return searchQuery.value;
};

defineExpose({
  focusInput,
  resetSearch,
  getSearchQuery
});
</script>
