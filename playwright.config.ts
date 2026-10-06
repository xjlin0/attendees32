import { defineConfig, devices } from '@playwright/test';

/**
 * The browser end-to-end suites.
 *
 * Two suites live in ./e2e, each written against its own data set, and each is
 * a separate project here so that neither runs against the other's data.
 *
 * The golden suite (projects `chromium` and `webkit`) drives a running
 * attendees32 against the golden congregation — 350 people, their families,
 * statuses and eight weeks of attendance. Bring both up first:
 *
 *   docker compose -f local.yml up -d
 *   docker compose -f local.yml run --rm django python manage.py migrate
 *   docker compose -f local.yml run --rm django python manage.py load_golden_data \
 *     --seed --force --manifest e2e/golden-manifest.json
 *   npm run test:e2e:chromium
 *
 * The manifest is how these specs know which UUID belongs to Grace Chen; it is
 * written by the same command that loads the data, so the two cannot drift.
 *
 * The ci-seed suite (project `ci-seed`) comes from upstream and expects
 * `fixtures/ci_seed.json` loaded instead, signing in as `jack` with the
 * password in C_PASSWORD (see .github/workflows/e2e.yml):
 *
 *   docker compose -f local.yml run --rm django python manage.py loaddata fixtures/ci_seed.json
 *   C_PASSWORD=... npm run test:e2e:ci-seed
 */
const CI_SEED_SPECS = [
  'attendeeUpdate.spec.ts',
  'attendeesList.spec.ts',
  'attendingMeetEnvelopes.spec.ts',
  'attendingMeetReport.spec.ts',
  'directoryReport.spec.ts',
  'errorPages.spec.ts',
  'neighbors.spec.ts',
].map((spec) => `**/${spec}`);

export default defineConfig({
  testDir: './e2e',
  // The golden congregation is shared, committed state on one server: running
  // specs in parallel would have them reading each other's navigation.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 25_000 },
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never' }], ['github']]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    // ATTENDEES_BASE_URL is the golden suite's name for it, BASE_URL the
    // ci-seed suite's; either points both at the server under test.
    baseURL:
      process.env.ATTENDEES_BASE_URL ?? process.env.BASE_URL ?? 'http://localhost:8008',
    viewport: { width: 1440, height: 1000 },
    navigationTimeout: 45_000,
    actionTimeout: 25_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    testIdAttribute: 'data-testid',
  },
  projects: [
    { name: 'chromium', testIgnore: CI_SEED_SPECS, use: { ...devices['Desktop Chrome'] } },
    // WebKit is not a formality: it is the engine that finds the date-input,
    // flexbox and Intl differences Chromium forgives.
    { name: 'webkit', testIgnore: CI_SEED_SPECS, use: { ...devices['Desktop Safari'] } },
    { name: 'ci-seed', testMatch: CI_SEED_SPECS, use: { ...devices['Desktop Chrome'] } },
  ],
});
