import { attendeeUrl } from './golden';
import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * Keeping somebody's record: the writes a coworker makes week to week.
 *
 * The Feng household is the one reserved for writing — five months in, still
 * visitors, and nobody else asserts on them. Ruian is left to
 * `journeys.spec.ts`.
 *
 * Granting membership is one-shot: somebody can only become a member once, and
 * the button withdraws itself afterwards. CI builds the congregation fresh, so
 * a second local run wants `load_golden_data --force` first.
 *
 * What makes these worth driving through a browser rather than the API is the
 * chain behind them: recording a status writes a Past, the Past opens a
 * participation through a post-save signal, and the participation is what the
 * next report prints. The screen shows all three, so it is the only place the
 * whole chain is visible at once.
 */

type Page = import('@playwright/test').Page;

/** Turn on editing, accepting the confirm it asks first. */
async function startEditing(page: Page) {
  await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('label[for="custom-control-edit-checkbox"]').click();
  await expect(page.locator('div.attendee-form-submits').first()).not.toHaveClass(
    /dx-state-disabled/,
  );
}

test.describe('a coworker records a status', () => {
  test('the one-click button writes the past and opens the participation', async ({
    page,
    signIn,
  }) => {
    // The button is offered only for a status the person does not hold, and
    // pressing it is meant to do two things at once: write the dated Past, and
    // — through a post-save signal — enrol them in the matching meet. A screen
    // that did the first and not the second would look completely normal.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_angela'));
    await startEditing(page);

    // Membership, specifically: the Fengs are already visitors, and the
    // directory button would opt them into a printed directory that another
    // spec asserts they stay out of.
    const grantMembership = page
      .locator('div.attendee-form-submits[id^="for-past-category-"]')
      .filter({ hasText: '會員' });
    await expect(grantMembership).toHaveCount(1);

    const statuses = page.locator('#status-past-datagrid-container');
    await statuses.scrollIntoViewIfNeeded();
    await waitForGridRows(page, '#status-past-datagrid-container');
    const before = await statuses.locator('.dx-data-row').count();

    page.once('dialog', (dialog) => {
      expect(dialog.message()).toMatch(/Are you sure to add/);
      dialog.accept();
    });
    await grantMembership.click();
    await page.waitForURL(/[?&]success=/);

    // The dated status is on the record …
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');
    await statuses.scrollIntoViewIfNeeded();
    await expect
      .poll(async () => statuses.locator('.dx-data-row').count(), {
        message: 'the status was never written',
      })
      .toBe(before + 1);
    // The grid labels the category in English; the button was labelled with
    // the meet's Chinese name.
    await expect(statuses).toContainText('member');

    // … and the participation the post-save signal opened is in the
    // activities grid, which is the half a screen could silently miss.
    await waitForGridRows(page, '#attendingmeet-datagrid-container');
    await expect(page.locator('#attendingmeet-datagrid-container')).toContainText(
      /會員|member/,
    );
  });
});

test.describe('a coworker keeps the contact details up to date', () => {
  test('adds a second phone through the contacts popup', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_xinyi'));
    await startEditing(page);

    // "Add more contacts" lives in the block caption, not the form body.
    await page.locator('span.attendee-form-submits').first().click();
    const popup = page.locator('.dx-overlay-wrapper.dx-popup-wrapper:visible', {
      hasText: /Add Contact/,
    });
    await expect(popup).toBeVisible();
    await expect(popup.locator('.dx-texteditor-input').first()).toBeVisible();
  });

  test('a phone number has to look like a phone number', async ({ page, signIn }) => {
    // The pattern is strict on purpose: these numbers are what a coworker
    // rings when a child is ill, so a half-typed one should not save.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_xinyi'));
    await startEditing(page);

    const phone = page.locator('#attendee-mainform-phone1 input').first();
    await phone.fill('555-1234');
    await phone.blur();
    await expect(page.locator('.dx-validationsummary-item').first()).toContainText(
      /national&area code|\+1\(510\)/,
    );
    await expect(page.locator('#attendee-mainform-phone1')).toHaveClass(/dx-invalid/);
  });
});

