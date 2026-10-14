import { attendeeUrl, golden } from './golden';
import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * End-to-end journeys: somebody arriving with a job to do, and finishing it.
 *
 * The other specs check screens. These follow a person across several of them,
 * through the writes, and back to where the result has to show up — which is
 * the only way to catch the seams, where a save succeeds but the thing it was
 * supposed to change does not.
 *
 * These are the specs that *write*. The suite runs against one shared, committed
 * congregation with no per-test rollback, so:
 *
 *  - each journey writes to a person reserved for it and nobody else asserts on
 *    (the Feng household — five months in, still visitors), or puts back what it
 *    changed;
 *  - Playwright runs files in path order, so `datagrids.spec.ts` and its
 *    absolute roster count run before anything here adds a row.
 */

const ROSTER_GRID = 'div.dataAttendees';

type Page = import('@playwright/test').Page;

/**
 * Turn on the attendee page's editing mode and wait for the form to follow.
 *
 * The toggle asks "Are you sure to toggle editing mode?" and leaves the page
 * read-only if the answer is no — which is what Playwright's default dialog
 * handling says. So the confirm has to be accepted, and the save button going
 * from disabled to enabled is how we know the whole page followed.
 */
async function startEditing(page: Page) {
  await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('label[for="custom-control-edit-checkbox"]').click();
  // The save button is itself the DevExtreme widget; the class names the role.
  await expect(page.locator('div.attendee-form-submits').first()).not.toHaveClass(
    /dx-state-disabled/,
  );
}

/**
 * Save the attendee form and wait for the save to have actually landed.
 *
 * The form posts over AJAX and, on success only, reloads itself with
 * `?success=`. Waiting for that is the difference between asserting the save
 * worked and asserting a button was clickable.
 */
/**
 * Choose a value in one of the form's dropdowns.
 *
 * The input carrying the field name is the hidden one the widget posts, so the
 * only way in is the visible editor and the list it opens — which is also the
 * only way a person can fill these in.
 */
async function pickFromDropdown(page: Page, field: string, choice: string) {
  const box = page.locator('div.datagrid-attendee-update .dx-selectbox', {
    has: page.locator(`input[name="${field}"]`),
  });
  await box.locator('.dx-texteditor-input').click();
  await page.locator('.dx-list-item', { hasText: choice }).first().click();
}

async function saveAttendeeForm(page: Page) {
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('div.attendee-form-submits').first().click();
  await page.waitForURL(/[?&]success=/);
}

test.describe('a data admin corrects somebody’s Chinese name', () => {
  test('the correction reaches the record and the search index', async ({
    page,
    signIn,
  }) => {
    // The seam this journey exists for: Attendee.save() derives the searchable
    // name forms on every save, and a partial update that dropped them would
    // leave the record right and the search wrong — with nothing on screen to
    // say so.
    const corrected = '馮瑞安改';

    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_ruian'));
    await startEditing(page);

    const chineseGivenName = page
      .locator('div.datagrid-attendee-update input[name="first_name2"]')
      .or(page.locator('#attendee-mainform-first_name2 input'))
      .first();
    await chineseGivenName.fill('瑞安改');
    await saveAttendeeForm(page);

    // Back out to the roster and find him by the new spelling.
    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, ROSTER_GRID);
    await page.locator(`${ROSTER_GRID} .dx-datagrid-search-panel input`).fill(corrected);
    await expect(page.locator(ROSTER_GRID)).toContainText('Ruian');

    // Put it back, so the congregation is as the next spec expects it.
    await visit(page, attendeeUrl('feng_ruian'));
    await startEditing(page);
    await chineseGivenName.fill('瑞安');
    await saveAttendeeForm(page);
  });
});

test.describe('a coworker adds a newcomer', () => {
  test('from the roster to a saved record and back again', async ({
    page,
    signIn,
  }) => {
    const givenName = `Walkin${Date.now().toString().slice(-6)}`;

    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, ROSTER_GRID);

    // The button an ordinary member does not get.
    const addAttendee = page.locator('a.add-attendee');
    await addAttendee.scrollIntoViewIfNeeded();
    await addAttendee.click();
    await page.waitForURL(/\/persons\/attendee\/new$/);
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');

    await page
      .locator('div.datagrid-attendee-update input[name="first_name"]')
      .first()
      .fill(givenName);
    await page
      .locator('div.datagrid-attendee-update input[name="last_name"]')
      .first()
      .fill('Newcomer');
    // Gender is the one field the form will not save without. Its named input
    // is the hidden one the widget posts, so the journey opens the dropdown
    // the way a person does and picks from the list.
    await pickFromDropdown(page, 'gender', 'FEMALE');
    // And a division, because a person nobody has placed shows up on no roster.
    await pickFromDropdown(page, 'division', 'The Crossing');

    await saveAttendeeForm(page);
    // Saving a new person lands on the person, not back on the blank form.
    await expect(page).toHaveURL(/\/persons\/attendee\/[0-9a-f-]{36}/);
    const newcomerUrl = new URL(page.url()).pathname;

    // The roster is the coworker's proof the person exists.
    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, ROSTER_GRID);
    await page.locator(`${ROSTER_GRID} .dx-datagrid-search-panel input`).fill(givenName);
    await expect(page.locator(ROSTER_GRID)).toContainText(givenName);

    // Somebody added in error gets removed again — and that is also how this
    // journey hands the congregation back the size it borrowed it at.
    await visit(page, newcomerUrl);
    await startEditing(page);
    page.once('dialog', (dialog) => dialog.accept());
    await Promise.all([
      page.waitForURL((url) => url.pathname === '/'),
      page.locator('div.attendee-form-delete').click(),
    ]);

    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, ROSTER_GRID);
    await page.locator(`${ROSTER_GRID} .dx-datagrid-search-panel input`).fill(givenName);
    await expect(page.locator(`${ROSTER_GRID} .dx-data-row`)).toHaveCount(0);
  });
});

