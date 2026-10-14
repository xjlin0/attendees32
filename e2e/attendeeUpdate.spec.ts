import { test, expect } from '@playwright/test';

test.describe('Attendee Update Page', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.fill('input[name="login"]', 'jack');

    const password = process.env.C_PASSWORD || 'your_password_for_superuser_in_seed';
    await page.locator('input[name="password"]').evaluate((el, val) => {
      (el as HTMLInputElement).value = val;
    }, password);

    await page.locator('input[name="password"]').dispatchEvent('input');
    await page.click('button[type="submit"]');

    await expect(page.locator('a[href="/accounts/logout/"]')).toBeVisible({ timeout: 15000 });
  });

  test('Delete attendee stays disabled until editing is switched on', async ({ page }) => {
    const davidAttendeeId = '0498c414-abd3-4173-add1-5e42053760e4';
    await page.goto(`/persons/attendee/${davidAttendeeId}`);
    await page.waitForSelector('div.datagrid-attendee-update .dx-texteditor-input');

    const deleteButton = page.locator('div.attendee-form-delete');
    await expect(deleteButton).toHaveClass(/dx-state-disabled/);

    // Switching editing on asks for confirmation, then enables the button.
    page.once('dialog', dialog => dialog.accept());
    await page.locator('label[for="custom-control-edit-checkbox"]').click();
    await expect(deleteButton).not.toHaveClass(/dx-state-disabled/);
  });
});
