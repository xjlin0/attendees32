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

    // Verify dynamic birth day dropdown options when selecting February
    const bmonthSelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-bmonth');
    const bdaySelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-bday');
    await bmonthSelect.selectOption('2');
    const febDays = await bdaySelect.locator('option').allTextContents();
    expect(febDays).not.toContain('30');
    expect(febDays).not.toContain('31');
    expect(febDays).toContain('29');

    // Enter non-leap year 1999 -> max is 28
    const byearInput = page.locator('.add-attendee-popup-wrapper .attendee-block-1 input.ob-byear');
    await byearInput.fill('1999');
    await byearInput.dispatchEvent('change');
    const feb1999Days = await bdaySelect.locator('option').allTextContents();
    expect(feb1999Days).not.toContain('29');
    expect(feb1999Days).toContain('28');

    // Verify onboard form fields
    const onboardContainer = page.locator('.add-attendee-popup-wrapper .onboard-view-container');
    await expect(onboardContainer).toBeVisible();
    await expect(onboardContainer).toContainText('Attendee Information');
    await expect(onboardContainer).toContainText('Contact Type');

    // Verify attendee contact type selector
    const contactTypeSelect = page.locator('.add-attendee-popup-wrapper select.ob-contact-type');
    await expect(contactTypeSelect).toBeVisible();

    // Verify Attendee Division and Relationship dropdowns [division][Relationship]
    const attDivisionSelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-division');
    await expect(attDivisionSelect).toBeVisible();
    await expect(async () => {
      const val = await attDivisionSelect.inputValue();
      expect(val).toBeTruthy();
    }).toPass({ timeout: 5000 });

    const attRelSelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-relationship');
    await expect(attRelSelect).toBeVisible();
    await expect(async () => {
      const selectedOptionText = await attRelSelect.locator('option:checked').innerText();
      expect(selectedOptionText.trim().toLowerCase()).toBe('self');
    }).toPass({ timeout: 5000 });

    // Verify guardian / companion relationship options dynamically loaded from API if section is present
    const relSelect = page.locator('.add-attendee-popup-wrapper select.ob-p-relationship');
    if (await relSelect.isVisible()) {
      await expect(async () => {
        const relOptions = await relSelect.locator('option').allTextContents();
        const normalized = relOptions.map(t => t.trim().toLowerCase());
        expect(normalized).toContain('parent');
        expect(normalized).toContain('child');
        expect(normalized).not.toContain('self');
        expect(normalized).not.toContain('hidden');
      }).toPass({ timeout: 5000 });
    }

    // Verify removal of bottom action buttons More Companions & More Attendees
    const moreCompanionsBtn = page.locator('.add-attendee-popup-wrapper .more-companions-btn');
    const moreAttendeesBtn = page.locator('.add-attendee-popup-wrapper .more-attendees-btn');
    await expect(moreCompanionsBtn).toHaveCount(0);
    await expect(moreAttendeesBtn).toHaveCount(0);

    // Verify Companion section and (+) button to add another companion
    const guardianSection = page.locator('.add-attendee-popup-wrapper .guardian-section');
    await expect(guardianSection).toBeVisible();
    await expect(guardianSection).toContainText('Companion Information');

    // In adult meets, companion information is collapsed by default; click header to open it
    const guardianContent = page.locator('.add-attendee-popup-wrapper .guardian-section-content');
    if (!(await guardianContent.isVisible())) {
      await page.locator('.add-attendee-popup-wrapper .guardian-section-header').click();
      await expect(guardianContent).toBeVisible();
    }
    await expect(guardianSection).toContainText('Companion 1');

    const comp1AddBtn = page.locator('.add-attendee-popup-wrapper .companion-block-1 .add-more-companion-btn');
    await expect(comp1AddBtn).toBeVisible();
    await comp1AddBtn.click();

    const comp2Block = page.locator('.add-attendee-popup-wrapper .companion-block-extra');
    await expect(comp2Block).toBeVisible();
    await expect(comp2Block).toContainText('Companion 2');
    await expect(comp2Block.locator('.add-more-companion-btn')).toBeVisible();

    await comp2Block.locator('.remove-companion-btn').click();
    await expect(comp2Block).toBeHidden();

    // Verify modal title in onboard state has [←] back button and onboard title
    const titleContainer = page.locator('.add-attendee-popup-wrapper .popup-title-container');
    await expect(titleContainer).toContainText('Add Attendee to Rosters / New Attendee Registration');
    const backBtn = page.locator('.add-attendee-popup-wrapper .popup-title-container .back-to-search-btn');
    await expect(backBtn).toBeVisible();

    // Click [←] back button: returns to search view and restores search title
    await backBtn.click();
    await expect(searchInput).toBeVisible();
    await expect(backBtn).toBeHidden();
    await expect(titleContainer).toContainText("Add Attendee to Rosters, Welcome! Let's search first.");
  });

  test('Should satisfy all fast onboarding UI rules: autofocus, column preselection, 1 name only, no other gender, responsive layout, post-onboard row & column highlight and check-in', async ({ page }) => {
    await page.goto('/occasions/rosters/');

    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // Set a date range
    const fromInput = page.locator('.dx-datebox input.dx-texteditor-input').nth(0);
    await fromInput.fill('01/01/2020, 12:00 AM');
    await fromInput.press('Enter');

    const toInput = page.locator('.dx-datebox input.dx-texteditor-input').nth(1);
    await toInput.fill('12/31/2026, 11:59 PM');
    await toInput.press('Enter');
    await page.waitForTimeout(500);

    // Select meet from tagbox
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    await page.mouse.click(0, 0);

    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.dx-loadpanel').first()).toBeHidden({ timeout: 15000 });

    // 2. Preselect a specific gathering column by clicking its header
    const gatheringHeaders = page.locator('.dx-header-row .roster-header-cell');
    await expect(gatheringHeaders.first()).toBeVisible({ timeout: 15000 });
    const headerCount = await gatheringHeaders.count();
    expect(headerCount).toBeGreaterThan(0);

    // Click the first gathering header to highlight that column
    await gatheringHeaders.first().click();

    // Click "+ Attendee" button
    const addAttendeeBtn = page.locator('a.add-attendee');
    await addAttendeeBtn.click();

    // 0. Test Autofocus on search input
    const searchInput = page.locator('.add-attendee-popup-wrapper input.omni-search-box');
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await expect(searchInput).toBeFocused({ timeout: 5000 });

    // 1. Test Font size of Target Meet and Gathering labels
    const targetMeetLabel = page.locator('.add-attendee-popup-wrapper .meet-gathering-header .target-meet-label');
    const targetGatheringLabel = page.locator('.add-attendee-popup-wrapper .meet-gathering-header .target-gathering-label');
    await expect(targetMeetLabel).toBeVisible();
    await expect(targetGatheringLabel).toBeVisible();
    const meetLabelFontSize = await targetMeetLabel.evaluate((el) => window.getComputedStyle(el).fontSize);
    const gatheringLabelFontSize = await targetGatheringLabel.evaluate((el) => window.getComputedStyle(el).fontSize);
    expect(meetLabelFontSize).toBe(gatheringLabelFontSize);

    // 2. Test preselected gathering matches the highlighted column
    const gatheringSelect = page.locator('.add-attendee-popup-wrapper select.target-gathering-dropdown');
    const selectedGatheringValue = await gatheringSelect.inputValue();
    expect(selectedGatheringValue).toBeTruthy();

    // Search for a unique new attendee name
    const uniqueFirstName = `Fast${Date.now()}`;
    await searchInput.fill(uniqueFirstName);
    await page.locator('.add-attendee-popup-wrapper .search-submit-btn').click();

    // Click Register as New Attendee
    const switchToOnboardBtn = page.locator('.add-attendee-popup-wrapper .switch-to-onboard-btn');
    await expect(switchToOnboardBtn).toBeVisible({ timeout: 10000 });
    await switchToOnboardBtn.click();

    // Verify dynamic birth day dropdown options when selecting February
    const bmonthSelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-bmonth');
    const bdaySelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-bday');
    await bmonthSelect.selectOption('2');
    const febDays = await bdaySelect.locator('option').allTextContents();
    expect(febDays).not.toContain('30');
    expect(febDays).not.toContain('31');
    expect(febDays).toContain('29');

    // Enter non-leap year 1999 -> max is 28
    const byearInput = page.locator('.add-attendee-popup-wrapper .attendee-block-1 input.ob-byear');
    await byearInput.fill('1999');
    await byearInput.dispatchEvent('change');
    const feb1999Days = await bdaySelect.locator('option').allTextContents();
    expect(feb1999Days).not.toContain('29');
    expect(feb1999Days).toContain('28');

    // 3b. Verify Gender select does NOT contain 'other'
    const genderOptions = await page.locator('.add-attendee-popup-wrapper select.ob-gender option').allTextContents();
    const normalizedGenderOptions = genderOptions.map(o => o.trim().toLowerCase());
    expect(normalizedGenderOptions).not.toContain('other');
    expect(normalizedGenderOptions).toContain('unspecified');
    expect(normalizedGenderOptions).toContain('male');
    expect(normalizedGenderOptions).toContain('female');

    // 4. Verify Responsive layout order: [last_name2] precedes [first_name2]
    const lastName2Input = page.locator('.add-attendee-popup-wrapper input.ob-last-name2');
    const firstName2Input = page.locator('.add-attendee-popup-wrapper input.ob-first-name2');
    const isLastName2BeforeFirstName2 = await page.evaluate(() => {
      const ln2 = document.querySelector('.add-attendee-popup-wrapper input.ob-last-name2');
      const fn2 = document.querySelector('.add-attendee-popup-wrapper input.ob-first-name2');
      return !!(ln2 && fn2 && (ln2.compareDocumentPosition(fn2) & Node.DOCUMENT_POSITION_FOLLOWING));
    });
    expect(isLastName2BeforeFirstName2).toBe(true);

    // 3a. Verify only ONE name is sufficient: Fill ONLY first_name, leave last_name and Chinese names empty
    await page.locator('.add-attendee-popup-wrapper input.ob-first-name').fill(uniqueFirstName);

    // Check if this meet requires kid fields or guardian fields
    const isKidSectionVisible = await page.locator('.add-attendee-popup-wrapper .kid-specific-fields').isVisible();
    if (isKidSectionVisible) {
      // Birthday
      await page.locator('.add-attendee-popup-wrapper input.ob-byear').fill('2018');
      await page.locator('.add-attendee-popup-wrapper select.ob-bmonth').selectOption('5');
      await page.locator('.add-attendee-popup-wrapper select.ob-bday').selectOption('15');
      // Grade & Food
      const gradeSelect = page.locator('.add-attendee-popup-wrapper select.ob-grade');
      const gradeOptions = await gradeSelect.locator('option').all();
      if (gradeOptions.length > 1) {
        await gradeSelect.selectOption({ index: 1 });
      }
      await page.locator('.add-attendee-popup-wrapper input.ob-food-pref').fill('None');

      // Unaccompanied minor
      await page.locator('.add-attendee-popup-wrapper input.ob-unaccompanied').check();
    }

    // 5. Submit fast onboard form
    await page.locator('.add-attendee-popup-wrapper button.ob-submit-btn').click();

    // Verify popup closes on success
    await expect(page.locator('.add-attendee-popup-wrapper')).toBeHidden({ timeout: 15000 });

    // 5. Verify the newly onboarded attendee row is highlighted (selected) on the grid
    const selectedRow = page.locator('.dx-datagrid-rowsview .dx-data-row.dx-selection').first();
    await expect(selectedRow).toBeVisible({ timeout: 10000 });
    await expect(selectedRow).toContainText(uniqueFirstName);

    // 5. Verify the gathering column is highlighted on the grid
    const highlightedHeader = page.locator('.dx-datagrid-headers [class*="roster-col-idx-"]');
    await expect(highlightedHeader.first()).toBeVisible({ timeout: 5000 });

    // 5. Verify the check-in button is green / solid checked-in (has .checked-in class) and Out button is visible
    const checkInBtn = page.locator('.dx-datagrid-rowsview .dx-data-row.dx-selection .roster-btn.checked-in').first();
    await expect(checkInBtn).toBeVisible({ timeout: 5000 });
    const outBtn = page.locator('.dx-datagrid-rowsview .dx-data-row.dx-selection .roster-btn-out').first();
    await expect(outBtn).toBeVisible({ timeout: 5000 });
  });

  test('Should support modal Esc close, contact validation, unaccompanied collapse, companion gender, and multiple contacts', async ({ page }) => {
    await page.goto('/occasions/rosters/');

    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // Select meet
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    await page.mouse.click(0, 0);

    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    // 1. Verify Esc key closes the Add Attendee modal
    const addAttendeeBtn = page.locator('a.add-attendee');
    await expect(addAttendeeBtn).toBeVisible();
    await addAttendeeBtn.click();

    const popupWrapper = page.locator('.add-attendee-popup-wrapper');
    await expect(popupWrapper).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(popupWrapper).toBeHidden({ timeout: 5000 });

    // Verify rightmost (X) close button closes the Add Attendee modal
    await addAttendeeBtn.click();
    await expect(popupWrapper).toBeVisible();
    const closeBtn = page.locator('.add-attendee-popup-wrapper .popup-close-btn');
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();
    await expect(popupWrapper).toBeHidden({ timeout: 5000 });

    // Verify frontend birthday validation in utilities (defaults to year 2000 if year is empty)
    const bdayTest1 = await page.evaluate(() => {
      return (window as any).Attendees?.utilities?.validateFastInputBirthday('', '2', '31');
    });
    expect(bdayTest1?.valid).toBe(false);
    expect(bdayTest1?.message).toContain('Invalid calendar date');

    const bdayTest2 = await page.evaluate(() => {
      return (window as any).Attendees?.utilities?.validateFastInputBirthday('', '2', '29');
    });
    expect(bdayTest2?.valid).toBe(true);

    // Reopen popup
    await addAttendeeBtn.click();
    await expect(popupWrapper).toBeVisible();

    // Search and switch to onboard
    const searchInput = page.locator('.add-attendee-popup-wrapper input.omni-search-box');
    await searchInput.fill('NonExistentAttendeeEscTest');
    await page.locator('.add-attendee-popup-wrapper .search-submit-btn').click();

    const switchToOnboardBtn = page.locator('.add-attendee-popup-wrapper .switch-to-onboard-btn');
    await expect(switchToOnboardBtn).toBeVisible({ timeout: 10000 });
    await switchToOnboardBtn.click();

    // Verify dynamic birth day dropdown options when selecting February
    const bmonthSelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-bmonth');
    const bdaySelect = page.locator('.add-attendee-popup-wrapper .attendee-block-1 select.ob-bday');
    await bmonthSelect.selectOption('2');
    const febDays = await bdaySelect.locator('option').allTextContents();
    expect(febDays).not.toContain('30');
    expect(febDays).not.toContain('31');
    expect(febDays).toContain('29');

    // Enter non-leap year 1999 -> max is 28
    const byearInput = page.locator('.add-attendee-popup-wrapper .attendee-block-1 input.ob-byear');
    await byearInput.fill('1999');
    await byearInput.dispatchEvent('change');
    const feb1999Days = await bdaySelect.locator('option').allTextContents();
    expect(feb1999Days).not.toContain('29');
    expect(feb1999Days).toContain('28');

    // 2. Dynamic multiple contacts (+ and - buttons)
    const attendeeContactRows = page.locator('.add-attendee-popup-wrapper .attendee-contacts-container .contact-row');
    await expect(attendeeContactRows).toHaveCount(1);
    // Row 1 only has + button, no - button
    await expect(attendeeContactRows.nth(0).locator('.add-contact-btn')).toBeVisible();
    await expect(attendeeContactRows.nth(0).locator('.remove-contact-btn')).toHaveCount(0);

    // Click + to add a second contact row
    await attendeeContactRows.nth(0).locator('.add-contact-btn').click();
    await expect(attendeeContactRows).toHaveCount(2);
    // Row 2 has both + and - buttons
    await expect(attendeeContactRows.nth(1).locator('.add-contact-btn')).toBeVisible();
    await expect(attendeeContactRows.nth(1).locator('.remove-contact-btn')).toBeVisible();

    // Click - on row 2 to remove it
    await attendeeContactRows.nth(1).locator('.remove-contact-btn').click();
    await expect(attendeeContactRows).toHaveCount(1);

    // 3. Companion Section toggle and Companion Gender input
    const guardianSection = page.locator('.add-attendee-popup-wrapper .guardian-section');
    await expect(guardianSection).toBeVisible();
    const guardianHeader = page.locator('.add-attendee-popup-wrapper .guardian-section-header');
    const guardianContent = page.locator('.add-attendee-popup-wrapper .guardian-section-content');
    const collapseIcon = page.locator('.add-attendee-popup-wrapper .companion-collapse-icon');

    if (!(await guardianContent.isVisible())) {
      // If collapsed by default (adult meet), verify caret right, click to expand, verify caret down
      await expect(collapseIcon).toHaveClass(/fa-caret-right/);
      await guardianHeader.click();
      await expect(guardianContent).toBeVisible();
      await expect(collapseIcon).toHaveClass(/fa-caret-down/);
    } else {
      // If expanded by default (kid meet), verify caret down, test collapse and re-expand
      await expect(collapseIcon).toHaveClass(/fa-caret-down/);
      await guardianHeader.click();
      await expect(guardianContent).toBeHidden();
      await expect(collapseIcon).toHaveClass(/fa-caret-right/);
      await guardianHeader.click();
      await expect(guardianContent).toBeVisible();
      await expect(collapseIcon).toHaveClass(/fa-caret-down/);
    }

    const comp1Gender = page.locator('.add-attendee-popup-wrapper .companion-block-1 select.ob-p-gender');
    await expect(comp1Gender).toBeVisible();
    const comp1GenderOptions = await comp1Gender.locator('option').allTextContents();
    const normalizedGenders = comp1GenderOptions.map(t => t.trim().toLowerCase());
    expect(normalizedGenders).toContain('unspecified');
    expect(normalizedGenders).toContain('female');
    expect(normalizedGenders).toContain('male');

    // 4. Unaccompanied minor checkbox collapses all companions
    const unaccompaniedCheck = page.locator('.add-attendee-popup-wrapper input.ob-unaccompanied');
    const comp1Block = page.locator('.add-attendee-popup-wrapper .companion-block-1');
    if (await unaccompaniedCheck.isVisible()) {
      await expect(comp1Block).toBeVisible();

      // Check unaccompanied
      await unaccompaniedCheck.check();
      await expect(comp1Block).toBeHidden();

      // Uncheck unaccompanied
      await unaccompaniedCheck.uncheck();
      await expect(comp1Block).toBeVisible();
    }
  });

  test('Should support attendee (+) button to register multiple attendees simultaneously', async ({ page }) => {
    await page.goto('/occasions/rosters/');

    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });

    // Select meet
    const tagBox = page.locator('.dx-tagbox').first();
    await tagBox.click();
    const listItem = page.locator('.dx-list-item').first();
    await listItem.waitFor({ state: 'visible' });
    await listItem.click();
    await page.mouse.click(0, 0);

    const gridContainer = page.locator('.dx-datagrid').first();
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    const addAttendeeBtn = page.locator('a.add-attendee');
    await expect(addAttendeeBtn).toBeVisible();
    await addAttendeeBtn.click();

    const popupWrapper = page.locator('.add-attendee-popup-wrapper');
    await expect(popupWrapper).toBeVisible();

    // Search and switch to onboard
    const searchInput = page.locator('.add-attendee-popup-wrapper input.omni-search-box');
    await expect(searchInput).toBeVisible();
    await searchInput.click();
    await searchInput.fill(`NonExistentMultiTest_${Date.now()}`);
    await page.locator('.add-attendee-popup-wrapper .search-submit-btn').click();

    const switchToOnboardBtn = page.locator('.add-attendee-popup-wrapper .switch-to-onboard-btn').first();
    await expect(switchToOnboardBtn).toBeVisible({ timeout: 10000 });
    await switchToOnboardBtn.click();

    // Verify Attendee 1 has add (+) button, but no remove (X) button
    const attendeeBlocks = page.locator('.add-attendee-popup-wrapper .attendee-block');
    const att1Block = attendeeBlocks.nth(0);
    const att1AddBtn = att1Block.locator('.add-more-attendee-btn');
    await expect(att1AddBtn).toBeVisible();
    await expect(att1Block.locator('.remove-attendee-btn')).toHaveCount(0);

    // Click (+) button on Attendee 1 to add Attendee 2
    await att1AddBtn.click();

    let currentAttendeeBlocks = page.locator('.add-attendee-popup-wrapper .attendee-block');
    await expect(currentAttendeeBlocks).toHaveCount(2);

    // Verify Attendee 2 block has both (+) button and remove (X) button
    const att2Block = currentAttendeeBlocks.nth(1);
    await expect(att2Block.locator('.add-more-attendee-btn')).toBeVisible();
    const removeAtt2Btn = att2Block.locator('.remove-attendee-btn');
    await expect(removeAtt2Btn).toBeVisible();

    // Click remove (X) on Attendee 2 to verify removal
    await removeAtt2Btn.click();
    await expect(page.locator('.add-attendee-popup-wrapper .attendee-block')).toHaveCount(1);

    // Verify More Attendees button is removed from bottom actions
    await expect(page.locator('.add-attendee-popup-wrapper .more-attendees-btn')).toHaveCount(0);

    // Click (+) on Attendee 1 to re-add Attendee 2
    await att1AddBtn.click();

    currentAttendeeBlocks = page.locator('.add-attendee-popup-wrapper .attendee-block');
    await expect(currentAttendeeBlocks).toHaveCount(2);

    // Fill Attendee 1
    const ts = Date.now();
    const att1First = `Multi1_${ts}`;
    const att2First = `Multi2_${ts}`;
    await currentAttendeeBlocks.nth(0).locator('input.ob-first-name').fill(att1First);
    await currentAttendeeBlocks.nth(0).locator('input.ob-last-name').fill('FamilyUnit');

    // Fill Attendee 2
    await currentAttendeeBlocks.nth(1).locator('input.ob-first-name').fill(att2First);
    await currentAttendeeBlocks.nth(1).locator('input.ob-last-name').fill('FamilyUnit');

    // If kid meet, fill kid fields and check unaccompanied for test simplicity
    const isKidSectionVisible = await currentAttendeeBlocks.nth(0).locator('.kid-specific-fields').isVisible();
    if (isKidSectionVisible) {
      // Attendee 1
      await currentAttendeeBlocks.nth(0).locator('input.ob-byear').fill('2017');
      await currentAttendeeBlocks.nth(0).locator('select.ob-bmonth').selectOption('3');
      await currentAttendeeBlocks.nth(0).locator('select.ob-bday').selectOption('10');
      const g1 = currentAttendeeBlocks.nth(0).locator('select.ob-grade');
      if ((await g1.locator('option').all()).length > 1) await g1.selectOption({ index: 1 });
      await currentAttendeeBlocks.nth(0).locator('input.ob-food-pref').fill('None');

      // Attendee 2
      await currentAttendeeBlocks.nth(1).locator('input.ob-byear').fill('2019');
      await currentAttendeeBlocks.nth(1).locator('select.ob-bmonth').selectOption('6');
      await currentAttendeeBlocks.nth(1).locator('select.ob-bday').selectOption('20');
      const g2 = currentAttendeeBlocks.nth(1).locator('select.ob-grade');
      if ((await g2.locator('option').all()).length > 1) await g2.selectOption({ index: 1 });
      await currentAttendeeBlocks.nth(1).locator('input.ob-food-pref').fill('None');

      await page.locator('.add-attendee-popup-wrapper input.ob-unaccompanied').check();
    }

    // Submit form
    await page.locator('.add-attendee-popup-wrapper button.ob-submit-btn').click();

    // Verify popup closes on success
    await expect(page.locator('.add-attendee-popup-wrapper')).toBeHidden({ timeout: 15000 });
  });
});



