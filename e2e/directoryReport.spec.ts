import { test, expect } from '@playwright/test';

test.describe('Directory Report List View', () => {

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
    
    // We dispatch input event to ensure Vue/React or native validation catches the value change
    await page.locator('input[name="password"]').dispatchEvent('input');
    await page.click('button[type="submit"]');

    await expect(page.locator('a[href="/accounts/logout/"]')).toBeVisible({ timeout: 15000 });
  });

  test('Should print Isaac twice because he is in both his own family and parents family', async ({ page }) => {
    // Navigate to the directory report with specific divisions
    await page.goto('/persons/directory_report/?divisionSelector=0&divisionSelector=1&divisionSelector=2&divisionSelector=3&divisionSelector=5&divisionSelector=6');
    
    // Wait for the body to be fully loaded
    await page.waitForSelector('body', { state: 'visible' });
    
    // Wait until "Isaac" or "Isaac" appears in the DOM
    await page.waitForFunction(() => document.body.innerText.includes('Isaac'));
    
    // Evaluate the page text to count how many times "Isaac" appears.
    const elementsWithIsaac = await page.evaluate(() => {
      const bodyText = document.body.innerText;
      const count = (bodyText.match(/Isaac/g) || []).length;
      return count;
    });

    console.log(`Found ${elementsWithIsaac} occurrences of "Isaac"`);
    
    // The test passes if Isaac appears at least twice (once in parents' family, once in his own family)
    expect(elementsWithIsaac).toBeGreaterThanOrEqual(2);
  });
});
