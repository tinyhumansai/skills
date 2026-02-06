#!/usr/bin/env node
// Download Gemma 3n E2B Q4_K_M GGUF model for local inference testing.
//
// Features:
//   - Resume support via HTTP Range headers
//   - Progress bar in terminal
//   - Downloads to temp file first, renames on completion
//   - Skips download if model already exists

import { existsSync, mkdirSync, statSync, createWriteStream, renameSync, unlinkSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import https from 'https';
import http from 'http';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');

const MODEL_URL =
  'https://huggingface.co/bartowski/google_gemma-3n-E2B-it-GGUF/resolve/main/google_gemma-3n-E2B-it-Q4_K_M.gguf';
const MODELS_DIR = join(rootDir, '.models');
const MODEL_FILENAME = 'gemma-3n-E2B-it-Q4_K_M.gguf';
const MODEL_PATH = join(MODELS_DIR, MODEL_FILENAME);
const TEMP_PATH = MODEL_PATH + '.download';

const colors = {
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  dim: '\x1b[2m',
  reset: '\x1b[0m',
  red: '\x1b[31m',
};

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function printProgress(downloaded, total) {
  const pct = total > 0 ? ((downloaded / total) * 100).toFixed(1) : '??';
  const bar = total > 0 ? makeBar(downloaded / total, 30) : '[...]';
  const dl = formatBytes(downloaded);
  const tot = total > 0 ? formatBytes(total) : '???';
  process.stdout.write(`\r  ${bar} ${pct}%  ${dl} / ${tot}  `);
}

function makeBar(ratio, width) {
  const filled = Math.round(ratio * width);
  return '[' + '#'.repeat(filled) + '-'.repeat(width - filled) + ']';
}

function fetchFollowRedirects(url, headers, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) return reject(new Error('Too many redirects'));

    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, { headers }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        // Follow redirect
        res.resume(); // discard body
        fetchFollowRedirects(res.headers.location, headers, maxRedirects - 1)
          .then(resolve)
          .catch(reject);
      } else {
        resolve(res);
      }
    });
    req.on('error', reject);
  });
}

async function downloadModel() {
  console.log(`${colors.cyan}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.cyan}              Model Downloader - Gemma 3n E2B                 ${colors.reset}`);
  console.log(`${colors.cyan}═══════════════════════════════════════════════════════════════${colors.reset}`);

  // Check if model already exists
  if (existsSync(MODEL_PATH)) {
    const stat = statSync(MODEL_PATH);
    console.log(`\n${colors.green}✓ Model already exists${colors.reset}`);
    console.log(`  ${colors.dim}Path: ${MODEL_PATH}${colors.reset}`);
    console.log(`  ${colors.dim}Size: ${formatBytes(stat.size)}${colors.reset}`);
    return;
  }

  // Create .models directory
  if (!existsSync(MODELS_DIR)) {
    mkdirSync(MODELS_DIR, { recursive: true });
  }

  // Check for partial download (resume support)
  let startByte = 0;
  if (existsSync(TEMP_PATH)) {
    const stat = statSync(TEMP_PATH);
    startByte = stat.size;
    console.log(`\n${colors.yellow}Resuming download from ${formatBytes(startByte)}...${colors.reset}`);
  } else {
    console.log(`\n${colors.blue}Downloading model...${colors.reset}`);
  }

  console.log(`  ${colors.dim}URL: ${MODEL_URL}${colors.reset}`);
  console.log(`  ${colors.dim}Destination: ${MODEL_PATH}${colors.reset}\n`);

  const headers = {};
  if (startByte > 0) {
    headers['Range'] = `bytes=${startByte}-`;
  }

  try {
    const res = await fetchFollowRedirects(MODEL_URL, headers);

    if (res.statusCode === 416) {
      // Range not satisfiable - file is complete, just rename
      res.resume();
      console.log(`\n${colors.green}✓ Download already complete, renaming temp file${colors.reset}`);
      renameSync(TEMP_PATH, MODEL_PATH);
      return;
    }

    if (res.statusCode !== 200 && res.statusCode !== 206) {
      res.resume();
      throw new Error(`HTTP ${res.statusCode}: ${res.statusMessage}`);
    }

    const contentLength = parseInt(res.headers['content-length'] || '0', 10);
    const totalSize = res.statusCode === 206 ? startByte + contentLength : contentLength;

    const fileStream = createWriteStream(TEMP_PATH, { flags: startByte > 0 ? 'a' : 'w' });
    let downloaded = startByte;

    res.on('data', (chunk) => {
      downloaded += chunk.length;
      printProgress(downloaded, totalSize);
    });

    res.pipe(fileStream);

    await new Promise((resolve, reject) => {
      fileStream.on('finish', resolve);
      fileStream.on('error', reject);
      res.on('error', reject);
    });

    console.log('\n');

    // Rename temp file to final path
    renameSync(TEMP_PATH, MODEL_PATH);

    console.log(`${colors.green}✓ Download complete!${colors.reset}`);
    console.log(`  ${colors.dim}Path: ${MODEL_PATH}${colors.reset}`);
    console.log(`  ${colors.dim}Size: ${formatBytes(downloaded)}${colors.reset}`);
  } catch (err) {
    console.error(`\n\n${colors.red}Download failed: ${err.message}${colors.reset}`);
    console.error(`${colors.dim}Partial download preserved at ${TEMP_PATH} for resume.${colors.reset}`);
    process.exit(1);
  }
}

downloadModel();
