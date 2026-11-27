<template>
  <div
    class="card mb-3 border-primary-subtle shadow-sm attendee-block"
    :class="`attendee-block-${index + 1}`"
  >
    <!-- Header with title, live candidate matches, and [+] / [X] buttons -->
    <div class="card-header bg-light py-2 d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center flex-wrap gap-2">
        <span class="fw-bold text-primary attendee-label">
          <i class="fas fa-user me-1"></i>
          {{ attendeesCount > 1 ? `Attendee ${index + 1} Information` : 'Attendee Information' }}
        </span>

        <!-- Candidate matches in card header (matches rosters_list_view.js) -->
        <div class="candidate-matches d-inline-flex align-items-center flex-wrap">
          <template v-if="!attendee.attendee_id && attendee.candidateMatches && attendee.candidateMatches.length > 0">
            <span class="text-danger fw-normal me-1">Existing:</span>
            <div
              v-for="cand in attendee.candidateMatches.slice(0, 3)"
              :key="cand.id"
              class="btn-group btn-group-sm rounded-pill border border-danger-subtle shadow-sm me-2 overflow-hidden candidate-pill-group"
              style="font-size: 0.75rem; vertical-align: middle;"
              :title="isLinkDisabled(cand) ? getLinkBtnTitle(cand) : getCandidateSubtitle(cand)"
              @dblclick.prevent="!isLinkDisabled(cand) && emitAdoptCandidate(cand)"
            >
              <a
                :href="`/persons/attendee/${cand.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="btn btn-outline-danger btn-xs py-0 px-2 d-inline-flex align-items-center border-0 bg-white text-danger fw-semibold"
                style="font-size: 0.75rem; text-decoration: none;"
                :title="getCandidateSubtitle(cand)"
                @click.stop
              >
                {{ cand.name }} <i class="fas fa-external-link-alt ms-1 text-danger-emphasis" style="font-size: 0.6rem; opacity: 0.75;"></i>
              </a>
              <button
                type="button"
                class="btn btn-xs py-0 px-2 d-inline-flex align-items-center text-white border-0 link-candidate-btn"
                :class="isLinkDisabled(cand) ? 'btn-secondary' : 'btn-danger'"
                :disabled="isLinkDisabled(cand)"
                :style="{ fontSize: '0.72rem', cursor: isLinkDisabled(cand) ? 'not-allowed' : 'pointer' }"
                :title="getLinkBtnTitle(cand)"
                @click.prevent.stop="!isLinkDisabled(cand) && emitAdoptCandidate(cand)"
              >
                <i class="fas fa-link me-1"></i>Link
              </button>
            </div>
          </template>

          <!-- Linked candidate badge in card header -->
          <span
            v-if="attendee.attendee_id"
            class="badge bg-success-subtle text-success border border-success d-inline-flex align-items-center gap-1 linked-candidate-badge"
            style="font-size: 0.75rem;"
            title="Linked to existing record. Will update on submit."
          >
            <i class="fas fa-check-circle"></i> Linked: {{ attendee.linkedCandidate?.name || `#${attendee.attendee_id}` }}
            <span v-if="attendee.linkedCandidate?.latest_family_name"> (🏠 {{ attendee.linkedCandidate.latest_family_name }})</span>
            <button
              type="button"
              class="btn-close btn-close-sm unlink-candidate-btn unlink-cand-btn"
              style="font-size: 0.55rem; filter: invert(0.3);"
              title="Not this one, Unlink candidate"
              @click.prevent.stop="emitUnlinkCandidate"
            ></button>
          </span>
        </div>
      </div>
      <div class="d-flex gap-1 align-items-center">
        <button
          type="button"
          class="btn btn-sm btn-outline-primary py-0 px-2 add-more-attendee-btn"
          title="Add another attendee"
          @click="emitAddAttendee"
        >
          <i class="fas fa-plus"></i>
        </button>
        <button
          v-if="index > 0"
          type="button"
          class="btn btn-sm btn-outline-danger py-0 px-2 remove-attendee-btn"
          title="Remove this attendee"
          @click="emitRemoveAttendee(index)"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>

    <div class="card-body p-3">
      <!-- Row 1: Division, Family, Relationship -->
      <div class="row g-2 mb-2">
        <div class="col-md-4 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-division-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} Division` : 'Division' }} <span v-if="divisionsList && divisionsList.length > 0" class="text-danger">*</span>
          </label>
          <select v-model="attendee.division_id" class="form-select form-select-sm ob-division">
            <option value="">Select Division</option>
            <option v-for="d in divisionsList" :key="d.id" :value="String(d.id)">
              {{ d.display_name }}
            </option>
          </select>
        </div>

        <div class="col-md-4 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-family-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} Family` : 'Family' }} (Set companion for existing families)
          </label>
          <select v-model="attendee.family_id" class="form-select form-select-sm ob-family">
            <option value="">+ New family (Default)</option>
            <option v-for="(fam, fIdx) in availableFamilies" :key="fam.id" :value="String(fam.id)">
              🏠 {{ fam.name }}{{ fIdx === 0 ? ' (Latest)' : '' }}{{ fam.members.length > 0 ? ` [${fam.members.join(', ')}]` : '' }}
            </option>
            <option v-if="availableFamilies.length > 0" value="__NEW__">+ Create a new family</option>
          </select>
        </div>

        <div class="col-md-4 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-relationship-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} Relationship` : 'Relationship' }}
          </label>
          <select v-model="attendee.relationship" class="form-select form-select-sm ob-relationship">
            <option v-for="r in attendeeRelationsList" :key="r.id" :value="String(r.id)">
              {{ r.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Row 2: English Names -->
      <div class="row g-2 mb-2">
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-firstname-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} First Name (English)` : 'First Name (English)' }} <span class="text-danger">*</span>
          </label>
          <input
            v-model="attendee.first_name"
            type="text"
            class="form-control form-control-sm ob-first-name"
            placeholder="First name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-lastname-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} Last Name (English)` : 'Last Name (English)' }} <span class="text-danger">*</span>
          </label>
          <input
            v-model="attendee.last_name"
            type="text"
            class="form-control form-control-sm ob-last-name"
            placeholder="Last name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
      </div>

      <!-- Row 3: Other Language Names -->
      <div class="row g-2 mb-2">
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-lastname2-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} Last Name 2 (Other language)` : 'Last Name 2 (Other language)' }} <span class="text-danger">*</span>
          </label>
          <input
            v-model="attendee.last_name2"
            type="text"
            class="form-control form-control-sm ob-last-name2"
            placeholder="Chinese last name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-firstname2-label">
            {{ attendeesCount > 1 ? `Attendee ${index + 1} First Name 2 (Other language)` : 'First Name 2 (Other language)' }} <span class="text-danger">*</span>
          </label>
          <input
            v-model="attendee.first_name2"
            type="text"
            class="form-control form-control-sm ob-first-name2"
            placeholder="Chinese first name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
      </div>

      <!-- Row 4: Gender & Birthday -->
      <div class="row g-2 mb-2">
        <div class="col-md-3 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary att-gender-label">Gender</label>
          <select v-model="attendee.gender" class="form-select form-select-sm ob-gender">
            <option value="UNSPECIFIED">Unspecified</option>
            <option value="MALE">Male</option>
            <option value="FEMALE">Female</option>
          </select>
        </div>

        <div class="col-md-3 col-4">
          <label class="form-label small mb-1 fw-semibold text-secondary att-byear-label">
            Birth Year <span :class="isKidMeet ? 'text-danger' : 'text-muted'" class="ob-birthday-badge">{{ isKidMeet ? '* (Required)' : '(Optional)' }}</span>
          </label>
          <input
            v-model="attendee.byear"
            type="number"
            class="form-control form-control-sm ob-byear"
            placeholder="YYYY"
            min="1900"
            max="2099"
            @change="onBirthdayChange"
          />
        </div>
        <div class="col-md-3 col-4">
          <label class="form-label small mb-1 fw-semibold text-secondary att-bmonth-label">
            Birth Month <span v-if="isKidMeet" class="text-danger">*</span>
          </label>
          <select v-model="attendee.bmonth" class="form-select form-select-sm ob-bmonth" @change="onBirthdayChange">
            <option value="">Month</option>
            <option v-for="m in 12" :key="m" :value="String(m)">{{ m }}</option>
          </select>
        </div>
        <div class="col-md-3 col-4">
          <label class="form-label small mb-1 fw-semibold text-secondary att-bday-label">
            Birth Day <span v-if="isKidMeet" class="text-danger">*</span>
          </label>
          <select v-model="attendee.bday" class="form-select form-select-sm ob-bday">
            <option value="">Day</option>
            <option v-for="d in maxDaysInMonth" :key="d" :value="String(d)">{{ d }}</option>
          </select>
        </div>
      </div>

      <!-- Kid-specific fields: Grade, Food preference, Insurer -->
      <div v-if="isKidMeet" class="row g-2 mb-2 p-2 bg-light rounded border kid-specific-fields">
        <div class="col-md-4 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary">School Grade: <span class="text-danger">*</span></label>
          <select v-model="attendee.grade" class="form-select form-select-sm ob-grade">
            <option value="">Select Grade</option>
            <option v-for="(g, gIdx) in gradesList" :key="gIdx" :value="String(g.id !== undefined ? g.id : gIdx)">
              {{ g.label || g }}
            </option>
          </select>
        </div>

        <div :class="showInsurer ? 'col-md-4 col-12' : 'col-md-8 col-12'">
          <label class="form-label small mb-1 fw-semibold text-secondary">Food Allergies / Preference: <span class="text-danger">*</span></label>
          <input
            v-model="attendee.food_pref"
            type="text"
            class="form-control form-control-sm ob-food-pref"
            placeholder="None, Vegetarian, Nut allergy..."
          />
        </div>

        <div v-if="showInsurer" class="col-md-4 col-12 insurer-field-group">
          <label class="form-label small mb-1 fw-semibold text-secondary">Medical Insurer:</label>
          <input
            v-model="attendee.insurer"
            type="text"
            class="form-control form-control-sm ob-insurer"
            placeholder="Kaiser, BlueCross..."
          />
        </div>
      </div>

      <!-- Row 5: Dynamic Contacts list -->
      <div class="mb-2 attendee-contacts-container">
        <label class="form-label small mb-1 fw-semibold text-secondary">
          Contact Type {{ !isKidMeet ? '(At least one contact required)' : '' }}:
        </label>
        <div
          v-for="(ct, ctIdx) in attendee.contacts"
          :key="ctIdx"
          class="row g-2 mb-1 align-items-center contact-row contact-entry-row"
        >
          <div class="col-md-3 col-4">
            <select v-model="ct.type" class="form-select form-select-sm ob-contact-type">
              <option value="phone">Phone</option>
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="wechat">WeChat</option>
              <option value="line">Line</option>
            </select>
          </div>
          <div class="col-md-7 col-6">
            <input
              v-model="ct.value"
              type="text"
              class="form-control form-control-sm ob-contact-value"
              placeholder="Phone number, email, or account"
              autocomplete="off"
            />
          </div>
          <div class="col-md-2 col-2 d-flex gap-1">
            <button
              type="button"
              class="btn btn-sm btn-outline-success py-0 px-2 add-contact-btn"
              title="Add another contact"
              @click="emitAddContact(ctIdx)"
            >
              <i class="fas fa-plus"></i>
            </button>
            <button
              v-if="ctIdx > 0"
              type="button"
              class="btn btn-sm btn-outline-danger py-0 px-2 remove-contact-btn"
              title="Remove contact"
              @click="emitRemoveContact(ctIdx)"
            >
              <i class="fas fa-minus"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { AttendeeFormItem, FamilyOption } from '../types';
import {
  getMaxDaysInMonth,
  getCandidateSubtitle,
  getCandidateFamilyId
} from '../composables/useFastOnboardForm';

const props = defineProps<{
  attendee: AttendeeFormItem;
  index: number;
  attendeesCount: number;
  isKidMeet: boolean;
  showInsurer: boolean;
  divisionsList: any[];
  attendeeRelationsList: any[];
  availableFamilies: FamilyOption[];
  hasOtherLinkedFamily?: boolean;
  linkedFamilyId?: string | null;
  linkedFamilyName?: string | null;
  gradesList: any[];
  searchEndpoint?: string;
  selectedMeetSlug: string;
}>();

const emit = defineEmits<{
  (e: 'removeAttendee', index: number): void;
  (e: 'addAttendee'): void;
  (e: 'addContact', contactIndex: number): void;
  (e: 'removeContact', contactIndex: number): void;
  (e: 'adoptCandidate', cand: any): void;
  (e: 'unlinkCandidate'): void;
}>();

/**
 * Checks whether linking a candidate is disabled due to another family already being linked.
 * The modal allows only one family to be linked at a time.
 * When another companion or attendee already linked a family, candidate linking is disabled.
 * @param cand Matched candidate record.
 */
const isLinkDisabled = (cand?: any): boolean => {
  if (props.hasOtherLinkedFamily) {
    return true;
  }
  if (!props.linkedFamilyId) {
    return false;
  }
  const candFamId = cand ? getCandidateFamilyId(cand) : null;
  return !candFamId || String(candFamId) !== String(props.linkedFamilyId);
};

/**
 * Returns tooltip title for candidate's Link button.
 * Explains reason if disabled.
 * @param cand Matched candidate record.
 */
const getLinkBtnTitle = (cand?: any): string => {
  if (isLinkDisabled(cand)) {
    const famName = props.linkedFamilyName ? `the ${props.linkedFamilyName} family` : "other family";
    return `Cannot link: Only one family can be linked per registration. Unlink ${famName} first.`;
  }
  return 'Copy & link to this record';
};

/**
 * Computes maximum valid days in selected year and month.
 */
const maxDaysInMonth = computed(() => {
  return getMaxDaysInMonth(props.attendee.byear, props.attendee.bmonth);
});

/**
 * Validates selected day when year or month changes.
 */
const onBirthdayChange = () => {
  const maxDays = maxDaysInMonth.value;
  if (props.attendee.bday && parseInt(props.attendee.bday, 10) > maxDays) {
    props.attendee.bday = String(maxDays);
  }
};

let debounceTimer: any = null;

/**
 * Searches candidates when user inputs names.
 */
const searchCandidates = async () => {
  if (props.attendee.attendee_id) return;
  const parts = [
    props.attendee.first_name || '',
    props.attendee.last_name || '',
    props.attendee.first_name2 || '',
    props.attendee.last_name2 || ''
  ].map(s => s.trim()).filter(Boolean);

  const q = parts.join(' ').replace(/\s+/g, ' ').trim();
  if (q.length < 2) {
    props.attendee.candidateMatches = [];
    return;
  }

  const endpointUrl = props.searchEndpoint || '/persons/api/search_attendees_for_roster/';
  try {
    const meetSlug = encodeURIComponent(props.selectedMeetSlug || '');
    const res = await fetch(`${endpointUrl}?meet_slug=${meetSlug}&q=${encodeURIComponent(q)}`);
    if (res.ok) {
      const data = await res.json();
      if (!props.attendee.attendee_id) {
        props.attendee.candidateMatches = Array.isArray(data) ? data : [];
      }
    }
  } catch {
    // Ignore background candidate search errors
  }
};

/**
 * Debounces search input handler.
 */
const onNameInput = () => {
  if (props.attendee.attendee_id) return;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(searchCandidates, 350);
};

// Also search immediately if names are prefilled on mount
onMounted(() => {
  if (!props.attendee.attendee_id) {
    const hasInitialName = Boolean(
      (props.attendee.first_name && props.attendee.first_name.trim().length >= 2) ||
      (props.attendee.last_name && props.attendee.last_name.trim().length >= 2) ||
      (props.attendee.first_name2 && props.attendee.first_name2.trim().length >= 2) ||
      (props.attendee.last_name2 && props.attendee.last_name2.trim().length >= 2)
    );
    if (hasInitialName) {
      searchCandidates();
    }
  }
});

/**
 * Emits add attendee request.
 */
const emitAddAttendee = () => {
  emit('addAttendee');
};

/**
 * Emits remove attendee request.
 * @param idx Attendee card index.
 */
const emitRemoveAttendee = (idx: number) => {
  emit('removeAttendee', idx);
};

/**
 * Emits add contact row request.
 * @param ctIdx Current contact index.
 */
const emitAddContact = (ctIdx: number) => {
  emit('addContact', ctIdx);
};

/**
 * Emits remove contact row request.
 * @param ctIdx Target contact index.
 */
const emitRemoveContact = (ctIdx: number) => {
  emit('removeContact', ctIdx);
};

/**
 * Emits candidate adoption.
 * @param cand Selected candidate.
 */
const emitAdoptCandidate = (cand: any) => {
  emit('adoptCandidate', cand);
};

/**
 * Emits unlink candidate.
 */
const emitUnlinkCandidate = () => {
  emit('unlinkCandidate');
};
</script>
