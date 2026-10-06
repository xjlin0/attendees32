import { test as base, expect, Page } from '@playwright/test';

import { PASSWORD, Persona } from './golden';

/**
 * Third-party assets, fetched once per worker and replayed from memory.
 *
 * The pages pull DevExtreme (4 MB), jQuery plugins and Bootstrap from public
 * CDNs on every load. Caching them takes the suite from minutes to seconds, and
 * the bytes are passed through unchanged so the subresource-integrity hashes in
 * the templates still have to check out — which is itself worth knowing.
 */
interface CachedAsset {
  status: number;
  contentType: string;
  body: Buffer;
}

const assetCache = new Map<string, CachedAsset>();

/** Errors the page throws that say nothing about the application. */
const IGNORABLE_PAGE_ERRORS = [/ResizeObserver/];

/**
 * WebKit reports a request cancelled by a navigation as "… due to access
 * control checks." The journeys navigate on purpose while a grid is still
 * fetching — somebody clicking Save before the page has settled does the same
 * thing — so for the application's own host this is the browser narrating our
 * click, not a fault.
 *
 * A genuine cross-origin refusal carries the identical wording, and catching
 * those is the point of serving the CDN bytes through unchanged, so the host
 * has to match the application under test before this is forgiven.
 */
function isRequestCancelledByNavigation(message: string, baseURL?: string): boolean {
  if (!/due to access control checks/.test(message)) return false;
  const host = baseURL ? new URL(baseURL).host : '';
  return host !== '' && message.includes(host);
}

export const test = base.extend<{
  signIn: (persona: Persona) => Promise<void>;
  pageErrors: string[];
}>({
  page: async ({ page, baseURL }, use) => {
    await page.context().route(
      (url) => !url.href.startsWith(baseURL ?? ''),
      async (route) => {
        const url = route.request().url();
        let cached = assetCache.get(url);
        if (!cached) {
          try {
            const response = await route.fetch();
            cached = {
              status: response.status(),
              contentType: response.headers()['content-type'] ?? 'application/octet-stream',
              body: await response.body(),
            };
            assetCache.set(url, cached);
          } catch {
            await route.abort();
            return;
          }
        }
        await route.fulfill({
          status: cached.status,
          body: cached.body,
          headers: {
            'content-type': cached.contentType,
            // The script tags are crossorigin="anonymous", so a fulfilled
            // response still has to satisfy the CORS rules.
            'access-control-allow-origin': '*',
            'cache-control': 'public, max-age=86400',
          },
        });
      },
    );
    await use(page);
  },

  pageErrors: async ({ page, baseURL }, use) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await use(errors);
    const fatal = errors.filter(
      (message) =>
        !IGNORABLE_PAGE_ERRORS.some((pattern) => pattern.test(message)) &&
        !isRequestCancelledByNavigation(message, baseURL),
    );
    expect(fatal, 'the page threw JavaScript errors').toEqual([]);
  },

  signIn: async ({ page, pageErrors }, use) => {
    void pageErrors; // collect errors from the first navigation onwards
    await use(async (persona: Persona) => {
      // Signing in as somebody else mid-test has to start from no session:
      // allauth redirects an already-authenticated visitor away from the
      // login page, and there would be no form to fill in.
      await page.context().clearCookies();
      await page.goto('/accounts/login/', { waitUntil: 'domcontentloaded' });
      await page.fill("input[name='login']", persona);
      await page.fill("input[name='password']", PASSWORD);
      await Promise.all([
        page.waitForURL((url) => !url.pathname.startsWith('/accounts/login')),
        page.click("button[type='submit'], input[type='submit']"),
      ]);
    });
  },
});

export { expect };

/** Navigate without waiting on every last third-party subresource. */
export async function visit(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
}

/** Wait for a DevExtreme grid inside `container` to have rendered rows. */
export async function waitForGridRows(page: Page, container: string) {
  await page.waitForSelector(`${container} .dx-datagrid`);
  await page.waitForSelector(`${container} .dx-data-row`);
  return page.locator(`${container} .dx-data-row`);
}
