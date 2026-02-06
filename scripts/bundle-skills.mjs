/**
 * Bundle skills that have separate tool files into a single file using esbuild.
 *
 * This script uses esbuild to bundle tool files into the main skill file,
 * making them available to the V8 runtime which doesn't support ES modules.
 */
import * as esbuild from 'esbuild';
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');
const skillsOutDir = join(rootDir, 'skills');
const skillsSrcDir = join(rootDir, 'skills-ts-out');

// Header code that provides CommonJS shim for the entry point
// This is needed because the bundled modules write to `exports`
const SKILL_HEADER = `/* Bundled skill with esbuild */
"use strict";
// CommonJS shim for entry point
var exports = {};
var module = { exports: exports };
`;

// Footer code that exposes the bundled skill object to globalThis.__skill
// The V8 runtime will access the skill via globalThis.__skill.default
const SKILL_FOOTER = `
// Expose skill bundle to globalThis for V8 runtime access
// Use module.exports.default if available (CommonJS), otherwise use __skill_bundle
globalThis.__skill = module.exports.default ? { default: module.exports.default } : __skill_bundle;

// IMPORTANT: Fix for esbuild CommonJS interop issue
// Tool modules write to global 'exports' object, but the tools array references
// empty module-specific exports. Rebuild tools array from global exports.
(function() {
  var skill = globalThis.__skill && globalThis.__skill.default;
  if (!skill || !skill.tools) return;

  // Check if tools array has undefined elements (sign of the CommonJS issue)
  var hasUndefined = skill.tools.some(function(t) { return t === undefined || t === null; });
  if (!hasUndefined) return;

  // Collect tools from global exports object (where they actually ended up)
  var fixedTools = [];
  for (var key in exports) {
    if (key.endsWith('Tool') && exports[key] && exports[key].name && exports[key].execute) {
      fixedTools.push(exports[key]);
    }
  }

  if (fixedTools.length > 0) {
    skill.tools = fixedTools;
    console.log('[skill-fixup] Rebuilt tools array from exports (' + fixedTools.length + ' tools)');
  }
})();
`;

// Find all skills that have a tools directory
const skills = readdirSync(skillsSrcDir, { withFileTypes: true })
  .filter(dirent => dirent.isDirectory())
  .map(dirent => dirent.name);

// Track which skills get bundled (so we skip them in the copy step)
const bundledSkills = new Set();

