#!/usr/bin/env node
/**
 * Google Gemini Image Generation for Article Images
 *
 * Uses Vertex AI with Google Cloud credentials for image generation.
 * Models: gemini-2.5-flash-image (primary), gemini-3-pro-image-preview (fallback)
 *
 * Required environment variables:
 *   GOOGLE_CLOUD_PROJECT - Your Google Cloud project ID
 *   GOOGLE_CLOUD_LOCATION - Region (default: us-central1)
 *
 * Or for Gemini Developer API:
 *   GOOGLE_API_KEY - Your Gemini API key
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DEFAULT_PROMPTS_GLOB = 'articles/prompts/*.md';
const DEFAULT_OUTPUT_ROOT = 'articles/images';
const DEFAULT_IMAGES_PER_PROMPT = 1;
const DEFAULT_MAX_PROMPTS = 1000;
const DEFAULT_MAX_IMAGES = 1000;
const DEFAULT_SLEEP_MIN_MS = 500;
const DEFAULT_SLEEP_MAX_MS = 1500;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_RETRY_BASE_MS = 1000;
const DEFAULT_PARALLEL = 1;

// Gemini models for image generation
const PRIMARY_MODEL = 'gemini-3-pro-image-preview';
const FALLBACK_MODEL = 'gemini-2.5-flash-image';

const IMAGE_MODELS = [
  { id: PRIMARY_MODEL, name: 'Gemini 3 Pro Image' },
  { id: FALLBACK_MODEL, name: 'Gemini 2.5 Flash Image' },
];

// Aspect ratio to size mapping for Gemini
// Gemini uses aspect ratio strings directly
const ASPECT_RATIOS = {
  '16:9': '16:9',
  '3:2': '3:2',
  '4:3': '4:3',
  '9:16': '9:16',
  '2:3': '2:3',
  '3:4': '3:4',
  '1:1': '1:1',
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getEnvNumber(name, fallback) {
  const value = process.env[name];
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getEnvString(name, fallback) {
  return process.env[name] ?? fallback;
}

function getEnvBoolean(name, fallback) {
  const value = process.env[name];
  if (value === undefined || value === '') return fallback;
  const strValue = String(value).toLowerCase();
  return !['false', '0', 'no', 'off'].includes(strValue);
}

function normalizeNewlines(text) {
  return text.replace(/\r\n/g, '\n');
}

function extractGenerationNotes(content) {
  const match = content.match(/\n##\s+Generation Notes\b([\s\S]*)$/i);
  if (!match) return '';
  return match[1].trim();
}

function parsePromptSection(sectionText) {
  const promptMarker = '**Prompt:**';
  const captionMarker = '**Caption:**';
  const promptIndex = sectionText.indexOf(promptMarker);
  if (promptIndex === -1) {
    return { promptText: '', caption: '' };
  }

  const afterPrompt = sectionText.slice(promptIndex + promptMarker.length);
  const captionIndex = afterPrompt.indexOf(captionMarker);

  let promptText = '';
  let caption = '';

  if (captionIndex === -1) {
    promptText = afterPrompt.trim();
  } else {
    promptText = afterPrompt.slice(0, captionIndex).trim();
    caption = afterPrompt.slice(captionIndex + captionMarker.length).trim();
  }

  return { promptText, caption };
}

function selectAspectForIndex(index, generationNotes, options = {}) {
  const technicalAspect = options.technicalAspect ?? '4:3';
  const conceptualAspect = options.conceptualAspect ?? '16:9';
  const heroAspect = options.heroAspect ?? '16:9';

  if (index === 1) {
    return heroAspect;
  }

  const technicalSet = new Set([2, 6, 8]);
  const conceptualSet = new Set([3, 4, 5, 7]);

  if (technicalSet.has(index)) {
    return technicalAspect;
  }

  if (conceptualSet.has(index)) {
    return conceptualAspect;
  }

  const aspectMatch = generationNotes.match(/\b(\d+:\d+)\b/);
  if (aspectMatch) {
    return aspectMatch[1];
  }

  return '16:9';
}

function parsePromptFile(content, options = {}) {
  const normalized = normalizeNewlines(content);
  const generationNotes = extractGenerationNotes(normalized);
  const generationNotesIndex = normalized.search(/\n##\s+Generation Notes\b/i);
  const imageRegex = /^##\s+Image\s+(\d+):\s*(.+)$/gim;
  const images = [];
  const matches = [];

  let match;
  while ((match = imageRegex.exec(normalized)) !== null) {
    matches.push({
      index: Number(match[1]),
      title: match[2].trim(),
      start: match.index,
    });
  }

  for (let i = 0; i < matches.length; i += 1) {
    const current = matches[i];
    const next = matches[i + 1];
    let end = next ? next.start : normalized.length;
    if (generationNotesIndex !== -1 && generationNotesIndex < end && generationNotesIndex > current.start) {
      end = generationNotesIndex;
    }
    const sectionText = normalized.slice(current.start, end);
    const { promptText, caption } = parsePromptSection(sectionText);
    const aspect = selectAspectForIndex(current.index, generationNotes, options);
    images.push({
      index: current.index,
      title: current.title,
      promptText,
      caption,
      aspect,
    });
  }

  return {
    generationNotes,
    images,
  };
}

function slugFromFilename(filePath) {
  const base = path.basename(filePath, path.extname(filePath));
  return base.replace(/^\d+-/, '');
}

function hashPrompt({ prompt, model, aspect, imagesPerPrompt }) {
  const hash = crypto.createHash('sha256');
  hash.update(JSON.stringify({ prompt, model, aspect, imagesPerPrompt, provider: 'gemini' }));
  return hash.digest('hex');
}

async function readJsonIfExists(filePath) {
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

function globToRegex(glob) {
  const escaped = glob.replace(/[\\.+^${}()|[\]]/g, '\\$&');
  const regexText = `^${escaped.replace(/\*/g, '[^/]*')}$`;
  return new RegExp(regexText);
}

async function expandGlob(pattern) {
  if (!pattern.includes('*')) {
    return [pattern];
  }
  const dir = path.dirname(pattern);
  const basePattern = path.basename(pattern);
  const matcher = globToRegex(basePattern);
  const entries = await fs.readdir(dir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && matcher.test(entry.name))
    .map((entry) => path.join(dir, entry.name));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Process items in parallel with a concurrency limit
 * @param {Array} items - Items to process
 * @param {Function} fn - Async function to process each item
 * @param {number} concurrency - Max concurrent operations
 * @returns {Promise<Array>} Results in same order as items
 */
async function parallelMap(items, fn, concurrency) {
  const results = new Array(items.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < items.length) {
      const index = nextIndex++;
      results[index] = await fn(items[index], index);
    }
  }

  const workers = Array.from({ length: Math.min(concurrency, items.length) }, () => worker());
  await Promise.all(workers);
  return results;
}

/**
 * Get Google Cloud access token using Application Default Credentials
 */
async function getAccessToken() {
  const { GoogleAuth } = await import('google-auth-library');
  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  return token.token;
}

/**
 * Generate image using Vertex AI Gemini model
 */
async function generateImageGemini({ prompt, model, aspect }) {
  const project = process.env.GOOGLE_CLOUD_PROJECT;
  const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

  if (!project) {
    throw new Error('GOOGLE_CLOUD_PROJECT is required for Gemini image generation');
  }

  const accessToken = await getAccessToken();

  // Vertex AI endpoint for generateContent
  const endpoint = `https://${location}-aiplatform.googleapis.com/v1/projects/${project}/locations/${location}/publishers/google/models/${model}:generateContent`;

  const requestBody = {
    contents: [
      {
        role: 'user',
        parts: [{ text: prompt }],
      },
    ],
    generationConfig: {
      responseModalities: ['TEXT', 'IMAGE'],
    },
  };

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const text = await response.text();
    const error = new Error(`Gemini image generation failed (${response.status}): ${text}`);
    error.status = response.status;
    throw error;
  }

  const data = await response.json();

  // Extract image from response
  const parts = data.candidates?.[0]?.content?.parts;

  if (!parts || parts.length === 0) {
    throw new Error(`No content returned from ${model}`);
  }

  // Find the image part
  const imagePart = parts.find((part) => part.inlineData?.mimeType?.startsWith('image/'));

  if (!imagePart || !imagePart.inlineData || !imagePart.inlineData.data) {
    throw new Error(`No image data returned from ${model}`);
  }

  return imagePart.inlineData.data;
}

