import { test, expect } from '@playwright/test';

test.describe('Rosters List Page', () => {

  test.beforeEach(async ({ page }) => {
    // Listen for browser logs and page errors
    page.on('console', msg => {
      console.log(`BROWSER LOG [${msg.type()}]: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`BROWSER ERROR: ${err.message}`);
    });

    console.log('--- STARTING LOGIN FLOW ---');
    await page.goto('/accounts/login/');
    
    await page.fill('input[name="login"]', 'jack'); // Try user 'jack'
    const password = process.env.C_PASSWORD || 'your_password_for_superuser_in_seed';
    
    // Set the password directly via DOM evaluation to avoid logging it in Playwright reports
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

  test('Should load multi-date roster and toggle check-in/out status', async ({ page }) => {
    // 1. Go to the new rosters list page
    await page.goto('/occasions/rosters/');

    // 2. Wait for the page container to become visible
    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // 3. Select a meet from the dxTagBox
    // Wait for the tag box input to be ready
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();
    
    // Wait for the list items to render and select the first available item
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    
    // Click outside to close the dropdown if needed
    await page.mouse.click(0, 0);

    // 4. Wait for the DataGrid to load
    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });
    
    // Wait for data load panel to hide
    await expect(page.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // 5. Verify the data grid has rows
    await expect(async () => {
      const dataRowCount = await page.evaluate(() => {
        return document.querySelectorAll('.dx-data-row').length;
      });
      expect(dataRowCount).toBeGreaterThan(0);
    }).toPass({ timeout: 15000 });

    // 6. Test the check-in button behavior
    // Look for a check-in button (that is not checked-in) OR a checked-in button
    const rosterBtn = page.locator('.roster-btn').first();
    await expect(rosterBtn).toBeVisible();

    const isCheckedIn = await rosterBtn.evaluate(el => el.classList.contains('checked-in'));

    if (!isCheckedIn) {
        // If not checked in, click Check In
        await rosterBtn.click();
        
        // Should now have 'checked-in' class and say 'Checked In'
        await expect(rosterBtn).toHaveClass(/checked-in/);
        await expect(rosterBtn).toHaveText('Checked In');
    }

    // Now an 'Out' button should be present
    const outBtn = page.locator('.roster-btn-out').first();
    await expect(outBtn).toBeVisible();
    
    const isCheckedOut = await outBtn.evaluate(el => el.classList.contains('checked-out'));

    if (!isCheckedOut) {
        // Click 'Out'
        await outBtn.click();
        
        // Should now say 'Checked Out' and have 'checked-out' class
        await expect(outBtn).toHaveClass(/checked-out/);
        await expect(outBtn).toHaveText('Checked Out');
    } else {
        // Click to Undo Check Out
        await outBtn.click();
        
        // Should now say 'Out' and NOT have 'checked-out' class
        await expect(outBtn).not.toHaveClass(/checked-out/);
        await expect(outBtn).toHaveText('Out');
    }
  });
});
