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

    // 3. Set a date range to ensure meet data is included
    const fromInput = page.locator('.dx-datebox input.dx-texteditor-input').nth(0);
    await fromInput.fill('01/01/2020, 12:00 AM');
    await fromInput.press('Enter');

    const toInput = page.locator('.dx-datebox input.dx-texteditor-input').nth(1);
    await toInput.fill('12/31/2026, 11:59 PM');
    await toInput.press('Enter');

    // Wait briefly for Vue reactive state to settle
    await page.waitForTimeout(500);

    // 4. Select a meet from the dxTagBox
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
    await expect(page.locator('.dx-loadpanel').first()).toBeHidden({ timeout: 15000 });

    // 5. Verify the data grid has rows
    await expect(async () => {
      const dataRowCount = await page.evaluate(() => {
        return document.querySelectorAll('.dx-data-row').length;
      });
      expect(dataRowCount).toBeGreaterThan(0);
    }).toPass({ timeout: 15000 });

    // 6. Test the "Show Photos" checkbox behavior
    // By default, photos are not shown, so .attendee-photo should not exist
    const photoElements = page.locator('td:not(.dx-hidden-cell) .attendee-photo');
    await expect(photoElements).toHaveCount(0);

    // Click the "Show Photos" checkbox label
    await page.locator('text=Show Photos').click();

    // Now .attendee-photo elements should appear in the visible grid
    await expect(photoElements.first()).toBeVisible({ timeout: 5000 });

    // 7. Test the check-in button and attendance count behavior
    const rosterBtn = page.locator('.roster-btn:not(.roster-btn-out)').first();
    await expect(rosterBtn).toBeVisible();
    
    // DevExtreme creates multiple tables for fixed columns, so we must pick the visible cell globally
    // Column 1 is Attendee, Column 2 is Team, Column 3 is Attendances count
    const attendanceCell = page.locator('td[role="gridcell"][aria-colindex="3"]:not(.dx-hidden-cell)').first();
    
    let isCheckedIn = await rosterBtn.evaluate(el => el.classList.contains('checked-in'));
    let initialCount = parseInt(await attendanceCell.innerText(), 10) || 0;

    if (!isCheckedIn) {
        // If not checked in, click Check In
        const postPromise = page.waitForResponse(res =>
          res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
          (res.status() === 200 || res.status() === 201)
        );
        await rosterBtn.click();
        await postPromise;
        
        // Should now have 'checked-in' class and say 'Checked In'
        await expect(rosterBtn).toHaveClass(/checked-in/);
        await expect(rosterBtn).toHaveText('Checked In');
        
        // Verify count incremented
        await expect(attendanceCell).toHaveText(String(initialCount + 1));
    } else {
        // If already checked in, click to Undo Check In
        const patchPromise1 = page.waitForResponse(res =>
          res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
          res.status() === 200
        );
        await rosterBtn.click();
        await patchPromise1;
        
        // Should now NOT have 'checked-in' class and say 'Check In'
        await expect(rosterBtn).not.toHaveClass(/checked-in/);
        await expect(rosterBtn).toHaveText('Check In');
        
        // Verify count decremented
        await expect(attendanceCell).toHaveText(String(Math.max(0, initialCount - 1)));
        
        // Click again to check back in so we can test the Out button
        const patchPromise2 = page.waitForResponse(res =>
          res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
          (res.status() === 200 || res.status() === 201)
        );
        await rosterBtn.click();
        await patchPromise2;
        await expect(rosterBtn).toHaveClass(/checked-in/);
        await expect(attendanceCell).toHaveText(String(initialCount)); // Back to initial
    }

    // Now an 'Out' button should be present in the same cell
    const outBtn = rosterBtn.locator('xpath=..').locator('.roster-btn-out');
    await expect(outBtn).toBeVisible();
    
    const isCheckedOut = await outBtn.evaluate(el => el.classList.contains('checked-out'));

    if (!isCheckedOut) {
        // Click 'Out'
        const patchPromise = page.waitForResponse(res =>
          res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
          res.status() === 200
        );
        await outBtn.click();
        await patchPromise;
        
        // Should now say 'Checked Out' and have 'checked-out' class
        await expect(outBtn).toHaveClass(/checked-out/);
        await expect(outBtn).toHaveText('Checked Out');
    } else {
        // Click to Undo Check Out
        const patchPromise = page.waitForResponse(res =>
          res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
          res.status() === 200
        );
        await outBtn.click();
        await patchPromise;
        
        // Should now say 'Out' and NOT have 'checked-out' class
        await expect(outBtn).not.toHaveClass(/checked-out/);
        await expect(outBtn).toHaveText('Out');
    }
  });

  test('Should allow check-in on a future gathering date without prior gathering and display Out button', async ({ page }) => {
    await page.goto('/occasions/rosters/');

    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // Set date range to include future dates (today to +3 months)
    const fromInput = page.locator('.dx-datebox input.dx-texteditor-input').nth(0);
    await fromInput.fill('01/01/2028, 12:00 AM');
    await fromInput.press('Enter');

    const toInput = page.locator('.dx-datebox input.dx-texteditor-input').nth(1);
    await toInput.fill('01/31/2028, 11:59 PM');
    await toInput.press('Enter');

    await page.waitForTimeout(500);

    // Select meet
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    await page.mouse.click(0, 0);

    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.dx-loadpanel').first()).toBeHidden({ timeout: 15000 });

    // Wait for the data rows and check-in buttons to be rendered
    const firstRosterBtn = page.locator('.roster-btn').first();
    await firstRosterBtn.waitFor({ state: 'visible', timeout: 15000 });

    // Find all check-in buttons in the table
    const rosterButtons = page.locator('.roster-btn:not(.roster-btn-out)');
    const count = await rosterButtons.count();
    expect(count).toBeGreaterThan(0);

    // Find the last button that currently says 'Check In' (future date)
    let targetBtn = null;
    for (let i = count - 1; i >= 0; i--) {
      const btn = rosterButtons.nth(i);
      const text = await btn.innerText();
      if (text.trim() === 'Check In') {
        targetBtn = btn;
        break;
      }
    }

    expect(targetBtn).not.toBeNull();

    // Prepare to intercept attendance POST response
    const postPromise = page.waitForResponse(response =>
      response.url().includes('/occasions/api/organization_meet_character_attendances/') &&
      (response.status() === 200 || response.status() === 201)
    );

    // Click Check In
    await targetBtn!.click();
    const response = await postPromise;
    expect([200, 201]).toContain(response.status());
    const responseData = await response.json();
    expect(responseData.gathering).toBeDefined();

    // Verify the button says 'Checked In' and has 'checked-in' class
    await expect(targetBtn!).toHaveText('Checked In');
    await expect(targetBtn!).toHaveClass(/checked-in/);

    // Verify the Out button is immediately visible right next to it
    const parentContainer = targetBtn!.locator('xpath=..');
    const outBtn = parentContainer.locator('.roster-btn-out');
    await expect(outBtn).toBeVisible();
    await expect(outBtn).toHaveText('Out');

    // Click 'Out' button to mark out
    const patchPromise = page.waitForResponse(res =>
      res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
      res.status() === 200
    );
    await outBtn.click();
    await patchPromise;

    await expect(outBtn).toHaveText('Checked Out');
    await expect(outBtn).toHaveClass(/checked-out/);

    // Click 'Checked Out' button to undo check out
    const undoPatchPromise = page.waitForResponse(res =>
      res.url().includes('/occasions/api/organization_meet_character_attendances/') &&
      res.status() === 200
    );
    await outBtn.click();
    await undoPatchPromise;

    await expect(outBtn).toHaveText('Out');
    await expect(outBtn).not.toHaveClass(/checked-out/);
  });

  test('Should show meet display name in column header when more than 1 meet is selected', async ({ page }) => {
    await page.goto('/occasions/rosters/');

    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // Select 2 meets from the dxTagBox
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();

    const listItems = page.locator('.dx-list-item');
    await listItems.first().waitFor({ state: 'visible' });
    const itemCount = await listItems.count();

    if (itemCount >= 2) {
      const meet1Name = (await listItems.nth(0).innerText()).trim();
      await listItems.nth(0).click();

      // DevExtreme dxTagBox closes the popup on selection; wait for it to close, then re-open to select meet 2
      await expect(listItems.first()).toBeHidden({ timeout: 5000 });
      await tagBox.click();
      await expect(listItems.first()).toBeVisible({ timeout: 5000 });
      await listItems.nth(1).click();
      await page.mouse.click(0, 0);

      // Wait for DataGrid to load
      const gridContainer = page.locator('.dx-datagrid').first();
      await expect(gridContainer).toBeVisible({ timeout: 10000 });

      // Check that at least one gathering column header contains the meet name
      const headers = page.locator('.dx-datagrid-headers .dx-header-row td');
      await expect(async () => {
        const headerTexts = await headers.allInnerTexts();
        const hasMeetNameInHeader = headerTexts.some(t => t.includes(meet1Name));
        expect(hasMeetNameInHeader).toBe(true);
      }).toPass({ timeout: 15000 });
    }
  });

  test('Should open + Attendee popup with search-first flow, English UI, and fast onboard form', async ({ page }) => {
    await page.goto('/occasions/rosters/');

    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // Select meet from tagbox
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    await page.mouse.click(0, 0);

    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    // Click "+ Attendee" button
    const addAttendeeBtn = page.locator('a.add-attendee');
    await expect(addAttendeeBtn).toBeVisible();
    await addAttendeeBtn.click();

    // Verify popup title
    const popupTitle = page.locator('.add-attendee-popup-wrapper .dx-popup-title');
    await expect(popupTitle).toBeVisible();
    await expect(popupTitle).toContainText('Add Attendee to Roster');

    // Verify side-by-side meet and gathering selectors
    await expect(page.locator('.add-attendee-popup-wrapper')).toContainText('Target Meet:');
    await expect(page.locator('.add-attendee-popup-wrapper')).toContainText('Gathering:');
    const gatheringDropdown = page.locator('.add-attendee-popup-wrapper .target-gathering-dropdown');
    await expect(gatheringDropdown).toBeVisible();

    // Verify search view is displayed first (mandatory search)
    const searchInput = page.locator('.add-attendee-popup-wrapper input.omni-search-box');
    await expect(searchInput).toBeVisible();
    await expect(page.locator('.add-attendee-popup-wrapper')).toContainText('Please search for attendee first');

    // Search for nonexistent person to test fast onboard button
    await searchInput.fill('NonExistentAttendeeTestXYZ');
    await page.locator('.add-attendee-popup-wrapper .search-submit-btn').click();

    // Should display no results and "Register as New Attendee" button
    const switchToOnboardBtn = page.locator('.add-attendee-popup-wrapper .switch-to-onboard-btn');
    await expect(switchToOnboardBtn).toBeVisible({ timeout: 10000 });
    await switchToOnboardBtn.click();

    // Verify onboard form fields
    const onboardContainer = page.locator('.add-attendee-popup-wrapper .onboard-view-container');
    await expect(onboardContainer).toBeVisible();
    await expect(onboardContainer).toContainText('Attendee Information');
    await expect(onboardContainer).toContainText('Contact Type');

    // Verify attendee contact type selector
    const contactTypeSelect = page.locator('.add-attendee-popup-wrapper select.ob-contact-type');
    await expect(contactTypeSelect).toBeVisible();

    // Verify back to search button
    const backBtn = page.locator('.add-attendee-popup-wrapper .back-to-search-btn');
    await expect(backBtn).toBeVisible();
    await backBtn.click();
    await expect(searchInput).toBeVisible();
  });
});


