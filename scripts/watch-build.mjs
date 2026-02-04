#!/usr/bin/env node

import { spawn } from 'child_process';
import { watch } from 'fs';
import { existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');
const skillsDir = join(projectRoot, 'skills');

// Run build:strip
function runStrip() {
  return new Promise((resolve, reject) => {
    console.log('[watch] Running build:strip...');
    const stripProcess = spawn('npm', ['run', 'build:strip'], {
      cwd: projectRoot,
      stdio: 'inherit',
      shell: true,
    });

    stripProcess.on('close', code => {
      if (code === 0) {
        console.log('[watch] build:strip completed successfully');
        resolve();
      } else {
        console.error(`[watch] build:strip exited with code ${code}`);
        reject(new Error(`build:strip failed with code ${code}`));
      }
    });

    stripProcess.on('error', err => {
      console.error('[watch] Error running build:strip:', err);
      reject(err);
    });
  });
}

// Watch for JS file changes in skills directory
function watchSkills() {
  if (!existsSync(skillsDir)) {
    console.log(`[watch] Skills directory doesn't exist yet, will watch after first build`);
    return;
  }

  console.log(`[watch] Watching ${skillsDir} for JS file changes...`);

  let timeout;
  let isRunning = false;

  watch(skillsDir, { recursive: true }, (eventType, filename) => {
    if (filename && filename.endsWith('.js') && !isRunning) {
      // Debounce: wait 300ms after last change before running strip
      clearTimeout(timeout);
      timeout = setTimeout(async () => {
        isRunning = true;
        try {
          await runStrip();
        } catch (err) {
          // Error already logged
        } finally {
          isRunning = false;
        }
      }, 300);
    }
  });
}

// Start TypeScript compiler in watch mode
console.log('[watch] Starting TypeScript compiler in watch mode...');
const tscProcess = spawn('tsc', ['--watch', '-p', 'tsconfig.build.json'], {
  cwd: projectRoot,
  stdio: 'inherit',
  shell: true,
});

// Wait a bit for initial build, then start watching and run strip
setTimeout(() => {
  watchSkills();
  // Run strip once initially after first compilation
  setTimeout(async () => {
    try {
      await runStrip();
    } catch (err) {
      // Error already logged
    }
  }, 1000);
}, 2000);

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n[watch] Shutting down...');
  tscProcess.kill();
  process.exit(0);
});

tscProcess.on('close', code => {
  console.log(`[watch] TypeScript compiler exited with code ${code}`);
  process.exit(code || 0);
});

tscProcess.on('error', err => {
  console.error('[watch] Error starting TypeScript compiler:', err);
  process.exit(1);
});
