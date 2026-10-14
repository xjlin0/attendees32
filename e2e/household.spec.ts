import { attendeeUrl } from './golden';
import { expect, test, visit, waitForGridRows } from './fixtures';

/**
 * Households: who belongs with whom, who may act for whom, and where they live.
 *
 * This is the part of the record that the guards are built on. A folk membership
 * is not decoration — it is what lets one person open another's page, what the
 * printed directory groups by, and what an emergency contact resolves through.
 * The API is covered in `attendees/tests/e2e/test_persons_api.py`; what only a
 * browser can show is that the buttons which create and change these things are
 * wired to it, and that the grids read the result back.
 *
 * The Feng household is the one reserved for writing.
 */

type Page = import('@playwright/test').Page;

const FAMILY_GRID = '#family-attendee-datagrid-container';

/** Turn on editing, accepting the confirm it asks first. */
async function startEditing(page: Page) {
  await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('label[for="custom-control-edit-checkbox"]').click();
  await expect(page.locator('div.attendee-form-submits').first()).not.toHaveClass(
    /dx-state-disabled/,
  );
}

test.describe('a coworker reads a household', () => {
  test('the family grid names the members and what they are to each other', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('chen_zhiming'));
    await waitForGridRows(page, FAMILY_GRID);

    const grid = page.locator(FAMILY_GRID);
    await expect(grid).toContainText('陳志明家');
    // The columns the guards and the reports are built on.
    await expect(grid).toContainText('Role');
    await expect(grid).toContainText('Scheduler');
    await expect(grid).toContainText('Emergency contact');
  });

  test('a guardianship reads as a ward, not a son', async ({ page, signIn }) => {
    // The parachute student: his guardians are not his parents, and the
    // difference is the whole reason relationships are a separate grid.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('xu_kevin'));
    await waitForGridRows(page, FAMILY_GRID);
    // The role lives on the folk membership, so it is the family grid that
    // has to say "ward" — the relationship grid is for folks that are not
    // families at all, like the carpool.
    await expect(page.locator(FAMILY_GRID)).toContainText(/ward/i);
  });

  test('the household buttons are dead until editing is on', async ({
    page,
    signIn,
  }) => {
    // Everything here changes who may open whose record, so none of it moves
    // by accident.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_ruian'));
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');

    await expect(page.locator('button.family-button-new')).toBeDisabled();
    await expect(page.locator('button.place-button-new').first()).toBeDisabled();

    await startEditing(page);
    await expect(page.locator('button.family-button-new')).toBeEnabled();
    await expect(page.locator('button.place-button-new').first()).toBeEnabled();
  });
});

test.describe('a coworker makes a second household', () => {
  test('creates a family, and it comes back as a button on the record', async ({
    page,
    signIn,
  }) => {
    // Real shape: a family splits, or somebody needs a second folk for a past
    // address. The new folk has to appear on the person's record immediately,
    // because the next thing anybody does is add members to it.
    const name = `Feng annexe ${Date.now().toString().slice(-5)}`;

    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_ruian'));
    await startEditing(page);

    await page.locator('button.family-button-new').click();
    const popup = page.locator('.dx-overlay-wrapper.dx-popup-wrapper:visible', {
      hasText: /Creating new Family/,
    });
    await expect(popup).toBeVisible();

    const field = (label: string) =>
      popup.locator('.dx-field-item', {
        has: page.locator('.dx-field-item-label-text', { hasText: label }),
      });
    await field('Name').locator('.dx-texteditor-input').first().fill(name);

    page.once('dialog', (dialog) => dialog.accept());
    await popup.getByText('Save Family', { exact: true }).click();

    // The record now offers it, which is how a member gets added to it next.
    await expect(page.locator('button.family-button', { hasText: name })).toHaveCount(1);
  });

  test('changing your mind about a new family leaves nothing behind', async ({
    page,
    signIn,
  }) => {
    // Creating a folk is not a small act — it is what the directory groups by
    // and what the guards read — so it asks first, and saying no has to mean
    // no rather than "saved anyway, undo it yourself".
    const abandoned = `Feng abandoned ${Date.now().toString().slice(-5)}`;

    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('feng_ruian'));
    await startEditing(page);

    const before = await page.locator('button.family-button').count();

    await page.locator('button.family-button-new').click();
    const popup = page.locator('.dx-overlay-wrapper.dx-popup-wrapper:visible', {
      hasText: /Creating new Family/,
    });
    await expect(popup).toBeVisible();
    await popup
      .locator('.dx-field-item', {
        has: page.locator('.dx-field-item-label-text', { hasText: 'Name' }),
      })
      .locator('.dx-texteditor-input')
      .first()
      .fill(abandoned);

    page.once('dialog', (dialog) => {
      expect(dialog.message()).toMatch(/are you sure/i);
      dialog.dismiss();
    });
    await popup.getByText('Save Family', { exact: true }).click();

    await expect(page.locator('button.family-button', { hasText: abandoned })).toHaveCount(
      0,
    );
    await expect(page.locator('button.family-button')).toHaveCount(before);
  });
});

test.describe('a coworker records where a household lives', () => {
  test('the address popup opens on the family and offers the existing one', async ({
    page,
    signIn,
  }) => {
    // Addresses hang off the folk, not the person — which is why the printed
    // directory can group a household under one street.
    await signIn('golden_data_organizer');
    await visit(page, attendeeUrl('chen_zhiming'));
    await startEditing(page);

    // Not `.place-button-new`, which carries the same class and comes first.
    const existing = page
      .locator('li.list-group-item button.place-button:not(.place-button-new)')
      .first();
    await existing.scrollIntoViewIfNeeded();
    await existing.click();

    const popup = page.locator('.dx-overlay-wrapper.dx-popup-wrapper:visible', {
      hasText: /Viewing |Creating /,
    });
    await expect(popup).toBeVisible();
    // A real street, read back from the record.
    await expect(popup).toContainText(/CA|Fremont|Hayward|Oakland|Union City/);
  });

  test('an ordinary member cannot open a stranger’s household at all', async ({
    page,
    signIn,
  }) => {
    await signIn('golden_member');
    await visit(page, attendeeUrl('tsai_serena'));
    await expect(page.locator('body')).toContainText(/not allowed to access this page/i);
  });
});
