export interface Endpoints {
  attendances: string;
  assemblies: string;
  categories: string;
  scheduledCategory: string;
  meets: string;
  meetsBySlug: string;
  rosters: string;
  attendingmeets: string;
  attendings: string;
  characters: string;
  teams: string;
  divisions: string;
  gatherings: string;
  searchAttendees: string;
  fastOnboard: string;
  relations: string;
  userCanWrite: boolean;
}

export interface Gathering {
  id: number | string | null;
  meet_id?: number | string;
  meet_display_name?: string;
  start?: string;
  finish?: string;
  attendances_count?: number;
  enrolled_count?: number | null;
}

export interface AttendanceRecord {
  id?: number | string;
  attending?: number | string;
  gathering?: number | string;
  category?: number | string;
  team?: number | string | null;
  character?: number | string | null;
  start?: string | null;
  finish?: string | null;
  file?: string | null;
  file_path?: string | null;
  meet_id?: number | string;
  meet_slug?: string;
  attending_meet_id?: number | string;
  is_attending?: boolean;
}

export interface AttendingMeet {
  id: number;
  attending: number;
  meet: number;
  character: number;
  category?: number;
  team?: number | null;
  start?: string;
  finish?: string;
  desc?: string;
  meet_slug?: string;
  meet_display_name?: string;
}

export interface AttendeeRow {
  id: number; // attending_id or attendee_id
  attendee_id: number;
  attending_id: number;
  name: string;
  first_name?: string;
  last_name?: string;
  first_name2?: string;
  last_name2?: string;
  gender?: string;
  actual_birthday?: string;
  grade?: number | null;
  team?: number | null;
  character?: number | null;
  contacts?: Record<string, any>;
  parent_contacts?: Record<string, any>;
  attendingmeets?: AttendingMeet[];
  attendances?: Record<string, AttendanceRecord>;
  attendances_count?: number;
  [key: string]: any;
}

export interface MeetInfo {
  id: number;
  slug: string;
  display_name: string;
  assembly: number;
  major_character?: number;
  infos?: {
    signature_required_at?: 'check-in' | 'check-out' | null;
    show_attendee_infos?: Record<string, boolean>;
    [key: string]: any;
  };
  show_attendee_infos?: Record<string, boolean>;
}

export interface FilterState {
  assemblies?: number[];
  meets: string[];
  startDate: Date | null;
  endDate: Date | null;
  showPhotos?: boolean;
  showPhoto?: boolean;
  showSiblings?: boolean;
  filterRules?: any[];
}

export interface ContactItem {
  type: string;
  value: string;
}

export interface AttendeeFormItem {
  id: string;
  attendee_id: string | number | null;
  linkedCandidate: any | null;
  division_id: string;
  family_id: string;
  relationship: string;
  first_name: string;
  last_name: string;
  first_name2: string;
  last_name2: string;
  gender: string;
  byear: string;
  bmonth: string;
  bday: string;
  contacts: ContactItem[];
  grade: string;
  food_pref: string;
  insurer: string;
  candidateMatches: any[];
  debounceTimer?: any;
}

export interface CompanionFormItem {
  id: string;
  attendee_id: string | number | null;
  linkedCandidate: any | null;
  division_id: string;
  family_id: string;
  relationship: string;
  first_name: string;
  last_name: string;
  first_name2: string;
  last_name2: string;
  gender: string;
  contacts: ContactItem[];
  candidateMatches: any[];
  debounceTimer?: any;
  removedInAdultMeet?: boolean;
}

export interface FamilyOption {
  id: string | number;
  name: string;
  created?: string;
  members: string[];
  is_latest?: boolean;
}
