<template>
  <div
    class="card mb-3 border-secondary-subtle companion-block"
    :class="[`companion-block-${index + 1}`, index > 0 ? 'companion-block-extra' : '']"
  >
    <!-- Header with title, live candidate matches, and [+] / [X] buttons -->
    <div class="card-header bg-light py-2 d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center flex-wrap gap-2">
        <span class="fw-bold text-secondary companion-label">
          <i class="fas fa-user me-1"></i>
          <span class="companion-title-text">Companion {{ index + 1 }}</span>
        </span>

        <!-- Candidate matches in companion card header -->
        <div class="candidate-matches d-inline-flex align-items-center flex-wrap">
          <template v-if="!companion.attendee_id && companion.candidateMatches && companion.candidateMatches.length > 0">
            <span class="text-danger fw-normal me-1">Existing:</span>
            <div
              v-for="cand in companion.candidateMatches.slice(0, 3)"
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

          <!-- Linked candidate badge in companion card header -->
          <span
            v-if="companion.attendee_id"
            class="badge bg-success-subtle text-success border border-success d-inline-flex align-items-center gap-1 linked-candidate-badge"
            style="font-size: 0.75rem;"
            title="Linked to existing record. Will update on submit."
          >
            <i class="fas fa-check-circle"></i> Linked: {{ companion.linkedCandidate?.name || `#${companion.attendee_id}` }}
            <span v-if="companion.linkedCandidate?.latest_family_name"> (🏠 {{ companion.linkedCandidate.latest_family_name }})</span>
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
          class="btn btn-sm btn-outline-secondary py-0 px-2 add-more-companion-btn"
          title="Add another companion"
          @click="emitAddCompanion"
        >
          <i class="fas fa-plus"></i>
        </button>
        <button
          v-if="index > 0 || !isKidMeet"
          type="button"
          class="btn btn-sm btn-outline-danger py-0 px-2 remove-companion-btn"
          :class="index === 0 ? 'remove-companion-1-btn' : ''"
          title="Remove this companion"
          @click="emitRemoveCompanion(index)"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>

    <div class="card-body p-3">
      <!-- Row 1: Division, Gender, Family, Relationship -->
      <div class="row g-2 mb-2">
        <div class="col-md-3 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-division-label">
            Companion {{ index + 1 }} Division <span v-if="divisionsList && divisionsList.length > 0" class="text-danger">*</span>
          </label>
          <select v-model="companion.division_id" class="form-select form-select-sm ob-p-division">
            <option value="">Select Division</option>
            <option v-for="d in divisionsList" :key="d.id" :value="String(d.id)">
              {{ d.display_name }}
            </option>
          </select>
        </div>

        <div class="col-md-3 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-gender-label">
            Companion {{ index + 1 }} Gender
          </label>
          <select v-model="companion.gender" class="form-select form-select-sm ob-p-gender">
            <option value="UNSPECIFIED">Unspecified</option>
            <option value="MALE">Male</option>
            <option value="FEMALE">Female</option>
          </select>
        </div>

        <div class="col-md-3 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-family-label">
            <i class="fas fa-home text-secondary me-1"></i>Companion {{ index + 1 }} Family
          </label>
          <select v-model="companion.family_id" class="form-select form-select-sm ob-p-family">
            <option value="">+ New family (Default)</option>
            <option v-for="(fam, fIdx) in availableFamilies" :key="fam.id" :value="String(fam.id)">
              🏠 {{ fam.name }}{{ fIdx === 0 ? ' (Latest)' : '' }}{{ fam.members.length > 0 ? ` [${fam.members.join(', ')}]` : '' }}
            </option>
            <option v-if="availableFamilies.length > 0" value="__NEW__">+ Create a new family</option>
          </select>
        </div>

        <div class="col-md-3 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-relationship-label">
            Companion {{ index + 1 }} Relationship
          </label>
          <select v-model="companion.relationship" class="form-select form-select-sm ob-p-relationship">
            <option v-for="r in companionRelationsList" :key="r.id" :value="String(r.id)">
              {{ r.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Row 2: English Names -->
      <div class="row g-2 mb-2">
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-firstname-label">
            Companion {{ index + 1 }} First Name (English) <span class="text-danger" v-if="index === 0 && isKidMeet">*</span>
          </label>
          <input
            v-model="companion.first_name"
            type="text"
            class="form-control form-control-sm ob-p-first-name"
            placeholder="First name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-lastname-label">
            Companion {{ index + 1 }} Last Name (English) <span class="text-danger" v-if="index === 0 && isKidMeet">*</span>
          </label>
          <input
            v-model="companion.last_name"
            type="text"
            class="form-control form-control-sm ob-p-last-name"
            placeholder="Last name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
      </div>

      <!-- Row 3: Other Language Names -->
      <div class="row g-2 mb-2">
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-lastname2-label">
            Companion {{ index + 1 }} Last Name 2 (Other language) <span class="text-danger" v-if="index === 0 && isKidMeet">*</span>
          </label>
          <input
            v-model="companion.last_name2"
            type="text"
            class="form-control form-control-sm ob-p-last-name2"
            placeholder="Chinese last name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label small mb-1 fw-semibold text-secondary comp-firstname2-label">
            Companion {{ index + 1 }} First Name 2 (Other language) <span class="text-danger" v-if="index === 0 && isKidMeet">*</span>
          </label>
          <input
            v-model="companion.first_name2"
            type="text"
            class="form-control form-control-sm ob-p-first-name2"
            placeholder="Chinese first name"
            autocomplete="off"
            @input="onNameInput"
          />
        </div>
      </div>

      <!-- Row 4: Dynamic Contacts list -->
      <div class="mb-2 companion-contacts-container">
        <div class="row g-2 align-items-center mb-1">
          <div class="col-md-3 col-4">
            <label class="form-label small mb-0 fw-semibold text-secondary comp-contacttype-label">
              Companion {{ index + 1 }} Contact Type
            </label>
          </div>
          <div class="col-md-9 col-8">
            <label class="form-label small mb-0 fw-semibold text-secondary comp-contactval-label">
              Companion {{ index + 1 }} Contact Number / Account <span class="text-danger" v-if="index === 0 && isKidMeet">*</span>
            </label>
          </div>
        </div>
        <div
          v-for="(ct, ctIdx) in companion.contacts"
          :key="ctIdx"
          class="row g-2 mb-1 align-items-center contact-row contact-entry-row"
        >
          <div class="col-md-3 col-4">
            <select v-model="ct.type" class="form-select form-select-sm ob-p-contact-type">
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
              class="form-control form-control-sm ob-p-contact-value"
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
import { onMounted } from 'vue';
import { CompanionFormItem, FamilyOption } from '../types';
import {
  getCandidateSubtitle,
  getCandidateFamilyId
} from '../composables/useFastOnboardForm';

const props = defineProps<{
  companion: CompanionFormItem;
  index: number;
  companionsCount: number;
  isKidMeet: boolean;
  divisionsList: any[];
  companionRelationsList: any[];
  availableFamilies: FamilyOption[];
  hasOtherLinkedFamily?: boolean;
  linkedFamilyId?: string | null;
  linkedFamilyName?: string | null;
  searchEndpoint?: string;
  selectedMeetSlug: string;
}>();

const emit = defineEmits<{
  (e: 'removeCompanion', index: number): void;
  (e: 'addCompanion'): void;
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
    const famName = props.linkedFamilyName ? `the ${props.linkedFamilyName} family` : "other companion's family";
    return `Cannot link: Only one family can be linked per registration. Unlink ${famName} first.`;
  }
  return 'Copy & link to this record';
};

let debounceTimer: any = null;

/**
 * Searches candidates when user inputs companion names.
 */
const searchCandidates = async () => {
  if (props.companion.attendee_id) return;
  const parts = [
    props.companion.first_name || '',
    props.companion.last_name || '',
    props.companion.first_name2 || '',
    props.companion.last_name2 || ''
  ].map(s => s.trim()).filter(Boolean);

  const q = parts.join(' ').replace(/\s+/g, ' ').trim();
  if (q.length < 2) {
    props.companion.candidateMatches = [];
    return;
  }

  const endpointUrl = props.searchEndpoint || '/persons/api/search_attendees_for_roster/';
  try {
    const meetSlug = encodeURIComponent(props.selectedMeetSlug || '');
    const res = await fetch(`${endpointUrl}?meet_slug=${meetSlug}&q=${encodeURIComponent(q)}`);
    if (res.ok) {
      const data = await res.json();
      if (!props.companion.attendee_id) {
        props.companion.candidateMatches = Array.isArray(data) ? data : [];
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
  if (props.companion.attendee_id) return;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(searchCandidates, 350);
};

// Also search immediately if names are prefilled on mount
onMounted(() => {
  if (!props.companion.attendee_id) {
    const hasInitialName = Boolean(
      (props.companion.first_name && props.companion.first_name.trim().length >= 2) ||
      (props.companion.last_name && props.companion.last_name.trim().length >= 2) ||
      (props.companion.first_name2 && props.companion.first_name2.trim().length >= 2) ||
      (props.companion.last_name2 && props.companion.last_name2.trim().length >= 2)
    );
    if (hasInitialName) {
      searchCandidates();
    }
  }
});

/**
 * Emits add companion request.
 */
const emitAddCompanion = () => {
  emit('addCompanion');
};

/**
 * Emits remove companion request.
 * @param idx Companion card index.
 */
const emitRemoveCompanion = (idx: number) => {
  emit('removeCompanion', idx);
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