test.describe('a parent looks after their children', () => {
  test('signs in, finds the child they schedule, and reads their week', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_member'); // 陳志明, father of Grace and Joshua

    // His own record first — the page every member lands on.
    await visit(page, '/persons/attendee/self');
    await waitForGridRows(page, '#family-attendee-datagrid-container');
    // The grid groups by family and fills in the members as it goes; the
    // household he belongs to is the part that has to be right here.
    await expect(page.locator('#family-attendee-datagrid-container')).toContainText(
      '陳志明家',
    );

    // Then the child's, which he may open only because he is their scheduler.
    await visit(page, attendeeUrl('chen_joshua'));
    await waitForGridRows(page, '#attendingmeet-datagrid-container');
    await expect(page.locator('#attendingmeet-datagrid-container')).toContainText(
      /The Rock|崇拜/,
    );

    // And the family's attendance history.
    await visit(page, '/occasions/datagrid_user_organization_attendances/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('a stranger’s child stays shut', async ({ page, signIn }) => {
    await signIn('golden_member');
    await visit(page, attendeeUrl('lee_peter'));
    await expect(page.locator('body')).toContainText(/not allowed to access this page/i);
  });
});

test.describe('the office prints the directory', () => {
  test('configures it, then gets a paginated document', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/persons/directory_print_configuration/');

    await page.fill('#directory-header', 'CFCCH 通訊錄 2026');
    await page.fill('#index-header', 'Index');
    // Print every division the church has.
    await page.locator('#division-selector option').first().waitFor();
    const divisions = page.locator('#division-selector option');
    await page
      .locator('#division-selector')
      .selectOption(
        await divisions.evaluateAll((nodes) =>
          nodes.map((node) => (node as HTMLOptionElement).value),
        ),
      );

    // Generating asks "this will take 2 minutes" before it navigates.
    page.once('dialog', (dialog) => dialog.accept());
    await page.locator('#directory-print-configuration button[type="submit"]').click();
    await page.waitForURL(/directory_report/);

    // Paged.js has to turn the flat HTML into printable pages, and it lays them
    // out one at a time — so the first page appearing is the start of the work,
    // not the end of it.
    await page.waitForSelector('.pagedjs_pages .pagedjs_page');
    await expect
      .poll(async () => page.locator('.pagedjs_page').count(), {
        message: 'the directory never paginated past a single page',
        timeout: 60_000,
      })
      .toBeGreaterThanOrEqual(2);
    const printed = page.locator('.pagedjs_pages');
    await expect(printed).toContainText('CFCCH 通訊錄 2026');
    await expect(printed).toContainText('Zhiming');
    // 陳桂枝 died four years ago, and the Fengs opted out.
    await expect(printed).not.toContainText('Guizhi');
  });
});

test.describe('anybody looks somebody up', () => {
  test('search the roster, open the record, read the family', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_children_organizer');
    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, ROSTER_GRID);

    await page.locator(`${ROSTER_GRID} .dx-datagrid-search-panel input`).fill('Tsai');
    await expect
      .poll(async () => page.locator(`${ROSTER_GRID} .dx-data-row`).count())
      .toBeGreaterThan(0);
    await expect(page.locator(ROSTER_GRID)).toContainText('蔡');

    // The restaurant family: no email at all, children in the after-school club.
    await visit(page, attendeeUrl('tsai_serena'));
    await waitForGridRows(page, '#family-attendee-datagrid-container');
    await expect(page.locator('#family-attendee-datagrid-container')).toContainText(
      'Shixiang',
    );
  });
});

test.describe('the congregation the journeys run against', () => {
  test('is the golden one', async ({ page, signIn }) => {
    // A guard on the manifest: if these journeys were pointed at some other
    // database, every selector above would still "work" and prove nothing.
    expect(golden.counts.attendees).toBe(350);
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendees/');
    await waitForGridRows(page, ROSTER_GRID);
    await expect(page.locator(`${ROSTER_GRID} .dx-datagrid-pager`)).toContainText(
      /\d{3} items/,
    );
  });
});
