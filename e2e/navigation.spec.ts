import { attendeeId, attendeeUrl, PASSWORD } from './golden';
import { expect, test, visit } from './fixtures';

test.describe('signing in', () => {
  test('a member signs in through the real form', async ({ page, signIn }) => {
    await signIn('golden_member');
    expect(page.url()).not.toContain('/accounts/login');
    await expect(page.locator('nav')).toContainText('Sign Out');
  });

  // Only one spec in this file fails a login on purpose: ACCOUNT_RATE_LIMITS
  // allows three per IP per ten minutes, and allauth answers a rate-limited
  // attempt with the same message as a wrong password.
  test('a wrong password is refused', async ({ page }) => {
    await visit(page, '/accounts/login/');
    await page.fill("input[name='login']", 'golden_member');
    await page.fill("input[name='password']", `${PASSWORD}-wrong`);
    await page.click("button[type='submit'], input[type='submit']");
    await page.waitForSelector(".alert-danger, .errorlist, [role='alert']");
    expect(page.url()).toContain('/accounts/login');
  });

  test('signing out ends the session', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, '/accounts/logout/');
    // Wait for the POST's own navigation: checking a load state can resolve
    // against the page we are still standing on, and the next request would
    // then go out with the session still alive.
    await Promise.all([
      page.waitForURL((url) => !url.pathname.startsWith('/accounts/logout')),
      page.click("button[type='submit'], input[type='submit']"),
    ]);
    await visit(page, '/persons/attendees/');
    expect(page.url()).toContain('/accounts/login');
  });

  test('an anonymous visitor is sent to the login page', async ({ page }) => {
    await visit(page, '/persons/attendees/');
    expect(page.url()).toContain('/accounts/login');
  });
});

test.describe('navigation', () => {
  test('the menu is built from the reader’s auth groups', async ({ page, signIn }) => {
    // users.Menu drives the navbar, and only the top-level entries are visible
    // until a dropdown is opened — so compare those.
    await signIn('golden_member');
    const memberMenu = await page.locator('nav').innerText();
    expect(memberMenu).toContain('My Info');
    expect(memberMenu, 'a member is not a coworker').not.toContain('同工資料');

    await signIn('golden_data_organizer');
    const organizerMenu = await page.locator('nav').innerText();
    expect(organizerMenu).toContain('同工資料');
    expect(organizerMenu.length).toBeGreaterThan(memberMenu.length);
  });

  test('the home page renders for anyone', async ({ page }) => {
    await visit(page, '/');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('the guards, as a user meets them', () => {
  test('a member is told when a page is not theirs', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, '/occasions/attendance_statistics/');
    await expect(page.locator('body')).toContainText(
      'does not have permissions to visit such route',
    );
  });

  test('a member cannot open a stranger', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, attendeeUrl('lee_peter'));
    await expect(page.locator('body')).toContainText(/not allowed to access this page/i);
  });

  test('a parent can open the child they schedule', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, attendeeUrl('chen_joshua'));
    await page.waitForSelector('div.datagrid-attendee-update');
    await expect(page.locator('body')).not.toContainText(/not allowed/i);
  });
});

test.describe('the printed pages', () => {
  test('the directory preview renders a household without the dead', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_counselor');
    await visit(page, `/persons/directory_preview/${attendeeId('chen_zhiming')}`);
    const body = page.locator('body');
    await expect(body).toContainText('Zhiming');
    // 陳桂枝 died four years ago; her household still prints, without her.
    await expect(body).not.toContainText('Guizhi');
  });

  test('the directory is paginated by Paged.js', async ({ page, signIn }) => {
    // Paged.js has to actually run, or the directory prints as one slab. The
    // polyfill used to be loaded from a URL that answers with HTML, so the
    // browser parsed a web page as JavaScript, threw a SyntaxError and left the
    // document unpaginated — invisible to any test that only reads the
    // server's response.
    await signIn('golden_data_organizer');
    await visit(
      page,
      '/persons/directory_report/?divisionSelector=1&divisionSelector=2' +
        '&divisionSelector=3&directoryHeader=CFCCH',
    );
    // Paged.js lays the document out one page at a time, so the first page
    // appearing is the start of the work rather than the end of it.
    await page.waitForSelector('.pagedjs_pages .pagedjs_page');
    await expect
      .poll(async () => page.locator('.pagedjs_page').count(), {
        message: '350 people do not fit on one printed page',
        timeout: 60_000,
      })
      .toBeGreaterThanOrEqual(2);
    await expect(page.locator('.pagedjs_pages')).toContainText('CFCCH');
  });

  test('the participation report is paginated too', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(
      page,
      '/persons/attendingmeet_report/?meet=d7c8Fd_cfcch_congregation_directory' +
        '&divisions=cfcch_chinese_ministry&reportTitle=CFCCH',
    );
    await page.waitForSelector('.pagedjs_pages .pagedjs_page');
    await expect(page.locator('.pagedjs_pages')).toContainText('CFCCH');
  });

  test('the calendar page boots', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, '/occasions/calendars/');
    await expect(page.locator('body')).toBeVisible();
  });
});