test.describe('a coworker writes a note', () => {
  test('the note lands in the notes grid', async ({ page, signIn }) => {
    const written = `Rang about the retreat ${Date.now().toString().slice(-6)}`;

    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_angela'));
    await startEditing(page);

    // Turning editing on rebuilds every grid on the page, so wait for the
    // rebuilt notes grid — its add-row button only exists in editing mode —
    // rather than clicking into one that is about to be replaced. Even then a
    // click can land during the rebuild and be swallowed, so the press is
    // repeated until the popup is actually up.
    const notes = page.locator('#note-past-datagrid-container');
    await expect(notes.locator('.dx-datagrid-addrow-button')).toHaveCount(1);
    // The notes grid is not the last to be rebuilt; a popup opened while the
    // others are still loading can have its editors swapped out underneath it.
    await expect(page.locator('.dx-loadpanel-content:visible')).toHaveCount(0);
    await notes.scrollIntoViewIfNeeded();

    const editor = page.locator('.dx-datagrid-edit-popup:visible');
    for (let attempt = 0; attempt < 3; attempt += 1) {
      await notes.locator('.dx-datagrid-addrow-button').first().click();
      try {
        await expect(editor).toBeVisible({ timeout: 5_000 });
        break;
      } catch {
        if (attempt === 2) throw new Error('the notes grid never opened its editor');
      }
    }

    const field = (label: string) =>
      editor.locator('.dx-field-item', {
        has: page.locator('.dx-field-item-label-text', { hasText: label }),
      });

    // An empty note is refused and the popup stays open. Worth pinning: the
    // category is what decides who may read a note, so one saved without a
    // category is how a confidential note ends up public.
    await editor.getByRole('button', { name: /^save$/i }).first().click();
    await expect(editor).toBeVisible();

    // Category first, and the title after it. Choosing a category re-renders
    // the form, and a title typed before that is silently dropped — which
    // showed up in CI as a saved note with a blank title rather than as any
    // kind of error.
    //
    // The list is found through the input's own aria-owns: DevExtreme renders
    // that popup under a different class depending on how many choices there
    // are, and its options arrive asynchronously.
    //
    // Like the add-row button above, a click that lands while the grids are
    // still being rebuilt is swallowed, so the press is repeated until the
    // list is actually open.
    const categoryInput = field('Category').locator('.dx-texteditor-input').first();
    await expect(async () => {
      if ((await categoryInput.getAttribute('aria-expanded')) !== 'true') {
        await categoryInput.click();
      }
      await expect(categoryInput).toHaveAttribute('aria-owns', /.+/, { timeout: 2_000 });
    }, 'the category editor named no list to choose from').toPass({ timeout: 20_000 });
    const listId = await categoryInput.getAttribute('aria-owns');

    const choices = page.locator(`#${listId} .dx-list-item`);
    await expect(choices.first()).toBeVisible();
    await choices.first().click();
    await expect(categoryInput).not.toHaveValue('');

    const titleInput = field('Title').locator('.dx-texteditor-input').first();
    await titleInput.fill(written);
    // Read it back before saving, so a dropped value fails here rather than
    // three lines later as a mystery about the grid.
    await expect(titleInput).toHaveValue(written);

    await editor.getByRole('button', { name: /^save$/i }).first().click();
    await expect(editor).toBeHidden();
    await expect(notes).toContainText(written);
  });
});

test.describe('a coworker closes a record', () => {
  test('the pass-away control is guarded and warns before it acts', async ({
    page,
    signIn,
  }) => {
    // Pressing it is destructive in a way the browser suite cannot undo — it
    // finishes every participation and takes the person off the roster the
    // other specs count — so the *behaviour* is proved in
    // ``attendees/tests/e2e/test_persons_api.py`` where it rolls back. What a
    // browser has to prove is the guard: dead until editing is on, and never
    // without saying what it is about to do.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_xinyi'));
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');

    const passAway = page.locator('div.attendee-form-dead');
    await expect(passAway).toHaveClass(/dx-state-disabled/);
    await expect(passAway).toHaveAttribute(
      'title',
      /ending all activities|passed away/i,
    );

    await startEditing(page);
    await expect(passAway).not.toHaveClass(/dx-state-disabled/);

    // Open the confirm and decline it: the record must be untouched.
    page.once('dialog', (dialog) => {
      expect(dialog.message()).toMatch(/die|ending all activities/i);
      dialog.dismiss();
    });
    await passAway.click();

    const deathday = page
      .locator('div.datagrid-attendee-update input[name="deathday"]')
      .first();
    await expect(deathday).toHaveValue('');
    await waitForGridRows(page, '#attendingmeet-datagrid-container');
  });

  test('a member’s own record still shows the destructive controls, disabled', async ({
    page,
    signIn,
  }) => {
    // Worth writing down because it is not what you would guess: the page
    // renders Delete and Pass away for anybody who can open the record. What
    // stops an ordinary member is the API refusing them, proved in
    // ``attendees/tests/e2e/test_permissions.py``. The browser's contribution
    // is that neither control can be pressed by accident — both are dead until
    // editing is deliberately switched on.
    await signIn('golden_member');
    await visit(page, '/persons/attendee/self');
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');

    await expect(page.locator('div.attendee-form-delete')).toHaveClass(
      /dx-state-disabled/,
    );
    await expect(page.locator('div.attendee-form-dead')).toHaveClass(
      /dx-state-disabled/,
    );
    await expect(page.locator('div.attendee-form-submits').first()).toHaveClass(
      /dx-state-disabled/,
    );
  });
});
