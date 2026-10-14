import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * What the office prints and what it counts.
 *
 * The directory is driven in `journeys.spec.ts`. This is the other half: the
 * participation list a coworker takes to a meeting, the envelopes that go in
 * the post, and the statistics somebody reads before deciding whether a group
 * is still running. All three are the end of a long chain — enrolment, then
 * attendance, then a printed page — and none of them is provable server-side,
 * because the page a person holds is laid out by Paged.js in the browser.
 */

/** Choose a value in one of a configuration form's dropdowns. */
async function pick(
  page: import('@playwright/test').Page,
  fieldLabel: string,
  option: RegExp | string,
) {
  const field = page.locator('.dx-field-item', {
    has: page.locator('.dx-field-item-label-text', { hasText: fieldLabel }),
  });
  await field.locator('.dx-texteditor-input').first().click();
  await page
    .locator('.dx-overlay-wrapper:visible')
    .locator('.dx-list-item', { hasText: option })
    .first()
    .click();
  await page.keyboard.press('Escape');
}

/** Tick every division: the report is required to be told which to include. */
async function selectAllDivisions(page: import('@playwright/test').Page) {
  await page.locator('button[aria-label*="check-double"], .fa-check-double').first().click();
}

test.describe('the office prints a participation list', () => {
  test('configures it, then gets a paginated document', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendingmeet_print_configuration/');
    await page.waitForSelector('form#attendingmeet-print-configuration .dx-texteditor-input');

    await pick(page, 'Select an activity(meet)', '中文崇拜');
    await selectAllDivisions(page);

    const title = page.locator('.dx-field-item', {
      has: page.locator('.dx-field-item-label-text', { hasText: 'Text 1 in bigger font' }),
    });
    await title.locator('.dx-texteditor-input').first().fill('中文崇拜 participation');

    page.once('dialog', (dialog) => dialog.accept());
    await page.getByText('Generate report for print', { exact: true }).click();
    await page.waitForURL(/attendingmeet_report/);

    // Paged.js lays it out one page at a time; the first page appearing is the
    // start of the work, not the end.
    await page.waitForSelector('.pagedjs_pages .pagedjs_page');
    await expect
      .poll(async () => page.locator('.pagedjs_page').count(), { timeout: 60_000 })
      .toBeGreaterThanOrEqual(1);
    await expect(page.locator('.pagedjs_pages')).toContainText('中文崇拜 participation');

    // The list is grouped by household, so a family name has to appear.
    await expect(page.locator('.pagedjs_pages')).toContainText(/家|family|Chen|陳/);
  });

  test('generates envelopes for the same meet', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendingmeet_print_configuration/');
    await page.waitForSelector('form#attendingmeet-print-configuration .dx-texteditor-input');

    await pick(page, 'Select an activity(meet)', '中文崇拜');
    await selectAllDivisions(page);

    page.once('dialog', (dialog) => dialog.accept());
    await page.getByText('Generate envelopes for print', { exact: true }).click();
    await page.waitForURL(/attendingmeet_envelopes/);

    await page.waitForSelector('.pagedjs_pages .pagedjs_page');
    // One envelope per household, not per person — which is the whole point of
    // printing them from the family rather than the roster.
    const pages = await page.locator('.pagedjs_page').count();
    expect(pages).toBeGreaterThanOrEqual(1);
    await expect(page.locator('.pagedjs_pages')).toContainText(/CA|California|\d{5}/);
  });

  test('a reader without the route is refused the printed page', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_member');
    await visit(page, '/persons/attendingmeet_report/');
    await expect(page.locator('body')).toContainText(
      /does not have permissions to visit such route|not allowed to access this page/i,
    );
  });
});

test.describe('somebody reads the numbers', () => {
  test('the statistics grid counts attendance for the meets chosen', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/attendance_statistics/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

    // Reach back over the eight committed weeks, then ask for one meet.
    const from = page.locator('div.filter-from input').nth(1);
    const reach = new Date();
    reach.setDate(reach.getDate() - 60);
    await from.fill(
      `${`${reach.getMonth() + 1}`.padStart(2, '0')}/${`${reach.getDate()}`.padStart(
        2,
        '0',
      )}/${reach.getFullYear()}, 12:00 AM`,
    );
    await from.press('Enter');

    await page.locator('div.selected-meets .dx-texteditor-input').first().click();
    await page
      .locator('.dx-overlay-wrapper:visible')
      .locator('.dx-list-item', { hasText: '中文崇拜' })
      .first()
      .click();
    await page.keyboard.press('Escape');

    const rows = await waitForGridRows(page, 'div#attendances-datagrid-container');
    expect(await rows.count()).toBeGreaterThan(0);
    // Every row is a person and a count of how often they came.
    await expect(page.locator('div#attendances-datagrid-container')).toContainText(
      'Attendance Count',
    );
  });

  test('an ordinary member is not given the statistics page', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_member');
    await visit(page, '/occasions/attendance_statistics/');
    await expect(page.locator('body')).toContainText(
      /does not have permissions to visit such route|not allowed to access this page/i,
    );
  });
});

test.describe('somebody takes the data away with them', () => {
  test('the roster exports to a spreadsheet the browser actually receives', async ({
    page,
    signIn,
  }) => {
    // Export is how a coworker gets a list into the hands of somebody who does
    // not have a login — a seating plan, a phone tree, a printout for a
    // meeting. It is generated in the browser from the rows already fetched,
    // so nothing server-side can tell you whether a file comes out at all.
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, 'div.dataAttendees');

    const download = page.waitForEvent('download', { timeout: 30_000 });
    // The toolbar button is labelled by its hint; with
    // allowExportSelectedData on it opens a menu rather than exporting at once.
    await page
      .locator('div.dataAttendees')
      .getByRole('button', { name: 'export-to' })
      .first()
      .click();
    const exportAll = page.locator('.dx-menu-item, .dx-item', {
      hasText: /Export all data/i,
    });
    if (await exportAll.count()) await exportAll.first().click();

    const file = await download;
    expect(file.suggestedFilename()).toMatch(/\.xlsx$/);
  });
});
