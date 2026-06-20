import { test, expect } from '@playwright/test';

// Define the URLs we want to test to ensure functional parity during migration.
// Once you build the Vue version, just add its URL to this array!
const testPages = [
  { name: 'Legacy jQuery', url: '/persons/attendee/a48e4375-1a64-4c4f-beb3-8f088bf77340' }, // Assuming Attendee 27 has a valid address in your fixture
  // { name: 'Modern Vue', url: '/persons/vue/attendee/a48e4375-1a64-4c4f-beb3-8f088bf77340' }
];

test.describe('Find Neighbors Feature', () => {

  // Global login before each test
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
    // 1. Go to login page
    await page.goto('/accounts/login/');
    console.log('Successfully loaded login page. Filling credentials...');

    // 2. Fill in credentials (UPDATE THESE with your actual db_seed2.json test user)
    // We use standard selectors here since we might not control the 3rd party allauth HTML
    await page.fill('input[name="login"]', 'jack'); // Try user 'jack'
    const password = process.env.C_PASSWORD || 'your_password_for_superuser_in_seed';
    console.log(`Using password: ${password === 'your_password_for_superuser_in_seed' ? 'please use password in seed' : 'provided secret in env'}`);
    
    // Set the password directly via DOM evaluation to avoid logging it in Playwright reports
    await page.locator('input[name="password"]').evaluate((el, val) => {
      (el as HTMLInputElement).value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, password);
    
    console.log('Clicking Submit button...');
    await page.click('button[type="submit"]');

    // 3. Verify login success (wait for a known element on the dashboard)
    console.log('Submitted login form. Waiting for redirect to /users/jack/...');
    try {
      await page.waitForURL('**/users/jack/**', { timeout: 10000 });
      console.log(`--- LOGIN SUCCESSFUL ---`);
      console.log(`Successfully logged in and redirected to dashboard. Current URL: ${page.url()}`);
    } catch (error) {
      console.error(`--- LOGIN FAILED ---`);
      console.error(`Login verification failed! Expected redirect to /users/jack/ but current URL is: ${page.url()}`);
      throw error;
    } 
  });

  for (const pageInfo of testPages) {
    test(`Behavior 1 & 2: Clicking place button updates spatial data and opens Nearest Neighbors on ${pageInfo.name}`, async ({ page }) => {
      
      // 1. Go to the specific attendee update page
      await page.goto(pageInfo.url);

      // Wait for the data grid to load its buttons
      const placeButton = page.locator('button.place-button:not([disabled])').first();
      await placeButton.waitFor({ state: 'visible', timeout: 10000 });

      // 2. Intercept the Update Spatial API
      const spatialApiPromise = page.waitForResponse(response => 
        response.url().includes('/whereabouts/api/update_spatial_for/') && 
        response.request().method() === 'POST' &&
        response.status() === 200
      );

      // 3. Click the place button to open the Place Popup
      await placeButton.click();

      // 4. Wait for the Place Popup to become visible (check for its inner form container)
      const placePopupContent = page.locator('.locate-form');
      await expect(placePopupContent).toBeVisible();

      // 5. Verify the Update Spatial API was called correctly in the background
      const spatialResponse = await spatialApiPromise;
      expect(spatialResponse.ok()).toBeTruthy();

      // ---------------------------------------------------------
      // Behavior 2: Find Neighbors Modal
      // ---------------------------------------------------------

      // 6. Intercept the Nearest Neighbors API
      const neighborsApiPromise = page.waitForResponse(response => 
        response.url().includes('/whereabouts/api/nearest_neighbors_for/') && 
        response.status() === 200
      );

      // 7. Click the "Find neighbors" button
      const findNeighborsBtn = page.getByTestId('find-neighbors-btn');
      await findNeighborsBtn.click();

      // 8. Verify the Place Popup is hidden
      await expect(placePopupContent).toBeHidden();

      // 9. Verify the Nearest Neighbors Popup is visible (check for its inner grid container)
      const neighborsPopupContent = page.locator('#nearest-neighbors-grid');
      await expect(neighborsPopupContent).toBeVisible();

      // 10. Verify the Nearest Neighbors API was successfully called
      const neighborsResponse = await neighborsApiPromise;
      const responseData = await neighborsResponse.json();
      expect(responseData).toHaveProperty('data');
      
      // 11. Verify the DataGrid rendered the data (look for "miles" in the distance column)
      // DevExtreme takes a moment to render the grid content
      const gridCell = neighborsPopupContent.locator('.dx-datagrid-content').getByText(/miles/i).first();
      await expect(gridCell).toBeVisible({ timeout: 10000 });
    });
  }
});
