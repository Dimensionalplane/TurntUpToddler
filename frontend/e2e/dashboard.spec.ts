import { test, expect } from '@playwright/test';

test('verify dashboard single page layout', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/home/jules/verification/new-dashboard.png', fullPage: true });
});
