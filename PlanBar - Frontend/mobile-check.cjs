const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const VIEWPORT = { width: 375, height: 667 }; // iPhone SE3

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

async function main() {
  const browser = await chromium.launch({ headless: true });
  let server;
  const root = process.cwd();

  try {
    server = http.createServer((req, res) => {
      let filePath = path.join(root, 'dist', req.url === '/' ? 'index.html' : req.url.split('?')[0]);
      const ext = path.extname(filePath);
      const contentType = mimeTypes[ext] || 'application/octet-stream';
      try {
        const content = fs.readFileSync(filePath);
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      } catch {
        try {
          const content = fs.readFileSync(path.join(root, 'dist', 'index.html'));
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(content);
        } catch {
          res.writeHead(404);
          res.end('Not found');
        }
      }
    });

    await new Promise(resolve => server.listen(9877, resolve));
    console.log('Static server on http://localhost:9877\n');
    console.log('Checking frontend at iPhone SE3 (375x667)...\n');

    const indexHtml = fs.readFileSync(path.join(root, 'index.html'), 'utf-8');
    const hasViewport = indexHtml.includes('name="viewport"') || indexHtml.includes("name='viewport'");
    console.log(`${hasViewport ? '✅' : '❌'} Viewport meta tag: ${hasViewport}`);

    const loginPage = await browser.newPage();
    await loginPage.setViewportSize(VIEWPORT);
    await loginPage.goto('http://localhost:9877/', { waitUntil: 'networkidle', timeout: 15000 });
    await loginPage.waitForTimeout(1000);

    const loginResult = await loginPage.evaluate(() => {
      const w = document.documentElement.scrollWidth;
      const v = window.innerWidth;
      const hasOverflow = w > v + 2;
      return { overflow: hasOverflow, docWidth: w, viewport: v };
    });
    console.log(`${loginResult.overflow ? '❌' : '✅'} Login page (${loginResult.docWidth}px in ${loginResult.viewport}px viewport)`);
    await loginPage.screenshot({ path: path.join(root, '/tmp/mobile-login.png'), fullPath: false });
    await loginPage.close();

    // Check source files for non-responsive flex-between patterns
    console.log('\n--- Responsive class audit ---');
    const pageFiles = fs.readdirSync(path.join(root, 'src/app/pages'));
    let issues = 0;
    for (const file of pageFiles) {
      if (!file.endsWith('.tsx') && !file.endsWith('.ts')) continue;
      const content = fs.readFileSync(path.join(root, 'src/app/pages', file), 'utf-8');
      const lines = content.split('\n');
      lines.forEach((line, i) => {
        const trimmed = line.trim();
        if (trimmed.includes('flex justify-between items-center') &&
            !trimmed.includes('flex-col') &&
            !trimmed.includes('sm:') &&
            !trimmed.includes('Loading') &&
            !trimmed.includes('loading')) {
          console.log(`❌ ${file}:${i+1} - ${trimmed}`);
          issues++;
        }
      });
    }

    if (issues === 0) {
      console.log('✅ All flex-between headers are responsive');
    }

  } finally {
    if (server) server.close();
    await browser.close();
  }

  process.exit(0);
}

main().catch(e => { console.error(e); process.exit(1); });
