import { test, expect } from '@playwright/test';

test.describe('Defensive and Standard 404 Error Pages', () => {

  test('Should render lightweight 404 page without base navbar before login (no session cookie)', async ({ page }) => {
    // 1. Visit a known public page first to build browsing history for testing history.back()
    await page.goto('/about/');
    await expect(page).toHaveURL(/\/about\/?$/);

    // 2. Navigate directly to the debug 404 endpoint (which maps to defensive_404_handler)
    await page.goto('/404/');
    await expect(page).toHaveURL(/\/404\/?$/);

    // 3. Verify that the standalone lightweight title and content are shown
    await expect(page.locator('h1')).toHaveText('Page Not Found (404)');

    // 4. Ensure base.html components like the global navbar are completely absent (zero DB overhead mode)
    await expect(page.locator('nav.navbar')).toHaveCount(0);

    // 5. Verify the custom styled English-only Go Back button is displayed
    const backBtn = page.locator('button.back-btn');
    await expect(backBtn).toBeVisible();
    await expect(backBtn).toHaveText('Go Back');

    // 6. Click 'Go Back' and verify history.back() returns us to the previous page (/about/)
    await backBtn.click();
    await expect(page).toHaveURL(/\/about\/?$/);
  });

  test('Should render standard 404 page with base navbar after login (with session cookie)', async ({ page }) => {
    // 1. Perform login flow to establish a session and session cookie
    console.log('--- STARTING LOGIN FLOW FOR AUTHENTICATED 404 TEST ---');
    await page.goto('/accounts/login/');
    await page.fill('input[name="login"]', 'jack');
    const password = process.env.C_PASSWORD || 'your_password_for_superuser_in_seed';

    await page.locator('input[name="password"]').evaluate((el, val) => {
      (el as HTMLInputElement).value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, password);

    await page.click('button[type="submit"]');

    try {
      await page.waitForURL('**/users/jack/**', { timeout: 10000 });
      console.log('--- LOGIN SUCCESSFUL ---');
    } catch (error) {
      console.error('--- LOGIN FAILED ---');
      throw error;
    }

    const profileUrl = page.url();

    // 2. Navigate to /404/ with active session cookie
    await page.goto('/404/');
    await expect(page).toHaveURL(/\/404\/?$/);

    // 3. Verify standard 404 header
    await expect(page.locator('h1')).toHaveText('Page not found');

    // 4. Verify base.html navbar IS present for authenticated users with active sessions
    await expect(page.locator('nav.navbar')).toBeVisible();

    // 5. Verify standard Bootstrap Go Back button is displayed
    const backBtn = page.locator('button.btn.btn-primary');
    await expect(backBtn).toBeVisible();
    await expect(backBtn).toHaveText('Go Back');

    // 6. Click 'Go Back' and verify history.back() navigates back to user profile
    await backBtn.click();
    await expect(page).toHaveURL(profileUrl);
  });
});
