import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * The golden congregation, as seen from outside Python.
 *
 * `manage.py load_golden_data --manifest` writes this file, so the keys here
 * and the rows in the database are produced by the same run and cannot drift.
 */
export interface GoldenManifest {
  counts: Record<string, number>;
  password: string;
  personas: Record<string, { groups: string[]; attendee: string | null }>;
  attendees: Record<string, string>;
  folks: Record<string, string>;
}

const MANIFEST_PATH = resolve(
  __dirname,
  process.env.ATTENDEES_GOLDEN_MANIFEST ?? 'golden-manifest.json',
);

function loadManifest(): GoldenManifest {
  if (!existsSync(MANIFEST_PATH)) {
    throw new Error(
      `No golden manifest at ${MANIFEST_PATH}.\n` +
        'Build the congregation first:\n' +
        '  docker compose -f local.yml run --rm django python manage.py \\\n' +
        '    load_golden_data --seed --force --manifest e2e/golden-manifest.json',
    );
  }
  return JSON.parse(readFileSync(MANIFEST_PATH, 'utf-8')) as GoldenManifest;
}

export const golden = loadManifest();

/** The UUID of a golden attendee, by the key the roster gives them. */
export function attendeeId(key: keyof GoldenManifest['attendees'] | string): string {
  const id = golden.attendees[key];
  if (!id) {
    throw new Error(`No golden attendee called "${key}"`);
  }
  return id;
}

/** The URL of an attendee's page. */
export function attendeeUrl(key: string): string {
  return `/persons/attendee/${attendeeId(key)}`;
}

/** Every persona shares one password; it is in the manifest, not hard-coded. */
export const PASSWORD = golden.password;

export type Persona =
  | 'golden_superuser'
  | 'golden_data_organizer'
  | 'golden_counselor'
  | 'golden_children_organizer'
  | 'golden_children_coworker'
  | 'golden_conference_organizer'
  | 'golden_member'
  | 'golden_crossing_member'
  | 'golden_youth'
  | 'golden_unaffiliated'
  | 'golden_outsider';
