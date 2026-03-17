#!/usr/bin/env node
import { mkdir, readFile, readdir, rename, rm } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { chromium } from "playwright";

function parseArgs(argv) {
  const options = {
    baseUrl: "http://127.0.0.1:8787",
    outputDir: "../../images/launch",
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--") {
      continue;
    }
    if (arg === "--manifest") {
      options.manifestPath = argv[++index];
    } else if (arg === "--workspace") {
      options.workspace = argv[++index];
    } else if (arg === "--base-url") {
      options.baseUrl = argv[++index];
    } else if (arg === "--output-dir") {
      options.outputDir = argv[++index];
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!options.manifestPath) {
    throw new Error("--manifest is required");
  }
  return options;
}

function consoleUrl(baseUrl, routePath, workspace) {
  const url = new URL(`/console/${routePath}`, baseUrl);
  url.searchParams.set("workspace", workspace);
  return url.toString();
}

async function capture(page, outputPath, width, height) {
  await page.setViewportSize({ width, height });
  await page.screenshot({ path: outputPath, fullPage: true });
}

async function main() {
  const options = parseArgs(process.argv);
  const manifest = JSON.parse(await readFile(options.manifestPath, "utf8"));
  const workspace = options.workspace ?? manifest.workspace;
  const outputDir = path.resolve(options.outputDir);
  const videoDir = path.join(outputDir, "video-temp");
  await mkdir(outputDir, { recursive: true });
  await mkdir(videoDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1024 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 1024 } },
  });
  const page = await context.newPage();

  await page.goto(consoleUrl(options.baseUrl, "", workspace), { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await capture(page, path.join(outputDir, "console-home.png"), 1440, 1080);

  await page.goto(consoleUrl(options.baseUrl, "inbox", workspace), { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await capture(page, path.join(outputDir, "console-inbox.png"), 1440, 1080);

  await page.goto(consoleUrl(options.baseUrl, "runs", workspace), { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await capture(page, path.join(outputDir, "console-runs.png"), 1440, 1200);

  await page.goto(
    consoleUrl(options.baseUrl, `runs/${manifest.showcase_run_id}`, workspace),
    { waitUntil: "networkidle" },
  );
  await page.waitForTimeout(1500);
  await capture(page, path.join(outputDir, "console-run-detail.png"), 1440, 2200);

  await context.close();
  await browser.close();

  const videoFiles = await readdir(videoDir);
  const firstVideo = videoFiles.find((entry) => entry.endsWith(".webm"));
  if (!firstVideo) {
    await rm(videoDir, { recursive: true, force: true });
    throw new Error(`Playwright did not produce a .webm capture in ${videoDir}`);
  }
  await rename(
    path.join(videoDir, firstVideo),
    path.join(outputDir, "observe-and-steer-demo.webm"),
  );
  await rm(videoDir, { recursive: true, force: true });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
