import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should display login page and validate inputs', async ({ page }) => {
    await page.goto('/login');
    
    // Check Enterprise Minimalist styling is applied
    const title = page.locator('.auth-title');
    await expect(title).toHaveText('Sign in to Slice');
    await expect(title).toHaveCSS('color', 'rgb(17, 24, 39)'); // var(--color-gray-900)

    // Attempt login with invalid credentials
    await page.fill('input[type="email"]', 'invalid-email');
    await page.click('button[type="submit"]');

    // Email field should be marked as invalid by Signal Forms
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toHaveClass(/invalid/);
  });
});
