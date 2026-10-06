import { attendeeUrl } from './golden';
import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * Who does what, and until when.
 *
 * A participation is the row that puts somebody on a register, in a printed
 * list and into a statistic, so ending one is how a person quietly disappears
 * from all three. The endpoints are covered in
 * `attendees/tests/e2e/test_persons_api.py`; what a browser adds is that the
 * grid a coworker actually uses is wired to them, edits in place, and reads the
 * result back.
 *
 * The Feng household is the one reserved for writing.
 */

type Page = import('@playwright/test').Page;

const GRID = '#attendingmeet-datagrid-container';

/**
 * Tick every meet and every character.
 *
 * Both filters are tag boxes, and each carries a "select all" button — which is
 * what a coworker reaches for when they want the whole picture rather than one
 * group.
 */
async function selectEverything(page: Page) {
  // Each box fills from an endpoint of its own, so a press can land before the
  // choices have arrived and quietly select nothing. The tags are the proof it
  // took, and the press is repeated until they appear.
  const tags = page.locator('div.selected-meets .dx-tag');

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const selectAll = page.locator('.fa-check-double');
    const count = await selectAll.count();
    for (let index = 0; index < count; index += 1) {
      await selectAll.nth(index).click();
    }
    try {
      await expect(tags.first()).toBeVisible({ timeout: 8_000 });
      return;
    } catch {
      if (attempt === 2) throw new Error('the filters never took a selection');
    }
  }
}

/** Turn on editing, accepting the confirm it asks first. */
async function startEditing(page: Page) {
  await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('label[for="custom-control-edit-checkbox"]').click();
  await expect(page.locator('div.attendee-form-submits').first()).not.toHaveClass(
    /dx-state-disabled/,
  );
}

test.describe('a coworker reads what somebody is enrolled in', () => {
  test('the grid lists the meets with their role and dates', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('chen_zhiming'));
    await waitForGridRows(page, GRID);

    const grid = page.locator(GRID);
    // A participation is a meet, a role in it, and a window of time.
    await expect(grid).toContainText(/崇拜|Service/);
    await expect(grid).toContainText('Character');
    await expect(grid).toContainText('Start');
  });

  test('a paused participation is shown as paused, not as gone', async ({
    page,
    signIn,
  }) => {
    // The pastor's child is away at college. Paused matters because a person
    // who is merely away should not have to be re-enrolled when they return.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('zhang_esther'));
    await waitForGridRows(page, GRID);
    await expect(page.locator(GRID)).toContainText(/paused/i);
  });

  test('the grid is read-only until editing is switched on', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_ruian'));
    await waitForGridRows(page, GRID);

    // No add button before, one after: this grid writes to the rows that put
    // people on registers, so it does not edit by accident.
    await expect(page.locator(`${GRID} .dx-datagrid-addrow-button`)).toHaveCount(0);
    await startEditing(page);
    await expect(page.locator(`${GRID} .dx-datagrid-addrow-button`)).toHaveCount(1);
  });
});

test.describe('a coworker ends a participation', () => {
  test('setting a finish date is offered instead of deleting the row', async ({
    page,
    signIn,
  }) => {
    // The confirmation says it out loud, and it is the difference between a
    // person's history being kept and being thrown away.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_ruian'));
    await waitForGridRows(page, GRID);
    await startEditing(page);

    // Turning editing on rebuilds the grid, so wait for the rebuilt version —
    // the add-row button only exists in editing mode — before touching a row.
    // Even then a press can land mid-rebuild and be swallowed, so repeat it
    // until the confirm is actually up.
    await expect(page.locator(`${GRID} .dx-datagrid-addrow-button`)).toHaveCount(1);

    const confirm = page.locator('.dx-dialog-wrapper');
    for (let attempt = 0; attempt < 3; attempt += 1) {
      await page.locator(`${GRID} .dx-data-row .dx-link-delete`).first().click();
      try {
        await expect(confirm).toBeVisible({ timeout: 5_000 });
        break;
      } catch {
        if (attempt === 2) throw new Error('the grid never asked before deleting');
      }
    }
    await expect(confirm).toContainText(
      /set the .finish date. to expire it instead/i,
    );

    // Decline: the row stays, because ending is what was wanted, not deleting.
    const before = await page.locator(`${GRID} .dx-data-row`).count();
    await confirm.getByRole('button', { name: 'No', exact: true }).click();
    await expect(page.locator(`${GRID} .dx-data-row`)).toHaveCount(before);
  });
});

test.describe('the enrolment list across the church', () => {
  test('a coworker can see who is in what, and narrow it', async ({ page, signIn }) => {
    // Every meet and character at once is 1 900 participations: this one is
    // genuinely slow, not stuck, and the default budget is not enough for it
    // on a loaded machine.
    test.slow();
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendingmeets/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

    // Like the roster, this list asks what you want to see before it shows
    // anything — 1 900 participations is not a useful first screen. Both
    // filters are tag boxes with a "select all" button, which is what a
    // coworker reaches for when they want the whole picture.
    await selectEverything(page);

    // Every meet at once is 1 900 participations; give the grid room to answer.
    const LIST = '#attendingmeets-datagrid-container';
    await page.waitForSelector(`${LIST} .dx-data-row`, { timeout: 60_000 });
    const rows = page.locator(`${LIST} .dx-data-row`);

    const before = await rows.count();
    await page.locator(`${LIST} .dx-datagrid-search-panel input`).fill('陳');
    await expect
      .poll(async () => page.locator(`${LIST} .dx-data-row`).count(), {
        message: 'the enrolment list never narrowed',
      })
      .toBeLessThanOrEqual(before);
    await expect(page.locator(LIST)).toContainText('陳');
  });

  test('the whole church can be asked for at once', async ({ page, signIn }) => {
    // Selecting every meet is the query behind "who is enrolled in anything",
    // and it is the one that has to page rather than fall over.
    test.slow();
    await signIn('golden_data_organizer');
    await visit(page, '/persons/attendingmeets/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');
    await selectEverything(page);

    await page.waitForSelector('#attendingmeets-datagrid-container .dx-data-row', {
      timeout: 60_000,
    });
    await expect(
      page.locator('#attendingmeets-datagrid-container .dx-datagrid-pager'),
    ).toContainText(/items/);
  });

  test('an ordinary member may read it but is told they cannot edit', async ({
    page,
    signIn,
  }) => {
    // This list is open to the whole congregation on purpose — it is how
    // somebody checks which group they are in. What they do not get is the
    // editing switch, and the page says so rather than leaving a dead toggle.
    await signIn('golden_member');
    await visit(page, '/persons/attendingmeets/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');
    await expect(page.locator('#user-cannot-write')).toContainText('Editing forbidden');
    await expect(page.locator('#custom-control-edit-switch')).toHaveCount(0);
  });
});
