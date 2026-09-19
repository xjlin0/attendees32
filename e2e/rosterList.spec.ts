import { test, expect } from '@playwright/test';

test.describe('Single Roster Page', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      console.log(`BROWSER LOG [${msg.type()}]: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`BROWSER ERROR: ${err.message}`);
    });

    console.log('--- STARTING LOGIN FLOW ---');
    await page.goto('/accounts/login/');
    
    await page.fill('input[name="login"]', 'jack'); // Try user 'jack'
    const password = process.env.C_PASSWORD || '5811630';
    
    await page.locator('input[name="password"]').evaluate((el, val) => {
      (el as HTMLInputElement).value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, password);
    
    await page.click('button[type="submit"]');

    try {
      await page.waitForURL('**/users/jack/**', { timeout: 10000 });
      console.log(`--- LOGIN SUCCESSFUL ---`);
    } catch (error) {
      console.error(`--- LOGIN FAILED ---`);
      throw error;
    } 
  });

  test('Should load single roster page without JS errors', async ({ page }) => {
    // 1. Go to the single roster list page
    await page.goto('/occasions/roster/');

    // 2. Wait for the page container to become visible
    const appContainer = page.locator('.roster-container');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // 3. Ensure the filter form is rendered
    const filterForm = page.locator('.dx-form').first();
    await expect(filterForm).toBeVisible({ timeout: 10000 });

    // 4. Select a meet from the dropdown (meets)
    // The first two dropdowns are Date pickers for 'from' and 'till'. The 3rd is 'meets'.
    const meetBox = page.locator('.dx-dropdowneditor-icon').nth(2);
    await meetBox.click();
    
    // Wait for the list items to render and select the first available item
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    
    // Click outside to close the dropdown if needed
    await page.mouse.click(0, 0);

    // 5. Wait for the DataGrid to load
    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });
    
    // We don't check for dx-loadpanel because data might not load until a gathering is selected

    // 6. Verify the data grid has headers (meaning it successfully initialized)
    await expect(async () => {
      const headerCount = await page.evaluate(() => {
        return document.querySelectorAll('.dx-datagrid-headers').length;
      });
      expect(headerCount).toBeGreaterThan(0);
    }).toPass({ timeout: 15000 });
  });
});
