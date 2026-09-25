import { test, expect } from '@playwright/test';

test.describe('AttendingMeet Envelopes List View', () => {

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

  test('Abigail and Chileab appear as recipient because David is paused and filtered out', async ({ page }) => {
    test.setTimeout(90000);
    
    // 0. Go to report page and ENSURE David is paused
    await page.goto('/persons/attendingmeet_report/?meet=d7c8Fd_cfcch_congregation_member&divisions=cfcch_children_ministry&divisions=cfcch_crossing_ministry&divisions=cfcch_chinese_ministry&divisions=cfcch_unspecified&divisions=cfcch_special_conference&divisions=cfcch_data_management&showPaused=true');
    await page.waitForSelector('body', { state: 'visible' });
    
    const davidAttendeeId = '0498c414-abd3-4173-add1-5e42053760e4';
    const davidLocator = page.locator(`div.member[data-attendee-id="${davidAttendeeId}"]`);
    await expect(davidLocator).toBeVisible();
    
    const isPaused = await davidLocator.evaluate(el => el.classList.contains('paused'));
    if (!isPaused) {
      // Pause him
      await davidLocator.click();
      await page.waitForResponse(response => 
        response.url().includes('/persons/api/datagrid_data_attendingmeet/') && response.request().method() === 'PATCH'
      );
      await expect(davidLocator).toHaveClass(/paused/);
    }
    
    // 1. Navigate to the envelopes report WITHOUT showPaused=true
    await page.goto('/persons/attendingmeet_envelopes/?meet=d7c8Fd_cfcch_congregation_member&divisions=cfcch_children_ministry&divisions=cfcch_crossing_ministry&divisions=cfcch_chinese_ministry&divisions=cfcch_unspecified&divisions=cfcch_special_conference&divisions=cfcch_data_management');
    
    // Wait for the body to be fully loaded
    await page.waitForSelector('body', { state: 'visible' });
    
    // 2. We expect to see Abigail and Chileab together in one recipient name block
    const recipients = page.locator('div.recipient span');
    await expect(recipients.first()).toBeVisible();
    
    const count = await recipients.count();
    let found = false;
    let actualText = '';
    
    for (let i = 0; i < count; i++) {
      const text = await recipients.nth(i).innerText();
      if (text.includes('Abigail') && text.includes('Chileab') && !text.includes('David')) {
        found = true;
        actualText = text;
        break;
      }
    }
    
    console.log(`Found recipient text: ${actualText}`);
    expect(found).toBe(true);
    
    // Clean up: Restore David to active
    await page.goto('/persons/attendingmeet_report/?meet=d7c8Fd_cfcch_congregation_member&divisions=cfcch_children_ministry&divisions=cfcch_crossing_ministry&divisions=cfcch_chinese_ministry&divisions=cfcch_unspecified&divisions=cfcch_special_conference&divisions=cfcch_data_management&showPaused=true');
    await page.waitForSelector('body', { state: 'visible' });
    const davidLoc = page.locator(`div.member[data-attendee-id="${davidAttendeeId}"]`);
    await expect(davidLoc).toBeVisible();
    const stillPaused = await davidLoc.evaluate(el => el.classList.contains('paused'));
    if (stillPaused) {
      await davidLoc.click();
      await page.waitForResponse(response => 
        response.url().includes('/persons/api/datagrid_data_attendingmeet/') && response.request().method() === 'PATCH'
      );
      await expect(davidLoc).not.toHaveClass(/paused/);
    }
  });
});
