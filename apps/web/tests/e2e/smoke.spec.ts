import { test, expect } from '@playwright/test';

test('app shell renders', async ({ page }) => {
  await page.goto('http://127.0.0.1:8888/import-jobs');
  await expect(page.getByText('Card Reader')).toBeVisible();
});