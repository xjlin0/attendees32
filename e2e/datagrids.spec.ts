import { attendeeUrl } from './golden';
import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * Every roster screen in this application is an empty <div> server-side that
 * DevExtreme fills over AJAX. The pytest suite proves the endpoints answer;
 * only a browser proves the screen asks them the right question and renders
 * the answer.
 */

const ROSTER_GRID = 'div.dataAttendees';

test.describe('the attendee roster', () => {
  test('the grid fills with the congregation', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendees/');
    const rows = await waitForGridRows(page, ROSTER_GRID);
    expect(await rows.count()).toBeGreaterThan(0);

    // DevExtreme's pager reports the whole result set: the 350-person roster
    // minus 陳桂枝, who died four years ago — this grid leaves the dead out
    // unless asked for them.
    await expect(page.locator(`${ROSTER_GRID} .dx-datagrid-pager`)).toContainText(
      '349 items',
    );
  });

  test('searching a Han name narrows the grid', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendees/');
    const rows = await waitForGridRows(page, ROSTER_GRID);
    const before = await rows.count();

    await page.locator(`${ROSTER_GRID} .dx-datagrid-search-panel input`).fill('陳明恩');
    await expect
      .poll(async () => rows.count(), { message: 'the grid never narrowed' })
      .toBeLessThan(before);
    await expect(page.locator(ROSTER_GRID)).toContainText('Grace');
  });

  test('an ordinary member is not offered the add button', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, '/persons/attendees/');
    await page.waitForSelector(`${ROSTER_GRID} .dx-datagrid`);
    await expect(page.locator('a.add-attendee')).toHaveCount(0);
  });

  test('a data admin is offered the add button', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendees/');
    await expect(page.locator('a.add-attendee')).toBeVisible();
  });
});

test.describe('the attendee page', () => {
  test('the family grid shows the household', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('chen_grace'));
    const rows = await waitForGridRows(page, '#family-attendee-datagrid-container');
    // father, mother, brother, grandfather, and Grace herself
    expect(await rows.count()).toBeGreaterThanOrEqual(4);
    const grid = page.locator('#family-attendee-datagrid-container');
    await expect(grid).toContainText('Zhiming');
    await expect(grid).toContainText('Joshua');
  });

  test('the participation grid shows the meets she joined', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('chen_grace'));
    await waitForGridRows(page, '#attendingmeet-datagrid-container');
    await expect(page.locator('#attendingmeet-datagrid-container')).toContainText(
      /崇拜|Sunday Service/,
    );
  });

  test('the form is filled from the record', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('chen_grace'));
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');
    const values = await page
      .locator('div.datagrid-attendee-update input')
      .evaluateAll((nodes) =>
        nodes.map((node) => (node as HTMLInputElement).value).filter(Boolean),
      );
    expect(values.join(' ')).toContain('Grace');
  });

  test('a guardianship shows up in the relationship grid', async ({ page, signIn }) => {
    // Kevin's guardians are not his parents — the "other" folk grid.
    await signIn('golden_counselor');
    await visit(page, attendeeUrl('xu_kevin'));
    await waitForGridRows(page, '#relationship-datagrid-container');
    await expect(page.locator('#relationship-datagrid-container')).toContainText(
      /guardian/i,
    );
  });
});

test.describe('the other grids', () => {
  test('the enrollment grid boots', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendingmeets/');
    await page.waitForSelector('#attendingmeets-datagrid-container .dx-datagrid');
  });

  test('the roster grid boots', async ({ page, signIn }) => {
    await signIn('golden_children_organizer');
    await visit(page, '/occasions/roster/');
    await page.waitForSelector('#attendances-datagrid-container .dx-datagrid');
  });

  test('the statistics grid boots', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/attendance_statistics/');
    await page.waitForSelector('#attendances-datagrid-container .dx-datagrid');
  });
});
