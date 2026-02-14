import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

// Login to Grafana
await page.goto('http://localhost:3000/login');
await page.fill('input[name="user"]', 'admin');
await page.fill('input[name="password"]', 'admin');
await page.click('button[type="submit"]');
await page.waitForTimeout(2000);

// Navigate to the dashboard
await page.goto('http://localhost:3000/d/portfolio-overview/portfolio-overview?orgId=1&from=now-1h&to=now');
await page.waitForTimeout(5000);

await page.screenshot({ path: 'grafana-dashboard.png', fullPage: true });
console.log('Screenshot saved to grafana-dashboard.png');

await browser.close();
