import { test as base, expect, Page } from '@playwright/test';

export interface TestOptions {
  ignoredErrorPatterns: RegExp[];
}

export const test = base.extend<
  TestOptions & {
    browserErrors: string[];
  }
>({
  ignoredErrorPatterns: [[], { option: true }],

  browserErrors: [
    async ({ page, ignoredErrorPatterns }, use) => {
      const errors: string[] = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const text = msg.text();
          if (!ignoredErrorPatterns.some((pattern) => pattern.test(text))) {
            errors.push(`[Console Error] ${text}`);
          }
        }
      });

      page.on('pageerror', (err) => {
        const text = err.message;
        if (!ignoredErrorPatterns.some((pattern) => pattern.test(text))) {
          errors.push(`[Uncaught PageError] ${text}`);
        }
      });

      await use(errors);

      expect(
        errors,
        `Expected no browser console errors or page exceptions, but found:\n${errors.join('\n')}`,
      ).toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
export type { Page };
