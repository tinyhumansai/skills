/**
 * model-bridge.ts - Synchronous wrapper around the async LLM worker.
 *
 * Uses Worker thread + SharedArrayBuffer + Atomics.wait to provide
 * synchronous model.generate() and model.summarize() calls, mirroring
 * how the Rust host blocks the QuickJS thread during native ops.
 */

import { Worker } from 'worker_threads';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Max response size: 256 KB (4 bytes length header + payload)
const RESULT_BUFFER_SIZE = 4 + 256 * 1024;
// Timeout for inference: 5 minutes
const INFERENCE_TIMEOUT_MS = 5 * 60 * 1000;

export interface ModelStatus {
  available: boolean;
  loaded: boolean;
  loading: boolean;
  downloaded: boolean;
  error?: string;
  modelPath?: string;
}

export interface ModelGenerateOptions {
  maxTokens?: number;
  temperature?: number;
  topP?: number;
}

export interface ModelSummarizeOptions {
  maxTokens?: number;
}

export class ModelBridge {
  private worker: Worker | null = null;
  private loaded = false;
  private loading = false;
  private modelPath: string | null = null;
  private error: string | null = null;

  /**
   * Start the worker and load the model. Must be called before generate/summarize.
   */
  async load(modelPath: string): Promise<void> {
    this.modelPath = modelPath;
    this.loading = true;
    this.error = null;

    const workerPath = join(__dirname, 'model-worker.mjs');
    this.worker = new Worker(workerPath);

    return new Promise<void>((resolve, reject) => {
      this.worker!.on('message', (msg: { type: string; ok: boolean; error?: string }) => {
        if (msg.type === 'loaded') {
          this.loading = false;
          if (msg.ok) {
            this.loaded = true;
            resolve();
          } else {
            this.error = msg.error ?? 'Unknown load error';
            reject(new Error(this.error));
          }
        }
      });

      this.worker!.on('error', (err: Error) => {
        this.loading = false;
        this.error = err.message;
        reject(err);
      });

      this.worker!.postMessage({ type: 'load', modelPath });
    });
  }

  /**
   * Generate text from a prompt. Blocks the main thread until the worker finishes.
   */
  generate(prompt: string, options?: ModelGenerateOptions): string {
    if (!this.worker || !this.loaded) {
      throw new Error('Model not loaded. Call load() first.');
    }

    const signalBuffer = new SharedArrayBuffer(4);
    const resultBuffer = new SharedArrayBuffer(RESULT_BUFFER_SIZE);

    // Reset signal
    const int32 = new Int32Array(signalBuffer);
    Atomics.store(int32, 0, 0);

    this.worker.postMessage({
      type: 'generate',
      prompt,
      options,
      signalBuffer,
      resultBuffer,
    });

    // Block until worker signals completion
    const waitResult = Atomics.wait(int32, 0, 0, INFERENCE_TIMEOUT_MS);
    if (waitResult === 'timed-out') {
      throw new Error('Model inference timed out');
    }

    return this.readResult(resultBuffer);
  }

  /**
   * Summarize text. Blocks the main thread until the worker finishes.
   */
  summarize(text: string, options?: ModelSummarizeOptions): string {
    if (!this.worker || !this.loaded) {
      throw new Error('Model not loaded. Call load() first.');
    }

    const signalBuffer = new SharedArrayBuffer(4);
    const resultBuffer = new SharedArrayBuffer(RESULT_BUFFER_SIZE);

    const int32 = new Int32Array(signalBuffer);
    Atomics.store(int32, 0, 0);

    this.worker.postMessage({
      type: 'summarize',
      text,
      options,
      signalBuffer,
      resultBuffer,
    });

    const waitResult = Atomics.wait(int32, 0, 0, INFERENCE_TIMEOUT_MS);
    if (waitResult === 'timed-out') {
      throw new Error('Model summarize timed out');
    }

    return this.readResult(resultBuffer);
  }

  isAvailable(): boolean {
    return this.loaded;
  }

  getStatus(): ModelStatus {
    return {
      available: this.loaded,
      loaded: this.loaded,
      loading: this.loading,
      downloaded: this.modelPath !== null,
      error: this.error ?? undefined,
      modelPath: this.modelPath ?? undefined,
    };
  }

  /**
   * Terminate the worker thread and release resources.
   */
  async dispose(): Promise<void> {
    if (this.worker) {
      this.worker.postMessage({ type: 'terminate' });
      await this.worker.terminate();
      this.worker = null;
      this.loaded = false;
    }
  }

  private readResult(resultBuffer: SharedArrayBuffer): string {
    const view = new DataView(resultBuffer);
    const length = view.getUint32(0, true);
    const decoder = new TextDecoder();
    const payload = new Uint8Array(resultBuffer, 4, length);
    const text = decoder.decode(payload);

    if (text.startsWith('[ERROR] ')) {
      throw new Error(text.slice(8));
    }

    return text;
  }
}
