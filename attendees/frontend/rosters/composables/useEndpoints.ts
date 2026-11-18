import { reactive } from 'vue';
import { Endpoints } from '../types';

export function useEndpoints() {
  const endpoints = reactive<Endpoints>({
    attendances: '',
    assemblies: '',
    categories: '',
    scheduledCategory: '1',
    meets: '',
    meetsBySlug: '',
    rosters: '',
    attendingmeets: '',
    attendings: '',
    characters: '',
    teams: '',
    divisions: '',
    gatherings: '',
    searchAttendees: '',
    fastOnboard: '',
    relations: '',
    userCanWrite: true,
  });

  const initEndpoints = (el?: HTMLElement | null) => {
    const appEl = el || document.getElementById('app');
    if (appEl) {
      endpoints.attendances = appEl.dataset.attendancesEndpoint || '';
      endpoints.assemblies = appEl.dataset.assembliesEndpoint || '';
      endpoints.categories = appEl.dataset.categoriesEndpoint || '';
      endpoints.scheduledCategory = appEl.dataset.scheduledCategory || '1';
      endpoints.meets = appEl.dataset.meetsEndpointBySlug || '';
      endpoints.meetsBySlug = appEl.dataset.meetsEndpointBySlug || '';
      endpoints.rosters = appEl.dataset.rostersEndpoint || '';
      endpoints.attendingmeets = appEl.dataset.attendingmeetsEndpoint || '';
      endpoints.attendings = appEl.dataset.attendingsEndpoint || '';
      endpoints.characters = appEl.dataset.charactersEndpoint || '';
      endpoints.teams = appEl.dataset.teamsEndpoint || '';
      endpoints.divisions = appEl.dataset.divisionsEndpoint || '/whereabouts/api/user_divisions/';
      endpoints.gatherings = appEl.dataset.gatheringsEndpoint || '/occasions/api/organization_team_gatherings/';
      endpoints.searchAttendees = appEl.dataset.searchAttendeesEndpoint || '/persons/api/search_attendees_for_roster/';
      endpoints.fastOnboard = appEl.dataset.fastOnboardEndpoint || '/persons/api/fast_onboard_attendee/';
      endpoints.relations = appEl.dataset.relationsEndpoint || '/persons/api/all_relations/';
      endpoints.userCanWrite = appEl.dataset.userCanWrite !== 'false';
    }
  };

  return { endpoints, initEndpoints };
}