for (const skillName of skills) {
  const skillDirInput = join(skillsSrcDir, skillName);
  const skillDirOutput = join(skillsOutDir, skillName);
  const skillIndexPath = join(skillDirInput, 'index.js');
  const skillIndexPathOutput = join(skillDirOutput, 'index.js');
  const toolsDir = join(skillDirInput, 'tools');

  // Skip if index.js doesn't exist
  if (!existsSync(skillIndexPath)) {
    continue;
  }

  // Read the main skill file
  let skillCode = readFileSync(skillIndexPath, 'utf-8');

  // Check if it has import or require statements (if not, it's already bundled or doesn't need bundling)
  if (!skillCode.includes('import ') && !skillCode.includes('require(')) {
    continue;
  }

  // Check if tools directory exists and has any .js files
  let hasTools = false;
  let toolCount = 0;
  if (existsSync(toolsDir)) {
    const toolFiles = readdirSync(toolsDir).filter(file => file.endsWith('.js'));
    toolCount = toolFiles.length;
    hasTools = toolCount > 0;
  }

  // Check if skill has local imports (require('./...') or require("./..."))
  // These need bundling even without a tools directory
  const hasLocalImports = /require\(['"]\.\//.test(skillCode);

  // Skip if no tools and no local imports
  if (!hasTools && !hasLocalImports) {
    continue;
  }

  const bundleReason = hasTools ? `${toolCount} tool files` : 'local imports';
  console.log(`[bundle-skills] Bundling ${skillName} (${bundleReason})...`);

  try {
    const polyfillsDir = join(__dirname, 'polyfills');

    // Use esbuild to bundle the skill with its tools
    // Use IIFE format and configure it to output code that can be executed directly
    const result = await esbuild.build({
      entryPoints: [skillIndexPath],
      bundle: true,
      write: false, // Don't write directly, we need to append footer
      format: 'iife',
      globalName: '__skill_bundle',
      platform: 'browser',
      target: 'es2020',
      minify: false,
      sourcemap: false,
      treeShaking: true,
      // Don't add "use strict" as it prevents global assignments
      legalComments: 'none',
      banner: { js: '/* Bundled skill with esbuild */' },
      // Configure to handle CommonJS modules properly
      mainFields: ['module', 'main'],
      // Suppress CommonJS-in-ESM warnings since we're intentionally using a hybrid approach
      logOverride: {
        'commonjs-variable-in-esm': 'silent',
      },
      inject: [join(polyfillsDir, 'buffer-inject.js')],
      alias: {
        buffer: join(polyfillsDir, 'buffer.js'),
        crypto: join(polyfillsDir, 'crypto.js'),
        events: join(polyfillsDir, 'events.js'),
        'async-mutex': join(polyfillsDir, 'async-mutex.js'),
        websocket: join(polyfillsDir, 'websocket.js'),
        store2: join(polyfillsDir, 'store2.js'),
        'big-integer': join(polyfillsDir, 'big-integer.js'),
        path: join(polyfillsDir, 'path.js'),
        fs: join(polyfillsDir, 'fs.js'),
        os: join(polyfillsDir, 'os.js'),
        net: join(polyfillsDir, 'net.js'),
        tls: join(polyfillsDir, 'tls.js'),
        stream: join(polyfillsDir, 'stream.js'),
        util: join(polyfillsDir, 'util.js'),
        socks: join(polyfillsDir, 'socks.js'),
        'ts-custom-error': join(polyfillsDir, 'ts-custom-error.js'),
        '@cryptography/aes': join(polyfillsDir, 'cryptography-aes.js'),
        htmlparser2: join(polyfillsDir, 'htmlparser2.js'),
        'node-localstorage': join(polyfillsDir, 'node-localstorage.js'),
        pako: join(polyfillsDir, 'pako.js'),
        mime: join(polyfillsDir, 'mime.js'),
      },
    });

    if (!result.outputFiles || result.outputFiles.length === 0) {
      throw new Error('esbuild did not produce output');
    }

    let bundledCode = result.outputFiles[0].text;

    // Remove the default esbuild header and add our CommonJS shim header
    bundledCode = bundledCode.replace(/^\/\* Bundled skill with esbuild \*\/\n"use strict";\n/, '');
    bundledCode = SKILL_HEADER + bundledCode;

    // Append footer that exposes skill functions to globalThis
    bundledCode = bundledCode + SKILL_FOOTER;

    // Ensure output directory exists
    if (!existsSync(skillDirOutput)) {
      mkdirSync(skillDirOutput, { recursive: true });
    }

    // Write the bundled file
    writeFileSync(skillIndexPathOutput, bundledCode);

    // Track that this skill was bundled
    bundledSkills.add(skillName);

    console.log(
      `[bundle-skills] Bundled ${skillName} (${(bundledCode.length / 1024).toFixed(1)} KB)`
    );
  } catch (error) {
    console.error(`[bundle-skills] Failed to bundle ${skillName}:`, error.message, error);
    if (error.errors) {
      for (const err of error.errors) {
        console.error(`  ${err.location?.file}:${err.location?.line}: ${err.text}`);
      }
    }
    // Don't exit - continue with other skills
  }
}

// Copy non-bundled skills (no tools dir) from skills-ts-out to skills; wrap with CommonJS shim so V8 sees globalThis.__skill
const srcDir = join(rootDir, 'src');
const COPY_HEADER = `/* Skill (no tools - copied from TS build) */
"use strict";
var exports = {};
var module = { exports: exports };
`;
const COPY_FOOTER = `
globalThis.__skill = module.exports && module.exports.default ? { default: module.exports.default } : (module.exports || {});
`;
for (const skillName of skills) {
  // Skip if already bundled
  if (bundledSkills.has(skillName)) continue;

  const skillDirInput = join(skillsSrcDir, skillName);
  const skillDirOutput = join(skillsOutDir, skillName);
  const skillIndexPath = join(skillDirInput, 'index.js');
  const skillIndexPathOutput = join(skillDirOutput, 'index.js');
  if (!existsSync(skillIndexPath)) continue;
  if (!existsSync(skillDirOutput)) mkdirSync(skillDirOutput, { recursive: true });
  let code = readFileSync(skillIndexPath, 'utf-8');
  code = COPY_HEADER + code + COPY_FOOTER;
  writeFileSync(skillIndexPathOutput, code);
  const srcManifest = join(srcDir, skillName, 'manifest.json');
  const outManifest = join(skillDirOutput, 'manifest.json');
  if (existsSync(srcManifest)) copyFileSync(srcManifest, outManifest);
  console.log(`[bundle-skills] Copied ${skillName} (no tools)`);
}

console.log('[bundle-skills] Bundle complete');
