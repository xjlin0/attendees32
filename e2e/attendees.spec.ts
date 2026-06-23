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

  test('Should show organizational meets grouped by assembly in the activities selector dropdown', async ({ page }) => {
    // 1. Go to the attendees list page
    await page.goto('/persons/attendees/');

    const gridContainer = page.locator('div.dataAttendees');
    await expect(gridContainer).toBeVisible({ timeout: 10000 });

    // 2. Locate the "Select activities..." tag box
    const tagBox = page.locator('div.meet-tag-box');
    await expect(tagBox).toBeVisible();

    // 3. Click the text editor container precisely where a user clicks to trigger the dropdown
    const tagBoxContainer = tagBox.locator('.dx-texteditor-container').first();
    await tagBoxContainer.click();

    // 4. Wait for the actual list items to render and become visible
    // We use a global locator because there might be other closed popups on the page (like grid filters)
    const listItems = page.locator('.dx-list-item');
    await expect(listItems.first()).toBeVisible({ timeout: 10000 });

    // 5. Verify that the dropdown contains Group Headers (representing Assemblies)
    const groupHeaders = page.locator('.dx-list-group-header');
    await expect(async () => {
      expect(await groupHeaders.count()).toBeGreaterThan(1);
    }).toPass();

    // 6. Verify that the dropdown contains individual list items (representing Meets)
    await expect(async () => {
      expect(await listItems.count()).toBeGreaterThan(5); 
    }).toPass();
  });
});
