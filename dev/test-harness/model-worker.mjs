// model-worker.mjs - Worker thread for async LLM inference
//
// Runs in a Worker thread. Receives messages from the main thread,
// performs inference via node-llama-cpp, and signals completion via
// SharedArrayBuffer + Atomics.notify.
//
// Message types:
//   { type: 'load', modelPath: string }
//   { type: 'generate', prompt, options, signalBuffer, resultBuffer }
//   { type: 'summarize', text, options, signalBuffer, resultBuffer }
//   { type: 'terminate' }

import { parentPort } from 'worker_threads';

let model = null;
let context = null;

async function loadModel(modelPath) {
  const { getLlama } = await import('node-llama-cpp');
  const llama = await getLlama();
  model = await llama.loadModel({ modelPath });
  context = await model.createContext();
  parentPort.postMessage({ type: 'loaded', ok: true });
}

function writeResult(resultBuffer, text) {
  const encoder = new TextEncoder();
  const encoded = encoder.encode(text);
  const view = new Uint8Array(resultBuffer);
  // First 4 bytes = length (uint32 LE)
  const lenView = new DataView(resultBuffer);
  lenView.setUint32(0, encoded.length, true);
  // Rest = UTF-8 payload
  view.set(encoded, 4);
}

function signal(signalBuffer) {
  const int32 = new Int32Array(signalBuffer);
  Atomics.store(int32, 0, 1); // set flag to 1 (done)
  Atomics.notify(int32, 0);
}

async function handleGenerate(prompt, options, signalBuffer, resultBuffer) {
  try {
    const { LlamaChatSession } = await import('node-llama-cpp');
    const session = new LlamaChatSession({ contextSequence: context.getSequence() });

    const maxTokens = options?.maxTokens ?? 2048;
    const temperature = options?.temperature ?? 0.7;
    const topP = options?.topP ?? 0.9;

    const response = await session.prompt(prompt, {
      maxTokens,
      temperature,
      topP,
    });

    session.dispose();
    writeResult(resultBuffer, response);
  } catch (err) {
    writeResult(resultBuffer, `[ERROR] ${err.message}`);
  }
  signal(signalBuffer);
}

async function handleSummarize(text, options, signalBuffer, resultBuffer) {
  const maxTokens = options?.maxTokens ?? 500;
  const summaryPrompt = `Please summarize the following text concisely:\n\n${text}\n\nSummary:`;

  try {
    const { LlamaChatSession } = await import('node-llama-cpp');
    const session = new LlamaChatSession({ contextSequence: context.getSequence() });

    const response = await session.prompt(summaryPrompt, {
      maxTokens,
      temperature: 0.5,
      topP: 0.9,
    });

    session.dispose();
    writeResult(resultBuffer, response);
  } catch (err) {
    writeResult(resultBuffer, `[ERROR] ${err.message}`);
  }
  signal(signalBuffer);
}

parentPort.on('message', async (msg) => {
  switch (msg.type) {
    case 'load':
      try {
        await loadModel(msg.modelPath);
      } catch (err) {
        parentPort.postMessage({ type: 'loaded', ok: false, error: err.message });
      }
      break;

    case 'generate':
      await handleGenerate(msg.prompt, msg.options, msg.signalBuffer, msg.resultBuffer);
      break;

    case 'summarize':
      await handleSummarize(msg.text, msg.options, msg.signalBuffer, msg.resultBuffer);
      break;

    case 'terminate':
      if (context) context.dispose();
      if (model) model.dispose();
      process.exit(0);
      break;
  }
});
