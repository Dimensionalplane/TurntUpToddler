import { test, expect } from '@playwright/test';

test('verify tooltips render correctly in UI', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  await page.waitForTimeout(1000);

  // Verify GlobalSettings tooltips
  const stylePromptTitle = page.locator('span[title="Describe the musical genre or mood for the generated song (e.g., \'Deep House, upbeat\'). This is passed to MusicGen/Replicate."]');
  await expect(stylePromptTitle).toBeVisible();

  const kidsModeTitle = page.locator('span[title="Enforces child-safe metadata filtering, alters the styling prompt to be playful/nursery-rhyme focused, and enables COPPA-compliant YouTube uploads."]');
  await expect(kidsModeTitle).toBeVisible();

  // Verify FileUploader tooltips
  const generateHymnTitle = page.locator('span[title="Starts the automated pipeline for the uploaded file using current sidebar settings."]');
  await expect(generateHymnTitle).toBeVisible();
});
