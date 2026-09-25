import { test, expect } from '@playwright/test';

test.describe('AttendingMeet Report List View', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      console.log(`BROWSER LOG [${msg.type()}]: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`BROWSER ERROR: ${err.message}`);
    });

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

  test('David should be in same family as Abigail and Chileab, single and double clicks work', async ({ page }) => {
    test.setTimeout(60000); // give it plenty of time
    
    // 1. Navigate to the report
    await page.goto('/persons/attendingmeet_report/?meet=d7c8Fd_cfcch_congregation_member&showPaused=true&divisions=cfcch_children_ministry&divisions=cfcch_crossing_ministry&divisions=cfcch_chinese_ministry&divisions=cfcch_unspecified&divisions=cfcch_special_conference&divisions=cfcch_data_management');
    
    // Wait for the body to be fully loaded
    await page.waitForSelector('body', { state: 'visible' });
    
    // 2. Locate David's member div
    const davidAttendeeId = '0498c414-abd3-4173-add1-5e42053760e4';
    const davidLocator = page.locator(`div.member[data-attendee-id="${davidAttendeeId}"]`);
    await expect(davidLocator).toBeVisible();
    
    // 3. Verify David is in the same family as Abigail and Chileab
    // Get the parent .members-container
    const membersContainer = davidLocator.locator('xpath=..');
    
    // Check that Abigail is in this container
    await expect(membersContainer).toContainText('Abigail');
    
    // Check that Chileab is in this container
    await expect(membersContainer).toContainText('Chileab');
    
    // Check that David is also in this container
    await expect(membersContainer).toContainText('David');
    
    // 4. Test Single Click (Toggle Pause)
    const initialTextDecoration = await davidLocator.evaluate(el => window.getComputedStyle(el).textDecoration);
    const initialHasPausedClass = await davidLocator.evaluate(el => el.classList.contains('paused'));
    
    // Click on the member
    await davidLocator.click();
    
    // Wait for network response (PATCH)
    const patchResponse = await page.waitForResponse(response => 
      response.url().includes('/persons/api/datagrid_data_attendingmeet/') && response.request().method() === 'PATCH'
    );
    expect(patchResponse.status()).toBe(200);
    
    // Wait for class toggled
    if (initialHasPausedClass) {
      await expect(davidLocator).not.toHaveClass(/paused/);
    } else {
      await expect(davidLocator).toHaveClass(/paused/);
    }
    
    // 5. Test Double Click (Add Note)
    const noteText = 'Test Note Added from E2E';
    
    // Handle the prompt dialog automatically
    page.on('dialog', async dialog => {
      console.log(`Dialog message: ${dialog.message()}`);
      if (dialog.type() === 'prompt') {
        await dialog.accept(noteText);
      } else {
        await dialog.accept();
      }
    });
    
    // Double click the member
    await davidLocator.dblclick();
    
    // Wait for the second PATCH network response
    const secondPatchResponse = await page.waitForResponse(response => 
      response.url().includes('/persons/api/datagrid_data_attendingmeet/') && response.request().method() === 'PATCH'
    );
    expect(secondPatchResponse.status()).toBe(200);
    
    // Verify the title attribute is updated to the note text
    await expect(davidLocator).toHaveAttribute('title', noteText);
    
    // Ensure the pause state did NOT change during the double click
    if (initialHasPausedClass) {
      // It was initially paused, single click unpaused it, so now it should still be unpaused
      await expect(davidLocator).not.toHaveClass(/paused/);
    } else {
      // It was initially unpaused, single click paused it, so now it should still be paused
      await expect(davidLocator).toHaveClass(/paused/);
    }
  });
});
