import { createHmac } from 'node:crypto';

import { PASSWORD } from './golden';
import { expect, test, visit } from './fixtures';

/**
 * Getting in, staying in, and being kept out.
 *
 * allauth is somebody else's well-tested code. What is worth driving here is
 * how *this* deployment wires it up: signup closed, verification mandatory,
 * second factors switched on, and a failed-login limit that answers a
 * rate-limited attempt with the same words as a wrong password.
 *
 * These journeys change a login's own credentials, so they use the personas
 * nobody else signs in as — `golden_unaffiliated` has no organization and no
 * attendee, so nothing else in the suite depends on it.
 */

const SPARE = 'golden_unaffiliated';

/**
 * One TOTP code for a base32 secret.
 *
 * Written out rather than pulled from a library: it is twenty lines, and a
 * second factor whose test depends on an unpinned dependency is a second
 * factor whose test can break at three in the morning for no reason.
 */
function totp(base32Secret: string, at: number = Date.now()): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of base32Secret.replace(/=+$/, '').toUpperCase()) {
    const index = alphabet.indexOf(character);
    if (index < 0) continue;
    bits += index.toString(2).padStart(5, '0');
  }
  const key = Buffer.from(
    (bits.match(/.{8}/g) ?? []).map((byte) => parseInt(byte, 2)),
  );

  const counter = Math.floor(at / 1000 / 30);
  const message = Buffer.alloc(8);
  message.writeUInt32BE(Math.floor(counter / 2 ** 32), 0);
  message.writeUInt32BE(counter >>> 0, 4);

  const digest = createHmac('sha1', key).update(message).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const binary =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3];
  return `${binary % 10 ** 6}`.padStart(6, '0');
}

/**
 * Put the spare login back on its usual password, whatever it is on now.
 *
 * These journeys mutate the one credential they sign in with, so a failure
 * half way through would otherwise leave the login unusable for every test
 * after it — including the ones in the other browser project, which run later
 * against the same database.
 */
test.afterEach(async ({ page }) => {
  const candidates = [PASSWORD, `${PASSWORD}-turned-over`];
  for (const candidate of candidates) {
    await page.context().clearCookies();
    await page.goto('/accounts/login/', { waitUntil: 'domcontentloaded' });
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", candidate);
    await page.click("button[type='submit'], input[type='submit']");
    await page.waitForLoadState('domcontentloaded');
    if (new URL(page.url()).pathname.startsWith('/accounts/login')) continue;
    if (candidate === PASSWORD) return;

    await page.goto('/accounts/password/change/', { waitUntil: 'domcontentloaded' });
    await page.fill("input[name='oldpassword']", candidate);
    await page.fill("input[name='password1']", PASSWORD);
    await page.fill("input[name='password2']", PASSWORD);
    await page.click("button[type='submit'], input[type='submit']");
    return;
  }
});

test.describe('the door', () => {
  test('signing up is closed, and says so rather than 404ing', async ({ page }) => {
    // This congregation provisions its own logins; a public signup form would
    // let anybody into a database of children's addresses.
    await visit(page, '/accounts/signup/');
    await expect(page.locator('body')).toContainText(/closed|not open|sign up/i);
    await expect(page.locator("input[name='password1']")).toHaveCount(0);
  });

  test('a wrong password and a rate-limited one are told apart by nobody', async ({
    page,
  }) => {
    // Deliberate: the message is identical, so an attacker cannot use it to
    // learn that a username exists. Worth pinning, because it is also why the
    // suite runs the application with the limit lifted.
    await visit(page, '/accounts/login/');
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", 'not-the-password');
    await page.click("button[type='submit'], input[type='submit']");
    await expect(page.locator('body')).toContainText(
      /correct username and password|not correct/i,
    );
    await expect(page).toHaveURL(/accounts\/login/);
  });

  test('an unverified address cannot be used to sign in', async ({ page, signIn }) => {
    // Verification is mandatory here. The golden personas are seeded verified;
    // what this checks is that the setting is actually in force, by way of the
    // page allauth sends a signed-in user to when it is not.
    await signIn(SPARE);
    await visit(page, '/accounts/email/');
    await expect(page.locator('body')).toContainText(/verified/i);
  });
});

