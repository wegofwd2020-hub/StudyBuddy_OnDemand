#!/usr/bin/env node
/**
 * Capture browser console logs during signin to debug form submission.
 *
 * Usage:
 *   npm install playwright
 *   node scripts/capture-signin-logs.js [URL] [email] [password]
 *
 * Examples:
 *   node scripts/capture-signin-logs.js http://localhost/signin student@demo.example.com DemoPass123
 *   node scripts/capture-signin-logs.js https://demo.usestudybuddy.com/signin test@example.com TestPass123
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function captureSigninLogs() {
  const url = process.argv[2] || 'http://localhost/signin';
  const email = process.argv[3] || 'student@demo.example.com';
  const password = process.argv[4] || 'DemoPass123';

  console.log(`\n📋 Capturing signin logs from: ${url}`);
  console.log(`📧 Email: ${email}`);
  console.log(`🔒 Password: ${'*'.repeat(password.length)}\n`);

  const logs = {
    console: [],
    network: [],
    errors: [],
    timestamp: new Date().toISOString(),
  };

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture console messages (log, error, warn, info)
  page.on('console', (msg) => {
    const logEntry = {
      type: msg.type(),
      text: msg.text(),
      location: msg.location(),
      args: msg.args().length,
      timestamp: new Date().toISOString(),
    };
    logs.console.push(logEntry);
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });

  // Capture network requests
  page.on('request', (request) => {
    const reqEntry = {
      method: request.method(),
      url: request.url(),
      postData: request.postData(),
      timestamp: new Date().toISOString(),
    };
    if (request.url().includes('/auth') || request.url().includes('/signin')) {
      logs.network.push(reqEntry);
      console.log(`[REQUEST] ${request.method()} ${request.url()}`);
    }
  });

  page.on('response', (response) => {
    const respEntry = {
      status: response.status(),
      url: response.url(),
      statusText: response.statusText(),
      timestamp: new Date().toISOString(),
    };
    if (response.url().includes('/auth') || response.url().includes('/signin')) {
      logs.network.push(respEntry);
      console.log(`[RESPONSE] ${response.status()} ${response.url()}`);
    }
  });

  // Capture uncaught errors
  page.on('pageerror', (err) => {
    const errEntry = {
      name: err.name,
      message: err.message,
      stack: err.stack,
      timestamp: new Date().toISOString(),
    };
    logs.errors.push(errEntry);
    console.log(`[ERROR] ${err.message}`);
  });

  try {
    console.log(`⏳ Navigating to signin page...\n`);
    await page.goto(url, { waitUntil: 'networkidle' });

    // Wait for form to be visible
    await page.waitForSelector('input[id="email"]', { timeout: 5000 });

    console.log(`✅ Signin page loaded. Filling form...\n`);

    // Fill email
    await page.fill('input[id="email"]', email);
    await page.waitForTimeout(300);

    // Fill password
    await page.fill('input[id="password"]', password);
    await page.waitForTimeout(300);

    console.log(`🖱️  Clicking Sign In button...\n`);

    // Click sign in button
    const submitButton = await page.$('button[type="submit"]');
    if (submitButton) {
      await submitButton.click();
    } else {
      console.error('❌ Submit button not found');
      logs.errors.push({
        name: 'ElementNotFound',
        message: 'Submit button not found on page',
        timestamp: new Date().toISOString(),
      });
    }

    // Wait for any response or error
    await page.waitForTimeout(3000);

    console.log(`\n⏸️  Waiting for responses...\n`);
    await page.waitForTimeout(2000);

  } catch (err) {
    console.error(`❌ Error during signin: ${err.message}`);
    logs.errors.push({
      name: err.name,
      message: err.message,
      stack: err.stack,
      timestamp: new Date().toISOString(),
    });
  }

  await browser.close();

  // Save logs to file
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `signin-logs-${timestamp}.json`;
  const filepath = path.join(process.cwd(), filename);

  fs.writeFileSync(filepath, JSON.stringify(logs, null, 2));

  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 Captured Logs Summary`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Console messages: ${logs.console.length}`);
  console.log(`Network requests: ${logs.network.length}`);
  console.log(`Errors: ${logs.errors.length}`);
  console.log(`\n💾 Full logs saved to: ${filepath}\n`);

  // Print key [universalLogin] logs
  const universalLoginLogs = logs.console.filter(l => l.text.includes('[universalLogin]'));
  if (universalLoginLogs.length > 0) {
    console.log(`🔍 [universalLogin] Logs Found:`);
    universalLoginLogs.forEach(log => {
      console.log(`  [${log.type}] ${log.text}`);
    });
  } else {
    console.log(`⚠️  No [universalLogin] logs found in console`);
  }

  // Print network logs
  if (logs.network.length > 0) {
    console.log(`\n🌐 Network Activity:`);
    logs.network.forEach(log => {
      if (log.method) {
        console.log(`  ${log.method} ${log.url}`);
      } else {
        console.log(`  ${log.status} ${log.url}`);
      }
    });
  } else {
    console.log(`\n⚠️  No network requests captured`);
  }

  // Print errors
  if (logs.errors.length > 0) {
    console.log(`\n❌ Errors:`);
    logs.errors.forEach(err => {
      console.log(`  ${err.name}: ${err.message}`);
    });
  }

  console.log(`\n${'='.repeat(60)}\n`);
}

captureSigninLogs().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
