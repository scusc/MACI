import { test, expect, Page } from '@playwright/test';

let screenshotCount = 0;

async function snap(page: Page, name: string) {
  screenshotCount++;
  const padded = String(screenshotCount).padStart(2, '0');
  await page.screenshot({ path: `e2e-screenshots/snap_${padded}_${name}.png`, fullPage: true });
}

test.describe('Massive Deep UI QA Blitz', () => {
  test.setTimeout(300000); 

  test('exhaustive walk through all pages and features', async ({ browser, request }) => {
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

    // 1. Landing / Login Page
    await page.goto('/login');
    await snap(page, 'login_page_load');

    // Invalid login attempt
    await page.fill('input[type="email"]', 'wrong@example.com');
    await snap(page, 'login_typing_invalid');
    await page.click('button[type="submit"]');
    await snap(page, 'login_invalid_submitted');
    
    // Valid login
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[type="password"]', 'SecurePassword123!');
    await snap(page, 'login_typing_valid');
    await page.click('button[type="submit"]');

    // 2. Feed Page
    await page.waitForURL('**/feed', { timeout: 15000 }).catch(() => {});
    await snap(page, 'feed_page_load');
    
    // Swipe left
    for(let i=0; i<2; i++) {
        const dislikeBtn = page.locator('.dislike-btn');
        if (await dislikeBtn.isVisible()) {
            await dislikeBtn.click();
            await page.waitForTimeout(500); 
            await snap(page, `feed_swipe_left_${i}`);
        }
    }
    
    // Swipe right to trigger pool creation
    for(let i=0; i<3; i++) {
        const likeBtn = page.locator('.like-btn');
        if (await likeBtn.isVisible()) {
            await likeBtn.click();
            await page.waitForTimeout(500);
            await snap(page, `feed_swipe_right_${i}`);
        }
    }

    // 3. Pool Dashboard
    const poolsLink = page.locator('a[href="/pools"]');
    if (await poolsLink.isVisible()) {
        await poolsLink.click();
    } else {
        await page.goto('/pools');
    }
    await page.waitForURL('**/pools');
    await snap(page, 'pools_dashboard_load');
    
    // View active pools
    const poolCards = page.locator('.pool-card');
    if (await poolCards.count() > 0) {
        await snap(page, 'pools_dashboard_has_pools');
        await poolCards.first().hover();
        await snap(page, 'pools_dashboard_card_hover');
    }

    // 4. Host Dashboard
    const hostLink = page.locator('a[href="/host"]');
    if (await hostLink.isVisible()) {
        await hostLink.click();
    } else {
        await page.goto('/host');
    }
    await snap(page, 'host_dashboard_load');

    // 5. Chat & AI
    await page.goto('/chat/demo-pool-123');
    await snap(page, 'chat_page_load');
    
    // Typing
    await page.fill('textarea.chat-textarea', 'Hey everyone, I want to book the master bedroom!');
    await snap(page, 'chat_typing_regular');
    await page.click('.send-btn');
    await page.waitForTimeout(1000);
    await snap(page, 'chat_sent_regular');
    
    // Trigger AI Swarm
    await page.fill('textarea.chat-textarea', '@slice what is the flight cost estimate for 4 people to Bali?');
    await snap(page, 'chat_typing_ai');
    await page.click('.send-btn');
    await snap(page, 'chat_sent_ai');
    
    // Wait for AI response
    const aiMessage = page.locator('.ai-message').first();
    try {
        await expect(aiMessage).toBeVisible({ timeout: 60000 });
        await snap(page, 'chat_ai_responded');
        
        await aiMessage.hover();
        await snap(page, 'chat_ai_hover');
    } catch (e) {
        console.log("AI response took too long or failed", e);
        await snap(page, 'chat_ai_timeout');
    }

    // Done
    await snap(page, 'final_state');
    await context.close();
  });
});
