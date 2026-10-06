import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * Taking attendance: the Sunday-morning screen.
 *
 * This is the one place in the application with a drawing surface, and the one
 * a volunteer uses under time pressure with a queue of parents in front of
 * them. Nothing else in the suite touches it, and no HTTP test can: the
 * signature only exists because somebody moved a pointer across a canvas.
 *
 * These journeys write, and they put back what they changed — the roster is
 * eight weeks of committed history that other assertions count.
 */

const GRID = 'div#attendances-datagrid-container';

/** Just enough of the page's own namespace to ask the pad whether it is empty. */
interface AttendeesWindow {
  Attendees: { roster: { signaturePad: { isEmpty(): boolean } } };
}

/** Fill one of the filter form's date boxes. */
async function setFilterDate(
  page: import('@playwright/test').Page,
  which: 'from' | 'till',
  value: string,
) {
  // The dxDateBox keeps two inputs; the second is the one a person types in.
  const input = page.locator(`div.filter-${which} input`).nth(1);
  await input.fill(value);
  await input.press('Enter');
}

/**
 * Choose a value in one of the filter form's dropdowns.
 *
 * Every dropdown keeps its list in the document once opened, so the items have
 * to be read out of the overlay that is actually on screen — otherwise the
 * gatherings list resolves against the meets list still sitting behind it.
 */
async function chooseFilter(
  page: import('@playwright/test').Page,
  cssClass: string,
  option: RegExp | string,
) {
  await page.locator(`div.${cssClass} .dx-texteditor-input`).first().click();
  const open = page.locator('.dx-overlay-wrapper:visible');
  await open.locator('.dx-list-item', { hasText: option }).first().click();
  await expect(page.locator(`div.${cssClass} .dx-texteditor-input`).first()).not.toHaveValue(
    '',
  );
}

/**
 * Write on the signature pad, and check the pad agrees that something was
 * written. A stroke that lands while the refusal toast is still fading is a
 * stroke on the toast, so this retries rather than pressing Sign in hope.
 */
async function sign(page: import('@playwright/test').Page) {
  const canvas = page.locator('canvas.signature');
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const box = await canvas.boundingBox();
    if (!box) throw new Error('the signature canvas has no box to draw in');
    await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.6);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.3, { steps: 8 });
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.7, { steps: 8 });
    await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.4, { steps: 8 });
    await page.mouse.up();
    const written = await page.evaluate(
      () => !(window as never as AttendeesWindow).Attendees.roster.signaturePad.isEmpty(),
    );
    if (written) return;
  }
  throw new Error('the pad recorded no stroke after three attempts');
}

/** Answer a DevExtreme confirm — a DOM dialog, not the browser's. */
async function answerDialog(page: import('@playwright/test').Page, answer: 'Yes' | 'No') {
  const dialog = page.locator('.dx-dialog-wrapper');
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: answer, exact: true }).click();
  await expect(dialog).toBeHidden();
}

/**
 * Toggle a check-in, and do not return until the page says it stored it.
 *
 * Two things make this harder than a click. The screen sets the cell and then
 * saves on a 500 ms debounce, and the save reloads the grid — so a press that
 * lands during that reload is dropped by DevExtreme with no error and no
 * request at all, which is what a slower machine produces. And the page's own
 * "update attendance success" toast is the only signal that tells a stored
 * change apart from a checkbox that merely looks ticked.
 *
 * So: press, wait for the toast, and press again if it does not come. The
 * state is re-read each time, so a repeat only ever pushes it the way it was
 * already going.
 */
async function toggleCheckIn(
  page: import('@playwright/test').Page,
  attendanceId: string,
  wanted: boolean,
) {
  const box = page.locator(`input#in-${attendanceId}`);
  const stored = page.locator('.dx-toast-success', { hasText: /attendance success/i });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    if ((await box.isChecked()) === wanted) return;

    // Let any toast from an earlier press clear, so the next one is this
    // press's own answer rather than the last one's.
    await expect(stored).toHaveCount(0, { timeout: 15_000 });

    await page.locator(`label[for="in-${attendanceId}"]`).click();
    if (!wanted) {
      // Unchecking asks before it throws the arrival time away.
      await answerDialog(page, 'Yes');
    }

    try {
      await expect(stored).toBeVisible({ timeout: 10_000 });
      await expect(box).toBeChecked({ checked: wanted, timeout: 10_000 });
      return;
    } catch {
      if (attempt === 2) {
        throw new Error(
          `the register never stored the check-in change for ${attendanceId}`,
        );
      }
    }
  }
}

