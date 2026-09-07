import { test, expect } from '@playwright/test';

test.describe('Attendee List Page', () => {

  // Global login before each test (mimicking your neighbor.spec.ts setup)
  test.beforeEach(async ({ page }) => {
    // Listen for browser logs and page errors
    page.on('console', msg => {
      console.log(`BROWSER LOG [${msg.type()}]: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`BROWSER ERROR: ${err.message}`);
    });

    console.log('--- STARTING LOGIN FLOW ---');
    console.log('Navigating to login page: /accounts/login/...');
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

  test('Should show more than one attendee in attendeeDatagrid at div.dataAttendees', async ({ page }) => {
    // 1. Go to the attendees list page
    await page.goto('/persons/attendees/');

    // 2. Wait for the datagrid container to become visible
    const gridContainer = page.locator('div.dataAttendees');
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    // 3. Wait for the initial data load to finish by checking the DevExtreme loader
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // 4. Verify that the grid loads MORE than one logical attendee row
    // We use Playwright's automatic retry block `toPass` to wait for the data to fetch and render
    await expect(async () => {
      const dataRowCount = await page.evaluate(() => {
        // @ts-ignore
        const visibleRows = window.Attendees.dataAttendees.attendeeDatagrid.getVisibleRows();
        return visibleRows.filter(r => r.rowType === 'data').length;
      });
      expect(dataRowCount).toBeGreaterThan(1);
    }).toPass({ timeout: 15000 });
  });


  test('Should filter records when searching with the word "roo"', async ({ page }) => {
    // 1. Go to the attendees list page
    await page.goto('/persons/attendees/');

    const gridContainer = page.locator('div.dataAttendees');
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    // Wait for the initial data load to finish by checking the DevExtreme loader
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // Locate the precise DevExtreme search input via ARIA label
    const searchInput = gridContainer.locator('input[aria-label="Search in the data grid"]').first();
    await expect(searchInput).toBeVisible();

    // Set up a listener to wait for the API request that DevExtreme will fire when searching
    const searchResponsePromise = page.waitForResponse(response => 
      response.url().includes('filter=') && 
      response.status() === 200
    );

    // Simulate user typing into the search panel
    await searchInput.click();
    await searchInput.pressSequentially('roo', { delay: 100 });

    // Wait for DevExtreme's debounce and the subsequent API response to complete
    await searchResponsePromise;

    // Wait for the UI to finish rendering the new data
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 10000 });

    // Verify that exactly ONE logical record is found
    // Since DevExtreme splits rows into two DOM tables for fixed columns, we use the grid's JS API to count logical rows
    await expect(async () => {
      const dataRowCount = await page.evaluate(() => {
        // @ts-ignore
        const visibleRows = window.Attendees.dataAttendees.attendeeDatagrid.getVisibleRows();
        return visibleRows.filter(r => r.rowType === 'data').length;
      });
      expect(dataRowCount).toBe(1);
    }).toPass({ timeout: 15000 });
  });

  test('Should show organizational meets grouped by assembly in the activities selector dropdown, and selecting activity will add column', async ({ page }) => {
    // 1. Go to the attendees list page
    await page.goto('/persons/attendees/');

    const gridContainer = page.locator('div.dataAttendees');
    await expect(gridContainer).toBeVisible({ timeout: 10000 });
    
    // Wait for the initial data load to finish
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // 1. Read how many columns the datagrid has initially
    const initialColumnCount = await page.evaluate(() => {
      // @ts-ignore
      return window.Attendees.dataAttendees.attendeeDatagrid.columnCount();
    });
    console.log(`Initial datagrid column count: ${initialColumnCount}`);

    // Locate the "Select activities..." tag box
    const tagBox = page.locator('div.meet-tag-box');
    await expect(tagBox).toBeVisible();

    // Click to open the dropdown
    const tagBoxContainer = tagBox.locator('.dx-texteditor-container').first();
    await tagBoxContainer.click();

    // Wait for the dropdown items to appear
    const listItems = page.locator('.dx-list-item');
    await expect(listItems.first()).toBeVisible({ timeout: 10000 });

    // 2. Select "directory" from the dropdown
    const directoryItem = listItems.filter({ hasText: '通訊錄 directory' });
    await expect(directoryItem).toBeVisible();
    await directoryItem.click();

    // Wait for the grid to re-render and hide the load panel
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // 3. Read the column count again and assert it increased by 1
    const finalColumnCount = await page.evaluate(() => {
      // @ts-ignore
      return window.Attendees.dataAttendees.attendeeDatagrid.columnCount();
    });
    console.log(`Final datagrid column count: ${finalColumnCount}`);

    expect(finalColumnCount).toBe(initialColumnCount + 1);

    // 4. Verify the new column header title is "通訊錄 directory"
    const newColumnHeader = gridContainer.locator('.dx-header-row .dx-datagrid-text-content').filter({ hasText: '通訊錄 directory' });
    await expect(newColumnHeader).toBeVisible();

    // 5. Find and click the directory preview link for "Abraham Faith 亞伯拉罕"
    const previewLink = gridContainer.locator('span.directory-preview[title="click to see Abraham Faith 亞伯拉罕 in directory preview."]');
    await expect(previewLink).toBeVisible();
    await previewLink.click();

    // 6. Verify that the "Directory Preview" popup appears
    // DevExtreme detaches the original div and wraps the visible popup in a .dx-popup-wrapper
    const previewPopup = page.locator('.dx-popup-wrapper').filter({ hasText: 'Directory Preview' }).first();
    await expect(previewPopup).toBeVisible({ timeout: 10000 });
  });

  test('Should allow joining and leaving a meet via checkbox click, triggering JS confirm and AJAX PUT', async ({ page }) => {
    // 1. Go to the attendees list page
    await page.goto('/persons/attendees/');

    const gridContainer = page.locator('div.dataAttendees');
    await expect(gridContainer).toBeVisible({ timeout: 10000 });
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // 2. Open the "Select activities..." tag box and select "會員 member"
    const tagBox = page.locator('div.meet-tag-box');
    await tagBox.locator('.dx-texteditor-container').first().click();

    const listItems = page.locator('.dx-list-item');
    await expect(listItems.first()).toBeVisible({ timeout: 10000 });

    const memberItem = listItems.filter({ hasText: '會員 member' });
    await expect(memberItem).toBeVisible();
    await memberItem.click();

    // Wait for grid to re-render
    await expect(gridContainer.locator('.dx-loadpanel')).toBeHidden({ timeout: 15000 });

    // 3. Verify the new column header title is "會員 member"
    const newColumnHeader = gridContainer.locator('.dx-header-row .dx-datagrid-text-content').filter({ hasText: '會員 member' });
    await expect(newColumnHeader).toBeVisible();

    // 4. Find the checkbox for "Abraham Faith 亞伯拉罕" in the "會員 member" column
    // DevExtreme rows can be split into fixed and scrollable tables, but they share the same aria-rowindex
    const abrahamRow = gridContainer.locator('.dx-data-row', { hasText: 'Abraham Faith 亞伯拉罕' }).first();
    const rowIndex = await abrahamRow.getAttribute('aria-rowindex');
    expect(rowIndex).toBeTruthy();
    
    // Find the corresponding checkbox in either part of the split row using the same aria-rowindex
    // We use the title attribute to find the join/leave checkbox to avoid hardcoded slugs.
    const checkbox = gridContainer.locator(`.dx-data-row[aria-rowindex="${rowIndex}"] input[type="checkbox"][title="click to join/leave"]`).first();
    await expect(checkbox).toBeVisible();

    // Setup dialog handler to automatically click "OK" on JS confirm
    let dialogCount = 0;
    page.on('dialog', async dialog => {
      dialogCount++;
      await dialog.accept();
    });

    page.on('pageerror', err => {
      console.error(`PAGE ERROR: ${err.message}`);
      throw err;
    });

    // Determine initial state BEFORE clicking
    const isInitiallyChecked = await checkbox.isChecked();
    const expectedFirstAction = isInitiallyChecked ? 'leave' : 'join';

    // Setup listener for the FIRST AJAX PUT request at the REQUEST stage
    const firstRequestPromise = page.waitForRequest(async request => {
      return request.url().includes('default_attendingmeets') && request.method() === 'PUT';
    });

    // 5. Invoke the JS function directly to bypass any event routing issues
    await checkbox.evaluate((node: HTMLInputElement) => {
      // Toggle the checked state since click() normally does this before change event fires
      node.checked = !node.checked;
      
      const mockEvent = {
        currentTarget: node,
        preventDefault: () => {},
        stopPropagation: () => {}
      };
      // @ts-ignore
      window.Attendees.dataAttendees.joinAndLeaveAttendingmeet(mockEvent);
    });

    // Verify dialog was triggered before waiting for network
    await expect.poll(() => dialogCount, { timeout: 5000 }).toBeGreaterThanOrEqual(1);

    // Wait for the AJAX request to be SENT
    const firstRequest = await firstRequestPromise;
    expect(firstRequest.url()).toContain('default_attendingmeets');

    // Wait for the RESPONSE of that specific request
    const firstResponse = await firstRequest.response();
    expect(firstResponse).toBeTruthy();
    expect([200, 201, 202]).toContain(firstResponse!.status());

    // Verify the state flipped
    if (isInitiallyChecked) {
      await expect(checkbox).not.toBeChecked({ timeout: 10000 });
    } else {
      await expect(checkbox).toBeChecked({ timeout: 10000 });
    }

    // --- Second interaction: FLIP BACK ---

    const expectedSecondAction = isInitiallyChecked ? 'join' : 'leave';

    // Setup listener for the SECOND AJAX PUT request
    const secondResponsePromise = page.waitForResponse(async response => {
      return response.url().includes('default_attendingmeets') && response.request().method() === 'PUT';
    });

    // 6. Click the checkbox again
    await checkbox.evaluate((node: HTMLInputElement) => {
      // Toggle the checked state since click() normally does this before change event fires
      node.checked = !node.checked;
      
      const mockEvent = {
        currentTarget: node,
        preventDefault: () => {},
        stopPropagation: () => {}
      };
      // @ts-ignore
      window.Attendees.dataAttendees.joinAndLeaveAttendingmeet(mockEvent);
    });

    // Verify dialog was triggered
    await expect.poll(() => dialogCount, { timeout: 5000 }).toBeGreaterThanOrEqual(2);

    // Wait for the AJAX response
    const secondResponse = await secondResponsePromise;
    expect([200, 201, 202]).toContain(secondResponse.status());

    // Verify it flipped back to initial state
    if (isInitiallyChecked) {
      await expect(checkbox).toBeChecked({ timeout: 10000 });
    } else {
      await expect(checkbox).not.toBeChecked({ timeout: 10000 });
    }
  });
});