/**
 * Try to generate with fallback models
 */
async function generateWithFallback({ prompt, aspect, maxRetries, retryBaseMs }) {
  let lastError = null;

  for (const model of IMAGE_MODELS) {
    let attempt = 0;

    while (attempt <= maxRetries) {
      try {
        console.log(`Generating with ${model.name}...`);
        const imageBase64 = await generateImageGemini({
          prompt,
          model: model.id,
          aspect,
        });
        return imageBase64;
      } catch (error) {
        lastError = error;
        const status = error.status ?? 0;

        // Check if error is recoverable
        const isRecoverable =
          status === 429 ||
          status >= 500 ||
          error.message.includes('RESOURCE_EXHAUSTED') ||
          error.message.includes('rate');

        if (isRecoverable && attempt < maxRetries) {
          const delay = retryBaseMs * 2 ** attempt + Math.floor(Math.random() * retryBaseMs);
          console.warn(`Retrying ${model.name} after ${delay}ms (attempt ${attempt + 1}/${maxRetries})`);
          await sleep(delay);
          attempt += 1;
          continue;
        }

        // For 404/NOT_FOUND, try next model
        if (status === 404 || error.message.includes('NOT_FOUND')) {
          console.warn(`${model.name} not available, trying fallback...`);
          break;
        }

        // For other errors, throw
        throw error;
      }
    }
  }

  throw new Error(`All models failed. Last error: ${lastError?.message}`);
}

