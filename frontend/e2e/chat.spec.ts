import { test, expect } from '@playwright/test';

test.describe('Real-Time AI Swarm Chat', () => {
  test('should render chat UI and allow message submission', async ({ page, request }) => {
    const uniqueEmail = `test_${Date.now()}@slice.com`;
    // Register the user via API first so login succeeds
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email: uniqueEmail,
        password: 'SecurePassword123!',
        first_name: 'Test',
        last_name: 'User'
      }
    });

    // First, login to get a valid token
    await page.goto('/login');
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[type="password"]', 'SecurePassword123!');
    await page.click('button[type="submit"]');
    
    // Wait for redirect to feed to ensure token is stored
    await page.waitForURL('/feed');

    // Navigate to a demo pool chat
    await page.goto('/chat/demo-pool-123');
    
    // Verify header and connection status
    await expect(page.locator('.chat-header h2')).toHaveText('Pool Chat');
    
    // The connection dot should be visible
    const statusDot = page.locator('.status-dot');
    await expect(statusDot).toBeVisible();

    // Verify system welcome message is rendered
    await expect(page.locator('.system-message .message-content')).toContainText('Slice AI Concierge Swarm is listening');

    // Send a message
    const input = page.locator('.chat-textarea');
    await input.fill('Find us a luxury villa in Bali for next week.');
    
    const sendButton = page.locator('.send-btn');
    await expect(sendButton).not.toBeDisabled();
    await sendButton.click();

    // Verify the textarea is cleared after sending
    await expect(input).toHaveValue('');
  });
});
