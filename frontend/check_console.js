const { chromium } = require('@playwright/test');
const { exec } = require('child_process');

(async () => {
  console.log('Starting frontend server...');
  const server = exec('npx nx serve frontend --port 4200', { cwd: '/Users/saichandsunkara/Documents/MACI/frontend' });
  
  // Wait a few seconds for server to start
  await new Promise(r => setTimeout(r, 10000));
  
  console.log('Launching browser...');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
  
  console.log('Navigating to http://localhost:4200...');
  try {
    await page.goto('http://localhost:4200', { waitUntil: 'networkidle', timeout: 15000 });
  } catch (e) {
    console.log('Navigation error:', e.message);
  }
  
  const content = await page.content();
  if (!content.includes('app-root')) {
    console.log('No app-root found in DOM');
  } else {
    console.log('app-root is present in DOM');
  }
  
  await browser.close();
  server.kill();
  console.log('Done.');
})();
