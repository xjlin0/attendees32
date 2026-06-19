import { test, expect } from '@playwright/test';

// Define the URLs we want to test to ensure functional parity during migration.
// Once you build the Vue version, just add its URL to this array!
const testPages = [
  { name: 'Legacy jQuery', url: '/persons/attendee/a48e4375-1a64-4c4f-beb3-8f088bf77340/' }, // Assuming Attendee 27 has a valid address in your fixture
  // { name: 'Modern Vue', url: '/persons/vue/attendee/a48e4375-1a64-4c4f-beb3-8f088bf77340/' }
];

test.describe('Find Neighbors Feature', () => {

  // Global login before each test
  test.beforeEach(async ({ page }) => {
    // 1. Go to login page
    await page.goto('/accounts/login/');
    
    // 2. Fill in credentials (UPDATE THESE with your actual db_seed2.json test user)
    // We use standard selectors here since we might not control the 3rd party allauth HTML
    await page.fill('input[name="login"]', 'jack'); // Try user 'jack'
    await page.fill('input[name="password"]', 'password123'); // Update this password!
    await page.click('button[type="submit"]');

    // 3. Verify login success (wait for a known element on the dashboard)
    // await expect(page.locator('text=Sign Out')).toBeVisible(); 
  });

  for (const pageInfo of testPages) {
    test(`Behavior 1 & 2: Clicking place button updates spatial data and opens Nearest Neighbors on ${pageInfo.name}`, async ({ page }) => {
      
      // 1. Go to the specific attendee update page
      await page.goto(pageInfo.url);

      // Wait for the data grid to load its buttons
      const placeButton = page.locator('button.place-button').first();
      await placeButton.waitFor({ state: 'visible', timeout: 10000 });

      // 2. Intercept the Update Spatial API
      const spatialApiPromise = page.waitForResponse(response => 
        response.url().includes('/whereabouts/api/update_spatial_for/') && 
        response.request().method() === 'POST' &&
        response.status() === 200
      );

      // 3. Click the place button to open the Place Popup
      await placeButton.click();

      // 4. Wait for the Place Popup to become visible
      const placePopup = page.getByTestId('place-popup');
      await expect(placePopup).toBeVisible();

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
      await expect(placePopup).toBeHidden();

      // 9. Verify the Nearest Neighbors Popup is visible
      const neighborsPopup = page.getByTestId('nearest-neighbors-popup');
      await expect(neighborsPopup).toBeVisible();

      // 10. Verify the Nearest Neighbors API was successfully called
      const neighborsResponse = await neighborsApiPromise;
      const responseData = await neighborsResponse.json();
      expect(responseData).toHaveProperty('data');
      
      // 11. Verify the DataGrid rendered the data (look for "miles" in the distance column)
      // DevExtreme takes a moment to render the grid content
      const gridCell = neighborsPopup.locator('.dx-datagrid-content').getByText(/miles/i).first();
      await expect(gridCell).toBeVisible({ timeout: 10000 });
    });
  }
});