function buildFinalPrompt(promptText, generationNotes) {
  if (!generationNotes) return promptText;
  return `${promptText}\n\nGeneration Notes:\n${generationNotes}`;
}

async function writeImage(outputDir, imageHint, imageBase64) {
  const filename = `${imageHint}_v1.png`;
  const filePath = path.join(outputDir, filename);
  const buffer = Buffer.from(imageBase64, 'base64');
  await fs.writeFile(filePath, buffer);
  return filename;
}

async function shouldSkip(existingEntry, outputDir) {
  if (!existingEntry) return false;
  if (!existingEntry.output_files || existingEntry.output_files.length === 0) return false;
  const results = await Promise.all(
    existingEntry.output_files.map((file) =>
      fs
        .access(path.join(outputDir, file))
        .then(() => true)
        .catch(() => false)
    )
  );
  return results.every(Boolean);
}

async function main() {
  const promptsGlob = getEnvString('PROMPTS_GLOB', DEFAULT_PROMPTS_GLOB);
  const outputRoot = getEnvString('OUTPUT_ROOT', DEFAULT_OUTPUT_ROOT);
  const imagesPerPrompt = getEnvNumber('IMAGES_PER_PROMPT', DEFAULT_IMAGES_PER_PROMPT);
  const maxPrompts = getEnvNumber('MAX_PROMPTS', DEFAULT_MAX_PROMPTS);
  const maxImages = getEnvNumber('MAX_IMAGES', DEFAULT_MAX_IMAGES);
  const dryRun = getEnvBoolean('DRY_RUN', false);
  const force = getEnvBoolean('FORCE', false);
  const maxRetries = getEnvNumber('MAX_RETRIES', DEFAULT_MAX_RETRIES);
  const retryBaseMs = getEnvNumber('RETRY_BASE_MS', DEFAULT_RETRY_BASE_MS);
  const technicalAspect = getEnvString('TECHNICAL_ASPECT_PREFERENCE', '4:3');
  const conceptualAspect = getEnvString('CONCEPTUAL_ASPECT_PREFERENCE', '16:9');
  const parallel = getEnvNumber('PARALLEL', DEFAULT_PARALLEL);

  const files = await expandGlob(promptsGlob);
  if (files.length === 0) {
    console.warn(`No prompt files found for glob: ${promptsGlob}`);
    return;
  }

  // Collect all pending image generation tasks across all files
  const pendingTasks = [];
  const fileManifests = new Map(); // filePath -> { outputDir, manifestPath, manifestImages, existingEntries }

  for (const filePath of files) {
    const content = await fs.readFile(filePath, 'utf8');
    const { generationNotes, images } = parsePromptFile(content, {
      technicalAspect,
      conceptualAspect,
    });
    const slug = slugFromFilename(filePath);
    const outputDir = path.join(outputRoot, slug);
    await ensureDir(outputDir);

    const manifestPath = path.join(outputDir, 'manifest.json');
    const existingManifest = await readJsonIfExists(manifestPath);
    const existingEntries = new Map(
      (existingManifest?.images ?? []).map((entry) => [entry.prompt_hash, entry])
    );
    const manifestImages = [];

    fileManifests.set(filePath, { outputDir, manifestPath, manifestImages, existingEntries });

    for (const image of images) {
      if (pendingTasks.length >= maxPrompts) break;

      const imageHint = `img-${String(image.index).padStart(2, '0')}`;
      const aspect = image.aspect || '16:9';

      const finalPrompt = buildFinalPrompt(image.promptText, generationNotes);
      const promptHash = hashPrompt({
        prompt: finalPrompt,
        model: PRIMARY_MODEL,
        aspect,
        imagesPerPrompt,
      });
      const existingEntry = existingEntries.get(promptHash);
      const canSkip = !force && (await shouldSkip(existingEntry, outputDir));

      if (canSkip) {
        manifestImages.push(existingEntry);
        console.log(`Skipping ${filePath} ${imageHint} (already generated).`);
        continue;
      }

      if (pendingTasks.length >= maxImages) {
        console.warn('Reached MAX_IMAGES limit.');
        break;
      }

      const outputFile = `${imageHint}_v1.png`;

      pendingTasks.push({
        filePath,
        image,
        imageHint,
        aspect,
        finalPrompt,
        promptHash,
        outputFile,
        outputDir,
      });
    }
  }

  if (pendingTasks.length === 0) {
    console.log('No images to generate.');
    return;
  }

  console.log(`Generating ${pendingTasks.length} images with concurrency ${parallel}...`);

  // Generate images in parallel
  const results = await parallelMap(
    pendingTasks,
    async (task) => {
      const { filePath, image, imageHint, aspect, finalPrompt, promptHash, outputFile, outputDir } = task;

      if (dryRun) {
        console.log(`[DRY RUN] Would generate ${outputFile} for ${filePath}`);
        return { success: true, task };
      }

      try {
        const imageBase64 = await generateWithFallback({
          prompt: finalPrompt,
          aspect,
          maxRetries,
          retryBaseMs,
        });
        await writeImage(outputDir, imageHint, imageBase64);
        console.log(`Generated ${outputFile}`);
        return { success: true, task };
      } catch (error) {
        console.error(`Failed to generate ${imageHint}: ${error.message}`);
        return { success: false, task, error };
      }
    },
    parallel
  );

  // Update manifests with results
  let generatedImageCount = 0;
  for (const result of results) {
    if (!result.success) continue;

    const { task } = result;
    const { filePath, image, aspect, finalPrompt, promptHash, outputFile } = task;
    const fileData = fileManifests.get(filePath);

    fileData.manifestImages.push({
      index: image.index,
      title: image.title,
      caption: image.caption,
      aspect,
      prompt: finalPrompt,
      prompt_hash: promptHash,
      output_files: [outputFile],
      provider: 'gemini',
      model: PRIMARY_MODEL,
    });

    generatedImageCount += 1;
  }

  // Write manifests
  for (const [filePath, fileData] of fileManifests) {
    const { manifestPath, manifestImages } = fileData;
    if (manifestImages.length === 0) continue;

    const manifest = {
      source_md_path: filePath,
      generated_at: new Date().toISOString(),
      provider: 'gemini',
      model: PRIMARY_MODEL,
      images: manifestImages,
    };
    if (!dryRun) {
      await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
    }
  }

  console.log(`\nGenerated ${generatedImageCount} images.`);
}

const isMain = process.argv[1]
  ? pathToFileURL(process.argv[1]).href === import.meta.url
  : false;

if (isMain) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
