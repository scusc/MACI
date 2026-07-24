import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCREENSHOT_DIR = '/Users/saichandsunkara/.gemini/antigravity-ide/brain/d7223e51-d85a-4d1d-817a-5b0c5048809a/screenshots';

test.describe('Rally Pilot Customer End-to-End Testing', () => {
  test.setTimeout(120000);

  test('Complete Pilot Customer Journey End-to-End', async ({ page }) => {
    // Step 1: Authentication / Registration
    await page.goto('/register');
    await page.waitForSelector('.auth-title', { timeout: 15000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_register_page.png') });

    await page.goto('/login');
    await page.waitForSelector('input[type="email"]');
    await page.fill('input[type="email"]', 'pilot_customer@rally.app');
    await page.fill('input[type="password"]', 'SecurePassword123!');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_login_form.png') });
    await page.click('button[type="submit"]');

    // Step 2: AI Psychometric Calibration Quiz
    await page.goto('/quiz');
    await page.waitForSelector('.quiz-card');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_psychometric_quiz_step1.png') });

    // Progress through quiz
    await page.click('.btn-primary'); // step 1 -> 2
    await page.click('.btn-primary'); // step 2 -> 3
    await page.click('.btn-primary'); // step 3 -> 4
    await page.click('.btn-primary'); // step 4 -> 5
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_psychometric_quiz_step5.png') });
    await page.click('.btn-primary'); // complete quiz
    await page.waitForTimeout(1500);

    // Step 3: Swipe Feed & Shielded Profiles
    await page.goto('/feed');
    await page.waitForSelector('.swipe-deck', { timeout: 15000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_swipe_feed.png') });
    await page.click('.like-btn');
    await page.waitForTimeout(500);

    // Step 4: Local Micro-Commitments & Escrow PIN Check-In
    await page.goto('/meetups');
    await page.waitForSelector('.meetup-cards');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_local_meetups_list.png') });

    await page.click('.btn-checkin');
    await page.waitForSelector('.modal');
    await page.fill('input[placeholder="e.g. 4921"]', '4921');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_meetup_pin_modal.png') });

    await page.click('.btn-confirm');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_meetup_pin_verified.png') });

    // Step 5: Pod Barter & Skill-Swapping Economy
    await page.goto('/skills');
    await page.waitForSelector('.skills-grid');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_skill_swap_offers.png') });

    await page.fill('input[name="title"]', '4K Aerial Drone Cinematography');
    await page.fill('textarea[name="description"]', 'Will shoot 4K aerial video of villa & excursions for the pod.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_skill_offer_form.png') });
    await page.click('.btn-submit');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_skill_offer_added.png') });

    // Step 6: Trust Passport Subscription Upgrade ($9.99/mo)
    await page.goto('/subscription');
    await page.waitForSelector('.pricing-cards');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_trust_passport_pricing.png') });

    await page.click('.btn-upgrade');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_trust_passport_active.png') });

    // Step 7: Live Group Chat & Mutual Handshake Reveal
    await page.goto('/chat/demo-pool-123');
    await page.waitForSelector('.chat-container');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '14_chat_shielded_mode.png') });

    await page.fill('textarea.chat-textarea', 'Hey everyone! Super excited for Bali. I just offered my drone footage skill.');
    await page.click('.send-btn');
    await page.waitForTimeout(500);

    await page.click('.btn-handshake');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '15_chat_identity_unmasked.png') });

    // Step 8: Pool Dashboard
    await page.goto('/pools');
    await page.waitForSelector('h2', { timeout: 5000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '16_pool_dashboard.png') });
  });
});
