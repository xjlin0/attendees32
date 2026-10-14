import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * Putting the church's week in the diary, and reading it back.
 *
 * Gatherings are the rows every register, report and statistic hangs off, and
 * the page that makes them has a button that writes many at once. One click
 * there is worth a term's worth of typing — and worth proving, because a batch
 * that silently makes none, or makes them in the wrong month, looks identical
 * until somebody tries to take a register.
 */

const GRID = 'div#gatherings-datagrid-container';

/** Fill one of the filter form's date boxes. */
async function setFilterDate(
  page: import('@playwright/test').Page,
  which: 'from' | 'till',
  value: string,
) {
  const input = page.locator(`div.filter-${which} input`).nth(1);
  await input.fill(value);
  await input.press('Enter');
}

/** mm/dd/yyyy, as the date boxes want it. */
function usDate(offsetDays: number): string {
  const day = new Date();
  day.setDate(day.getDate() + offsetDays);
  return [
    `${day.getMonth() + 1}`.padStart(2, '0'),
    `${day.getDate()}`.padStart(2, '0'),
    day.getFullYear(),
  ].join('/');
}

test.describe('a coworker fills in the diary', () => {
  test('the page lists what is already scheduled', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/gatherings/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

    // Reach back over the eight committed weeks.
    await setFilterDate(page, 'from', `${usDate(-60)}, 12:00 AM`);
    await page.locator('div.selected-meets .dx-texteditor-input').first().click();
    await page
      .locator('.dx-overlay-wrapper:visible')
      .locator('.dx-list-item', { hasText: '中文崇拜' })
      .first()
      .click();
    await page.keyboard.press('Escape');

    const rows = await waitForGridRows(page, GRID);
    expect(await rows.count()).toBeGreaterThan(0);
    await expect(page.locator(GRID)).toContainText('中文崇拜');
  });

  test('editing is off until it is deliberately switched on', async ({
    page,
    signIn,
  }) => {
    // Everything on this page writes to the schedule the whole church reads,
    // so nothing is editable until somebody says so.
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/gatherings/');
    const editing = page.locator('div#custom-control-edit-switch');
    await expect(editing).toBeVisible();
    await expect(editing).toContainText('Editing disabled');

    await editing.click();
    await expect(editing).toContainText('Editing enabled');
  });

  test('the batch button will not fire without a single meet and a window', async ({
    page,
    signIn,
  }) => {
    // It writes a term of Sundays in one press, so it stays dead until the
    // question is unambiguous: exactly one meet, and both ends of the window.
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/gatherings/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

    const generate = page.locator('div#generate-gatherings');
    await expect(generate).toBeVisible();
    await expect(generate).toHaveClass(/dx-state-disabled/);
  });
});

test.describe('anybody reads the diary', () => {
  test('the calendar shows the organization’s occurrences', async ({ page, signIn }) => {
    await signIn('golden_member');
    // The listener has to be armed before the navigation: the calendar asks
    // for its window while it boots, which is over before a `waitFor` set up
    // afterwards would ever see it.
    const asked = page.waitForRequest(
      (request) =>
        request.url().includes('organization_occurrences') ||
        request.url().includes('organization_calendars'),
      { timeout: 25_000 },
    );
    await visit(page, '/occasions/calendars/');
    await expect(page.locator('body')).toBeVisible();
    expect((await asked).url()).toContain('/occasions/api/');
  });

  test('the location timeline renders the rooms in use', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/location_timeline/');
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('.dx-widget').first()).toBeVisible();
  });
});