/** The Sunday the golden congregation last met, as the gatherings are named. */
function lastSunday(): string {
  const day = new Date();
  day.setDate(day.getDate() - ((day.getDay() + 7) % 7));
  return [
    day.getFullYear(),
    `${day.getMonth() + 1}`.padStart(2, '0'),
    `${day.getDate()}`.padStart(2, '0'),
  ].join('-');
}

/**
 * Open the roster on a gathering that actually happened.
 *
 * The page defaults to "yesterday until next week", which straddles the most
 * recent Sunday only if the clock happens to cooperate — so reach back a
 * fortnight and take the first gathering offered.
 */
async function openLastSundaysRoster(page: import('@playwright/test').Page) {
  await visit(page, '/occasions/roster/');
  await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

  const fortnightAgo = new Date(Date.now() - 14 * 24 * 3600 * 1000);
  const month = `${fortnightAgo.getMonth() + 1}`.padStart(2, '0');
  const day = `${fortnightAgo.getDate()}`.padStart(2, '0');
  await setFilterDate(page, 'from', `${month}/${day}/${fortnightAgo.getFullYear()}, 12:00 AM`);

  // Exactly this meet: "Chinese" alone also matches the choir, and "Worship"
  // matches The Crossing's worship team.
  await chooseFilter(page, 'selected-meets', '中文崇拜');
  await chooseFilter(page, 'selected-gatherings', /\d{4}-\d{2}-\d{2}/);
  return waitForGridRows(page, GRID);
}

