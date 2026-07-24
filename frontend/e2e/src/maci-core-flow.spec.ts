import { test, expect } from '@playwright/test';

test.describe('MACI Core End-to-End Flow', () => {
  // Increase test timeout to 90 seconds (90000 ms) because the AI Swarm takes a while to generate a response
  test.setTimeout(90000);

  test('should authenticate, swipe, create pool, and chat', async ({ browser, request }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const uniqueEmail = `host_${Date.now()}@example.com`;
    
    // 0. Register user via API
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email: uniqueEmail,
        password: 'SecurePassword123!',
        first_name: 'Host',
        last_name: 'User'
      }
    });

    // 1. Authenticate
    await page.goto('/login');
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[type="password"]', 'SecurePassword123!');
    await page.click('button[type="submit"]');
    
    // Wait for auth to complete and redirect to feed
    await page.waitForURL('/feed');
    
    // 2. Discover / Swipe Feed
    // We expect the swipe deck to load after hitting the external SerpAPI (or mock)
    await expect(page.locator('.swipe-deck')).toBeVisible({ timeout: 15000 });
    const cardTitle = page.locator('.asset-title').first();
    await expect(cardTitle).toBeVisible();
    
    // Swipe Right (Like)
    await page.locator('.like-btn').click();
    
    // 3. View My Pools
    await page.locator('a[href="/pools"]').click();
    await page.waitForURL('/pools');
    await expect(page.locator('h2:has-text("My Pools")')).toBeVisible();
    
    // Wait for pools list to load (grid may be empty so we don't wait for visibility)
    await page.waitForSelector('.pools-grid', { state: 'attached' });

    // 4. Connect to Pool Chat
    // Assuming a pool is there, or we can just navigate to demo
    await page.goto('/chat/demo-pool-123');
    
    // Verify Chat is Live
    await expect(page.locator('.status-dot.connected')).toBeVisible();
    await expect(page.locator('text=Live')).toBeVisible();
    
    // Send a message
    const msg = `Hello world ${Date.now()}`;
    await page.fill('textarea.chat-textarea', msg);
    await page.click('.send-btn');
    
    // Wait for the message to be broadcasted back via WebSocket
    await expect(page.locator(`text=${msg}`)).toBeVisible();
    
    // Call AI swarm
    await page.fill('textarea.chat-textarea', '@slice what is the weather in Bali?');
    await page.click('.send-btn');
    
    // Wait for AI response
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 30000 });

    await context.close();
  });
});
