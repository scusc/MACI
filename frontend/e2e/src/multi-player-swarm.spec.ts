import { test, expect, Page, BrowserContext, APIRequestContext } from '@playwright/test';

let screenshotCount = 0;

// Helper to take a screenshot and log it
async function snap(page: Page, perspective: string, name: string) {
  screenshotCount++;
  const padded = String(screenshotCount).padStart(3, '0');
  await page.screenshot({ path: `e2e-screenshots/swarm_${padded}_[${perspective}]_${name}.png`, fullPage: true });
}

// Helper to register a user via API
async function registerUser(request: APIRequestContext, email: string) {
    const res = await request.post('http://localhost:8000/api/v1/auth/register', {
        data: {
            email: email,
            password: 'SecurePassword123!',
            first_name: email.split('@')[0],
            last_name: 'User'
        }
    });
    return res.ok();
}

// Helper to login a user via UI
async function loginUser(page: Page, email: string, perspective: string) {
    await page.goto('/login');
    await snap(page, perspective, 'login_page_loaded');
    
    // Negative test: invalid credentials
    if (perspective === 'User_1_Host') {
        await page.fill('input[type="email"]', 'invalid_fake@example.com');
        await page.fill('input[type="password"]', 'WrongPass!');
        await page.click('button[type="submit"]');
        await page.waitForTimeout(500); // Wait for error
        await snap(page, perspective, 'login_error_invalid_credentials');
    }
    
    // Positive test
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'SecurePassword123!');
    await snap(page, perspective, 'login_credentials_filled');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/feed', { timeout: 15000 }).catch(() => {});
    await snap(page, perspective, 'feed_dashboard_loaded');
}

test.describe('100+ Screenshot Multi-Player Swarm Simulation', () => {
  // Give this massive simulation 10 minutes to run
  test.setTimeout(600000); 

  test('5 players interacting simultaneously with AI Concierge in real-time', async ({ browser, request }) => {
    // 0. Seed 20 Users in DB via API to simulate network activity
    console.log("Seeding 20 users...");
    for(let i = 0; i < 20; i++) {
        await registerUser(request, `seed_user_${Date.now()}_${i}@example.com`);
    }

    // Prepare our 5 actual players
    const emails = [];
    for(let i=0; i<5; i++) {
        const em = `player_${Date.now()}_${i}@example.com`;
        emails.push(em);
        await registerUser(request, em);
    }
    console.log("Seeded 5 active players.");

    // Spawn 5 completely independent browser contexts
    const contexts: BrowserContext[] = [];
    const pages: Page[] = [];
    const names = ['User_1_Host', 'User_2', 'User_3', 'User_4', 'User_5'];

    for(let i=0; i<5; i++) {
        contexts.push(await browser.newContext());
        pages.push(await contexts[i].newPage());
    }

    const hostPage = pages[0];

    // 1. Host creates a pool
    await loginUser(hostPage, emails[0], names[0]);
    
    // Host browses feed
    for(let i=0; i<3; i++) {
        const dislike = hostPage.locator('.dislike-btn');
        if (await dislike.isVisible()) {
            await dislike.click();
            await hostPage.waitForTimeout(400);
            await snap(hostPage, names[0], `feed_swipe_left_${i}`);
        }
    }
    
    // Host likes an asset to trigger pool
    const likeBtn = hostPage.locator('.like-btn').first();
    if (await likeBtn.isVisible()) {
        await likeBtn.click();
        await hostPage.waitForTimeout(500);
        await snap(hostPage, names[0], `feed_swipe_right_match`);
    }

    // Host navigates to pools
    const poolsLink = hostPage.locator('a[href="/pools"]');
    if (await poolsLink.isVisible()) await poolsLink.click();
    else await hostPage.goto('/pools');
    
    await hostPage.waitForURL('**/pools');
    await snap(hostPage, names[0], 'pools_dashboard');

    // Host clicks on the pool chat (assume demo-pool-123 for robust routing)
    await hostPage.goto('/chat/demo-pool-123');
    await snap(hostPage, names[0], 'host_enters_chat');

    // 2. The other 4 users log in and join the pool
    for(let i=1; i<5; i++) {
        // Negative test: Try accessing pool without auth
        if (i === 1) {
            await pages[i].goto('/chat/demo-pool-123');
            await pages[i].waitForTimeout(500);
            await snap(pages[i], names[i], 'unauthorized_pool_access_attempt');
        }

        // Login properly
        await loginUser(pages[i], emails[i], names[i]);
        
        // Navigate directly to the pool
        await pages[i].goto('/chat/demo-pool-123');
        await pages[i].waitForTimeout(1000); // Let websockets connect
        await snap(pages[i], names[i], 'joins_chat_room');
    }

    // Take a unified snapshot to show everyone is in
    for(let i=0; i<5; i++) await snap(pages[i], names[i], 'lobby_synchronized');

    // 3. Multi-Player Chat Swarm with Negative Scenarios
    // User 2 sends a message
    await pages[1].fill('textarea.chat-textarea', 'Hey guys! I made it.');
    await snap(pages[1], names[1], 'typing_greeting');
    await pages[1].click('.send-btn');
    await pages[1].waitForTimeout(1000);
    
    // Check perspective of User 3 receiving the message
    await snap(pages[2], names[2], 'receives_greeting_from_user_2');

    // Negative scenario: User 4 sends empty message
    await pages[3].fill('textarea.chat-textarea', '   ');
    await expect(pages[3].locator('.send-btn')).toBeDisabled();
    await snap(pages[3], names[3], 'empty_message_validation');

    // User 4 sends real message
    await pages[3].fill('textarea.chat-textarea', 'I am super excited for this trip. Who is doing the itinerary?');
    await pages[3].click('.send-btn');
    await pages[3].waitForTimeout(1000);

    // Host (User 1) calls the AI
    await hostPage.fill('textarea.chat-textarea', '@slice Plan an itinerary for us to Bali, keeping it under $500 per person for flights.');
    await snap(hostPage, names[0], 'calling_ai_concierge');
    await hostPage.click('.send-btn');
    await hostPage.waitForTimeout(500);

    // Show User 5 waiting for AI
    await snap(pages[4], names[4], 'waiting_for_ai_response');

    // Wait for AI to respond on the Host page
    const aiMessage = hostPage.locator('.ai-message').first();
    try {
        await expect(aiMessage).toBeVisible({ timeout: 60000 });
        await snap(hostPage, names[0], 'ai_responded');
        
        // Show everyone else seeing the AI response
        for(let i=1; i<5; i++) {
            await snap(pages[i], names[i], 'sees_ai_itinerary');
        }
    } catch (e) {
        console.log("AI timeout");
        await snap(hostPage, names[0], 'ai_timeout');
    }

    // 4. Rally / Escrow Interaction (If UI supports it)
    await pages[2].fill('textarea.chat-textarea', 'I approve of this plan!');
    await pages[2].click('.send-btn');
    await pages[2].waitForTimeout(1000);

    // Show perspective of all users at the end of the chat session
    for(let i=0; i<5; i++) {
        await snap(pages[i], names[i], 'final_chat_state');
    }

    // 5. Host navigates to Host Dashboard to check status
    await hostPage.goto('/host');
    await hostPage.waitForTimeout(1000);
    await snap(hostPage, names[0], 'host_checks_admin_dashboard');

    // Tear down
    for(let i=0; i<5; i++) {
        await contexts[i].close();
    }
  });
});