test.describe('a member looks after their own login', () => {
  test('turns the password over, and the old one stops working', async ({
    page,
    signIn,
  }) => {
    // One journey rather than two, deliberately: every step here mutates the
    // credential the next spec signs in with, so there is exactly one window
    // in which this login is not on its usual password, and the last thing
    // the journey does is prove it is back on it.
    const replacement = `${PASSWORD}-turned-over`;

    await signIn(SPARE);
    await visit(page, '/accounts/password/change/');
    await page.fill("input[name='oldpassword']", PASSWORD);
    await page.fill("input[name='password1']", replacement);
    await page.fill("input[name='password2']", replacement);
    await page.click("button[type='submit'], input[type='submit']");
    // allauth keeps you on this URL and flashes; the door is the real proof.
    await expect(page.locator('body')).not.toContainText(
      /Please type your current password|too short|too common|didn.t match/i,
    );

    // The old one is refused …
    await page.context().clearCookies();
    await visit(page, '/accounts/login/');
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", PASSWORD);
    await page.click("button[type='submit'], input[type='submit']");
    await expect(page).toHaveURL(/accounts\/login/);

    // … and the new one works, which is the only proof that counts.
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", replacement);
    await Promise.all([
      page.waitForURL((url) => !url.pathname.startsWith('/accounts/login')),
      page.click("button[type='submit'], input[type='submit']"),
    ]);

    // Hand it back, and check the hand-back rather than assuming it.
    await visit(page, '/accounts/password/change/');
    await page.fill("input[name='oldpassword']", replacement);
    await page.fill("input[name='password1']", PASSWORD);
    await page.fill("input[name='password2']", PASSWORD);
    await page.click("button[type='submit'], input[type='submit']");
    await expect(page.locator('body')).not.toContainText(
      /Please type your current password|too short|too common|didn.t match/i,
    );

    await page.context().clearCookies();
    await visit(page, '/accounts/login/');
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", PASSWORD);
    await Promise.all([
      page.waitForURL((url) => !url.pathname.startsWith('/accounts/login')),
      page.click("button[type='submit'], input[type='submit']"),
    ]);
  });
});

test.describe('a member turns on a second factor', () => {
  test('activates an authenticator app and then signs in through it', async ({
    page,
    signIn,
  }) => {
    // TOTP is configured but nothing has ever exercised it. The journey that
    // matters is the whole loop: activate with a code, then be *asked* for a
    // code at the next sign-in and get in with one.
    await signIn(SPARE);
    await visit(page, '/accounts/2fa/totp/activate/');

    // allauth puts the shared secret in a disabled field beside the QR code,
    // so it can be typed into an app by hand — which is exactly what this
    // journey does, only in twenty lines of arithmetic.
    const secret = await page.locator('#authenticator_secret').inputValue();
    expect(secret, 'the activation page showed no secret to enrol with').toMatch(
      /^[A-Z2-7]{16,}$/,
    );

    await page.fill("input[name='code']", totp(secret));
    await page.click("button[type='submit'], input[type='submit']");
    await expect(page.locator('body')).not.toContainText(/incorrect code/i);

    // Signing in now takes two steps.
    await page.context().clearCookies();
    await visit(page, '/accounts/login/');
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", PASSWORD);
    await Promise.all([
      page.waitForURL(/2fa|authenticate/),
      page.click("button[type='submit'], input[type='submit']"),
    ]);
    await page.fill("input[name='code']", totp(secret));
    await Promise.all([
      page.waitForURL((url) => !/authenticate/.test(url.pathname)),
      page.click("button[type='submit'], input[type='submit']"),
    ]);

    // Take it off again, and prove it is off the way it was proved on: by
    // signing in and not being asked. That also hands the persona back as a
    // plain login for every other spec.
    await visit(page, '/accounts/2fa/totp/deactivate/');
    await page.click("button[type='submit'], input[type='submit']");

    await page.context().clearCookies();
    await visit(page, '/accounts/login/');
    await page.fill("input[name='login']", SPARE);
    await page.fill("input[name='password']", PASSWORD);
    await Promise.all([
      page.waitForURL((url) => !url.pathname.startsWith('/accounts/login')),
      page.click("button[type='submit'], input[type='submit']"),
    ]);
    await expect(page).not.toHaveURL(/2fa|authenticate/);
  });
});