test.describe('a coworker takes the register', () => {
  test('checks somebody in, and can undo it', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    const rows = await openLastSundaysRoster(page);
    await expect(rows.first()).toBeVisible();

    // Take somebody's row, then hold on to *them* rather than to "the first
    // row": saving reloads the grid, and the row that comes back first need
    // not be the one that was clicked. Every id here is the attendance's own,
    // so it survives the reload.
    const rowId = await page
      .locator(`${GRID} input.roll-call-button[value="checkIn"]`)
      .first()
      .getAttribute('id');
    const attendanceId = (rowId ?? '').replace(/^in-/, '');
    const checkIn = page.locator(`input#in-${attendanceId}`);
    const wasChecked = await checkIn.isChecked();

    await toggleCheckIn(page, attendanceId, !wasChecked);
    await expect(checkIn).toBeChecked({ checked: !wasChecked });

    // Put the register back the way the eight weeks of history expect it.
    await toggleCheckIn(page, attendanceId, wasChecked);
    await expect(checkIn).toBeChecked({ checked: wasChecked });
  });

  test('checks a child out, and will not do it without a signature', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_children_organizer');
    await visit(page, '/occasions/roster/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

    const fortnightAgo = new Date(Date.now() - 14 * 24 * 3600 * 1000);
    const month = `${fortnightAgo.getMonth() + 1}`.padStart(2, '0');
    const day = `${fortnightAgo.getDate()}`.padStart(2, '0');
    await setFilterDate(
      page,
      'from',
      `${month}/${day}/${fortnightAgo.getFullYear()}, 12:00 AM`,
    );
    await chooseFilter(page, 'selected-meets', 'The Rock');
    // The most recent Sunday, which is the one still part-finished.
    await chooseFilter(page, 'selected-gatherings', lastSunday());
    await waitForGridRows(page, GRID);

    // A child who arrived and whom nobody has signed for yet: check-in ticked,
    // check-out offered and clear. That is the row this screen exists for.
    const waiting = page
      .locator(
        `${GRID} input.roll-call-button[value="checkOut"]:not(.d-none):not(:checked)`,
      )
      .first();
    await expect(waiting).toHaveCount(1);
    const attendanceId = ((await waiting.getAttribute('id')) ?? '').replace(/^out-/, '');

    await page.locator(`label[for="out-${attendanceId}"]`).click();

    // The popup's contents live in an overlay of their own, not in the anchor
    // div the page declares, and its title is rewritten to name the child —
    // which is the check that matters when a queue of parents is waiting.
    // Scoped to the popup wrapper: the refusal toast is an overlay too, and
    // it says "Checking out requires signature!".
    const signing = page.locator('.dx-overlay-wrapper.dx-popup-wrapper:visible', {
      hasText: /Checking out /,
    });
    await expect(signing).toBeVisible();
    await expect(page.locator('canvas.signature')).toBeVisible();

    // Sign it: a signature is a pointer dragged across the canvas, and the pad
    // is asked whether it agrees that something was written.
    await sign(page);
    await signing.getByText('Sign', { exact: true }).click();
    await expect(signing).toBeHidden();

    // The time-out is recorded, and the signature is stored against it.
    const checkOut = page.locator(`input#out-${attendanceId}`);
    await expect.poll(async () => checkOut.isChecked()).toBe(true);

    // Undo it — the confirm shows the signature back to the person undoing it,
    // and the file is kept for audit even though the time is cleared.
    await page.locator(`label[for="out-${attendanceId}"]`).click();
    await answerDialog(page, 'Yes');
    await expect.poll(async () => checkOut.isChecked()).toBe(false);

    // Then the other half, on a clean pad: an unsigned child is exactly what
    // this screen exists to prevent, so Sign has to refuse and the popup has
    // to stay open. It goes last because the refusal is a toast centred over
    // the canvas, and a stroke drawn while it fades lands on the toast.
    await page.locator(`label[for="out-${attendanceId}"]`).click();
    await expect(signing).toBeVisible();
    await signing.getByText('Sign', { exact: true }).click();
    // The error toast specifically: the saves earlier in this journey each
    // left a success toast of their own on screen.
    await expect(page.locator('.dx-toast-error')).toContainText(/signature/i);
    await expect(signing).toBeVisible();

    // Cancel puts the tick back where it was, so the child is still recorded
    // as here and nobody has been written down as having collected them.
    await signing.getByText('Cancel', { exact: true }).click();
    await expect(signing).toBeHidden();
    await expect.poll(async () => checkOut.isChecked()).toBe(false);

    // Which hands the row back the way it was found: arrived, not yet
    // collected, waiting for whoever comes for them.
  });

  test('cannot add a walk-in before choosing a gathering', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, '/occasions/roster/');
    await page.waitForSelector('form.filters-dxform .dx-texteditor-input');

    page.once('dialog', (dialog) => {
      expect(dialog.message()).toMatch(/select a gathering/i);
      dialog.accept();
    });
    await page.locator('div.dx-toolbar .dx-icon-add').first().click();
  });
});

test.describe('the register itself', () => {
  test('remembers how it was arranged, and can be reset', async ({ page, signIn }) => {
    // Somebody who arranges this screen their way on Sunday morning expects
    // to find it that way after a reload — and expects one button to undo it.
    await signIn('golden_data_organizer');
    await openLastSundaysRoster(page);

    const search = page.locator(`${GRID} .dx-datagrid-search-panel input`);
    await search.fill('Chen');
    await expect
      .poll(async () => page.locator(`${GRID} .dx-data-row`).count())
      .toBeGreaterThan(0);

    // Saving is debounced, so wait for it to actually land rather than
    // reloading into a race.
    await expect
      .poll(
        async () =>
          page.evaluate(() => window.sessionStorage.getItem('rollCallList') ?? ''),
        { message: 'the grid never stored how it was arranged' },
      )
      .toContain('Chen');

    // The arrangement survives a reload, because the page keeps it per
    // browser. (The date and gathering choices deliberately do not — the
    // restore for those is commented out in the page — so the grid comes back
    // arranged but empty, which is exactly what a reload looks like here.)
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector(`${GRID} .dx-datagrid-search-panel input`);
    await expect(search).toHaveValue('Chen');

    // And one button puts it back to how it ships.
    page.once('dialog', (dialog) => dialog.accept());
    await page.locator('div.dx-toolbar .dx-icon-clearsquare').first().click();
    await expect.poll(async () => search.inputValue()).toBe('');
  });
});
