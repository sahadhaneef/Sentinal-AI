// No intercepted API responses: this browser consumes the isolated running FastAPI database.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const [base, port] = process.argv.slice(2);
const mode = process.argv[4] ?? "persisted";
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+\/api\/v1$/);
assert.match(port, /^\d+$/);
const uiBase = `http://127.0.0.1:${port}`;
const frontend = fileURLToPath(new URL("../../frontend/", import.meta.url));
const vite = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "--host",
    "127.0.0.1",
    "--port",
    port,
    "--strictPort",
  ],
  {
    cwd: frontend,
    env: { ...process.env, VITE_DATA_SOURCE: "api", VITE_API_BASE_URL: base },
    stdio: "ignore",
    windowsHide: true,
  },
);
let browser;
try {
  const deadline = Date.now() + 15000;
  while (true) {
    assert.equal(vite.exitCode, null, "Vite exited during startup");
    try {
      if ((await fetch(uiBase)).ok) break;
    } catch {}
    assert.ok(Date.now() < deadline, "Vite did not become ready");
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  browser = await chromium.launch();
  const page = await browser.newPage({ reducedMotion: "reduce" });
  page.setDefaultTimeout(10000);
  const errors = [],
    actual = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.url().startsWith(base)) actual.push(response.url());
  });
  await page.goto(uiBase + "/dashboard");
  await page
    .getByRole("complementary")
    .getByText("Read-only workspace", { exact: true })
    .waitFor();
  if (mode === "unavailable") {
    await page
      .getByText("Backend unavailable.", { exact: false })
      .first()
      .waitFor();
    assert.equal(
      await page.getByText("Demo reviewer", { exact: true }).count(),
      0,
    );
    assert.equal(actual.length, 0);
  } else if (mode === "empty") {
    await page
      .locator(".kpi")
      .filter({ hasText: "Total incidents" })
      .getByText("00", { exact: true })
      .waitFor();
    await page.goto(uiBase + "/applications");
    await page
      .getByText("No results match your filters.", { exact: true })
      .waitFor();
    assert.equal(await page.locator(".app-card-header").count(), 0);
    await page.goto(uiBase + "/incidents");
    await page
      .getByText("No results match your filters.", { exact: true })
      .waitFor();
    assert.equal(await page.locator(".incident-row").count(), 0);
  } else {
    await page
      .getByRole("heading", { name: "Fixture app", exact: true })
      .waitFor();
    await page.goto(uiBase + "/applications/app_demo");
    const start = page.getByRole("button", {
      name: "Start monitoring",
      exact: true,
    });
    await start.waitFor();
    assert.equal(await start.isDisabled(), true);
    await page.getByText("Read-only API phase.", { exact: false }).waitFor();
    const listing = await (await page.request.get(base + "/incidents")).json();
    const id = listing.data.items[0].id;
    await page.goto(uiBase + `/incidents/${id}`);
    await page
      .getByText("Synthetic persistence fixture", { exact: false })
      .first()
      .waitFor();
    await page
      .getByText("Read-only backend phase.", { exact: false })
      .first()
      .waitFor();
    assert.equal(
      await page
        .getByRole("button", { name: "Approve candidate", exact: true })
        .isDisabled(),
      true,
    );
    await page.goto(uiBase + "/agents/diagnosis");
    await page
      .getByRole("heading", { name: "Diagnosis Agent", exact: true })
      .waitFor();
    await page.goto(uiBase + "/history");
    await page
      .getByRole("link", { name: /Synthetic persistence fixture/ })
      .waitFor();
    await page.goto(uiBase + "/repair-testing");
    await page
      .getByRole("heading", { name: "Repair & Testing", exact: true })
      .waitFor();
    await page.goto(uiBase + "/approval-recovery");
    await page
      .getByRole("heading", { name: "Approval & Recovery", exact: true })
      .waitFor();
    await page.goto(uiBase + "/settings");
    await page.getByText("Read-only database API.", { exact: false }).waitFor();
  }
  assert.deepEqual(errors, []);
  if (mode !== "unavailable")
    assert.ok(actual.some((url) => url.includes("/dashboard/summary")));
  if (mode === "persisted") {
    assert.ok(actual.some((url) => url.includes("/incidents/")));
    assert.ok(actual.some((url) => url.includes("/agents/diagnosis")));
  }
  console.log(
    JSON.stringify({ live_browser: "passed", interception: false, mode }),
  );
} finally {
  await browser?.close();
  vite.kill();
  await new Promise((resolve) => {
    if (vite.exitCode !== null) resolve();
    else vite.once("exit", resolve);
  });
}
