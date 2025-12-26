#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DEFAULT_PROMPTS_GLOB = 'articles/prompts/*.md';
const DEFAULT_OUTPUT_ROOT = 'articles/images';
const DEFAULT_MODEL = 'gpt-image-1';
const DEFAULT_IMAGES_PER_PROMPT = 1;
const DEFAULT_MAX_PROMPTS = 1000;
const DEFAULT_MAX_IMAGES = 1000;
const DEFAULT_SLEEP_MIN_MS = 500;
const DEFAULT_SLEEP_MAX_MS = 1500;
const DEFAULT_MAX_RETRIES = 5;
const DEFAULT_RETRY_BASE_MS = 500;
const DEFAULT_TECHNICAL_ASPECT = '4:3';
const DEFAULT_CONCEPTUAL_ASPECT = '16:9';

const ASPECT_SIZES = {
  '16:9': '1536x864',
  '4:3': '1536x1152',
  '1:1': '1024x1024',
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

export function selectAspectForIndex(index, generationNotes, options = {}) {
  const technicalAspect = options.technicalAspect ?? DEFAULT_TECHNICAL_ASPECT;
  const conceptualAspect = options.conceptualAspect ?? DEFAULT_CONCEPTUAL_ASPECT;
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

export function parsePromptFile(content, options = {}) {
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

function getAspectSize(aspect) {
  const envKey = `SIZE_${aspect.replace(':', '_')}`;
  const override = process.env[envKey];
  return override ?? ASPECT_SIZES[aspect];
}

function hashPrompt({ prompt, model, size, imagesPerPrompt }) {
  const hash = crypto.createHash('sha256');
  hash.update(JSON.stringify({ prompt, model, size, imagesPerPrompt }));
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
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, '\\$&');
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

async function generateImagesOpenAI({ prompt, model, size, imagesPerPrompt }) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('OPENAI_API_KEY is required to generate images.');
  }

  const response = await fetch('https://api.openai.com/v1/images', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      prompt,
      size,
      n: imagesPerPrompt,
      response_format: 'b64_json',
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    const error = new Error(`OpenAI image generation failed (${response.status}): ${text}`);
    error.status = response.status;
    throw error;
  }

  const data = await response.json();
  if (!data.data || !Array.isArray(data.data)) {
    throw new Error('Unexpected response from OpenAI image API.');
  }

  return data.data.map((item) => item.b64_json);
}

async function generateWithRetry({ prompt, model, size, imagesPerPrompt, maxRetries, retryBaseMs }) {
  let attempt = 0;
  while (true) {
    try {
      return await generateImagesOpenAI({ prompt, model, size, imagesPerPrompt });
    } catch (error) {
      const status = error.status ?? 0;
      const shouldRetry = status === 429 || status >= 500;
      if (!shouldRetry || attempt >= maxRetries) {
        throw error;
      }
      const delay = retryBaseMs * 2 ** attempt + Math.floor(Math.random() * retryBaseMs);
      console.warn(`Retrying after ${delay}ms due to error: ${error.message}`);
      await sleep(delay);
      attempt += 1;
    }
  }
}

function buildFinalPrompt(promptText, generationNotes) {
  if (!generationNotes) return promptText;
  return `${promptText}\n\nGeneration Notes:\n${generationNotes}`;
}

async function writeImages(outputDir, imageHint, imagesBase64, dryRun) {
  const files = [];
  for (let i = 0; i < imagesBase64.length; i += 1) {
    const version = i + 1;
    const filename = `${imageHint}_v${version}.png`;
    const filePath = path.join(outputDir, filename);
    files.push(filename);
    if (!dryRun) {
      const buffer = Buffer.from(imagesBase64[i], 'base64');
      await fs.writeFile(filePath, buffer);
    }
  }
  return files;
}

async function shouldSkip(existingEntry, outputDir) {
  if (!existingEntry) return false;
  if (!existingEntry.output_files || existingEntry.output_files.length === 0) return false;
  const results = await Promise.all(
    existingEntry.output_files.map((file) =>
      fs
        .access(path.join(outputDir, file))
        .then(() => true)
        .catch(() => false),
    ),
  );
  return results.every(Boolean);
}

async function main() {
  const promptsGlob = getEnvString('PROMPTS_GLOB', DEFAULT_PROMPTS_GLOB);
  const outputRoot = getEnvString('OUTPUT_ROOT', DEFAULT_OUTPUT_ROOT);
  const model = getEnvString('MODEL', DEFAULT_MODEL);
  const imagesPerPrompt = getEnvNumber('IMAGES_PER_PROMPT', DEFAULT_IMAGES_PER_PROMPT);
  const maxPrompts = getEnvNumber('MAX_PROMPTS', DEFAULT_MAX_PROMPTS);
  const maxImages = getEnvNumber('MAX_IMAGES', DEFAULT_MAX_IMAGES);
  const dryRun = Boolean(process.env.DRY_RUN);
  const force = Boolean(process.env.FORCE);
  const sleepMin = getEnvNumber('SLEEP_MIN_MS', DEFAULT_SLEEP_MIN_MS);
  const sleepMax = getEnvNumber('SLEEP_MAX_MS', DEFAULT_SLEEP_MAX_MS);
  const maxRetries = getEnvNumber('MAX_RETRIES', DEFAULT_MAX_RETRIES);
  const retryBaseMs = getEnvNumber('RETRY_BASE_MS', DEFAULT_RETRY_BASE_MS);
  const technicalAspect = getEnvString('TECHNICAL_ASPECT_PREFERENCE', DEFAULT_TECHNICAL_ASPECT);
  const conceptualAspect = getEnvString('CONCEPTUAL_ASPECT_PREFERENCE', DEFAULT_CONCEPTUAL_ASPECT);

  const files = await expandGlob(promptsGlob);
  if (files.length === 0) {
    console.warn(`No prompt files found for glob: ${promptsGlob}`);
    return;
  }

  let processedPromptCount = 0;
  let generatedImageCount = 0;

  for (const filePath of files) {
    if (processedPromptCount >= maxPrompts) {
      console.warn('Reached MAX_PROMPTS limit.');
      break;
    }

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
      (existingManifest?.images ?? []).map((entry) => [entry.prompt_hash, entry]),
    );
    const manifestImages = [];

    for (const image of images) {
      if (processedPromptCount >= maxPrompts) {
        break;
      }
      const imageHint = `img-${String(image.index).padStart(2, '0')}`;
      const aspect = image.aspect || '16:9';
      const size = getAspectSize(aspect);
      if (!size) {
        throw new Error(`No size mapping for aspect ratio ${aspect}`);
      }

      const finalPrompt = buildFinalPrompt(image.promptText, generationNotes);
      const promptHash = hashPrompt({
        prompt: finalPrompt,
        model,
        size,
        imagesPerPrompt,
      });
      const existingEntry = existingEntries.get(promptHash);
      const canSkip = !force && (await shouldSkip(existingEntry, outputDir));

      if (canSkip) {
        manifestImages.push(existingEntry);
        console.log(`Skipping ${filePath} ${imageHint} (already generated).`);
        processedPromptCount += 1;
        continue;
      }

      const outputFiles = Array.from({ length: imagesPerPrompt }, (_, idx) => {
        const version = idx + 1;
        return `${imageHint}_v${version}.png`;
      });

      if (dryRun) {
        console.log(`[DRY RUN] Would generate ${outputFiles.join(', ')} for ${filePath}`);
      } else {
        if (generatedImageCount + imagesPerPrompt > maxImages) {
          console.warn('Reached MAX_IMAGES limit.');
          break;
        }

        const imagesBase64 = await generateWithRetry({
          prompt: finalPrompt,
          model,
          size,
          imagesPerPrompt,
          maxRetries,
          retryBaseMs,
        });
        await writeImages(outputDir, imageHint, imagesBase64, dryRun);
        generatedImageCount += imagesBase64.length;
      }

      manifestImages.push({
        index: image.index,
        title: image.title,
        caption: image.caption,
        aspect,
        size,
        prompt: finalPrompt,
        prompt_hash: promptHash,
        output_files: outputFiles,
      });

      processedPromptCount += 1;

      const sleepDuration = sleepMin + Math.floor(Math.random() * (sleepMax - sleepMin + 1));
      if (!dryRun) {
        await sleep(sleepDuration);
      }
    }

    const manifest = {
      source_md_path: filePath,
      generated_at: new Date().toISOString(),
      model,
      images: manifestImages,
    };
    await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  }
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
