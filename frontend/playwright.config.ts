import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir:'./tests', timeout:60_000, fullyParallel:false, workers:1,
  outputDir:'../tmp/playwright-results', reporter:'list',
  use:{baseURL:'http://127.0.0.1:5173',trace:'off',screenshot:'off'},
  projects:[{name:'desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
  webServer:[
    {command:'uv run --project ../backend --directory ../backend uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log',env:{PUBLIC_ORIGIN:'http://127.0.0.1:5173'},url:'http://127.0.0.1:8000/healthz',reuseExistingServer:!process.env.CI,timeout:60_000},
    {command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:!process.env.CI,timeout:60_000}
  ]
});
