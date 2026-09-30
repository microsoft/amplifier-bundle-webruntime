# Initialization Sequence

The browser Amplifier initialization must follow a specific order. This document details each step and common failure modes.

## The Sequence

```
1. Check WebGPU Support     → Fail fast if not available
        ↓
2. Load Pyodide Runtime     → ~5-10 seconds
        ↓
3. Install Python Packages  → pydantic, pyyaml, typing-extensions
        ↓
4. Install amplifier-core   → From embedded wheel
        ↓
5. Load WebLLM Model        → ~30s-5min depending on model/cache
        ↓
6. Set Up JS Bridges        → js_llm_complete, js_web_fetch
        ↓
7. Load Browser Module      → amplifier-browser.py
        ↓
8. Create Amplifier Session → With system prompt
        ↓
9. Ready for Chat!
```

## Step-by-Step Implementation

### Step 1: Check WebGPU

**Must be first** - no point loading anything else if WebGPU unavailable.

```javascript
if (!navigator.gpu) {
    throw new Error('WebGPU not supported. Use Chrome 113+ or Edge 113+.');
}

const adapter = await navigator.gpu.requestAdapter();
if (!adapter) {
    throw new Error('No WebGPU adapter found. Check GPU drivers.');
}
```

**Common failures:**
- Firefox without flag enabled
- Safari < 18
- Missing/outdated GPU drivers
- Running in incognito with hardware acceleration disabled

### Step 2: Load Pyodide

```javascript
const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.0/full/';

// Load the Pyodide script
const script = document.createElement('script');
script.src = `${PYODIDE_URL}pyodide.js`;
document.head.appendChild(script);

await new Promise((resolve, reject) => {
    script.onload = resolve;
    script.onerror = () => reject(new Error('Failed to load Pyodide'));
});

// Initialize Pyodide
pyodide = await window.loadPyodide({ indexURL: PYODIDE_URL });
```

**Common failures:**
- CDN blocked by firewall/proxy
- Slow network causing timeout
- Content Security Policy blocking CDN

### Step 3: Install Python Packages

```javascript
await pyodide.loadPackage('micropip');
const micropip = pyodide.pyimport('micropip');

// Install in order - these are amplifier-core dependencies
const packages = ['pydantic', 'pyyaml', 'typing-extensions'];
for (const pkg of packages) {
    await micropip.install(pkg);
}
```

**Why these packages:**
- `pydantic` - Data validation for Amplifier models
- `pyyaml` - YAML parsing for configs
- `typing-extensions` - Python typing backports

### Step 4: Install amplifier-core

```javascript
// Get embedded wheel
const wheelB64 = document.getElementById('amplifier-wheel-b64').textContent.trim();

// Decode and write to filesystem
const wheelBytes = Uint8Array.from(atob(wheelB64), c => c.charCodeAt(0));
pyodide.FS.writeFile('/tmp/amplifier_core-1.0.0-py3-none-any.whl', wheelBytes);

// Install from local filesystem
await micropip.install('emfs:/tmp/amplifier_core-1.0.0-py3-none-any.whl');
```

**Critical:** The `emfs:` prefix tells micropip to read from Emscripten filesystem.

### Step 5: Load WebLLM Model

```javascript
import { CreateMLCEngine } from '@mlc-ai/web-llm';

const modelId = 'Phi-3.5-mini-instruct-q4f16_1-MLC';

llmEngine = await CreateMLCEngine(modelId, {
    initProgressCallback: (progress) => {
        // Update UI with progress
        if (progress.progress !== undefined) {
            updateProgress(Math.round(progress.progress * 100));
        }
    }
});
```

**First load:** Downloads model from CDN (~2GB for Phi-3.5)
**Subsequent loads:** Uses browser cache (OPFS), much faster

### Step 6: Set Up JS Bridges

```javascript
// Main completion bridge
globalThis.js_llm_complete = async (messagesJson, toolsJson) => {
    const messages = JSON.parse(messagesJson);
    const response = await llmEngine.chat.completions.create({
        messages,
        temperature: 0.7,
        max_tokens: 2048
    });
    return JSON.stringify({
        content: response.choices[0].message.content || '',
        usage: response.usage,
        finish_reason: response.choices[0].finish_reason
    });
};

// Streaming bridge (optional, falls back to complete)
globalThis.js_llm_stream = async (messagesJson, onChunk) => {
    // Can implement streaming here
    return globalThis.js_llm_complete(messagesJson, null);
};

// Web fetch bridge
globalThis.js_web_fetch = async (url) => {
    try {
        const parsed = new URL(url);
        if (parsed.protocol !== 'https:' || parsed.username || parsed.password) {
            throw new Error('Only absolute HTTPS URLs without credentials are allowed');
        }
        if (globalThis.location && parsed.origin === globalThis.location.origin) {
            throw new Error('Same-origin requests are not allowed');
        }
        const response = await fetch(parsed.href, {
            credentials: 'omit',
            mode: 'cors',
            redirect: 'error',
            referrerPolicy: 'no-referrer'
        });
        if (!response.ok) {
            return JSON.stringify({ error: `HTTP ${response.status}` });
        }
        const text = await response.text();
        return text.length > 50000 
            ? text.substring(0, 50000) + '\n\n[Truncated]' 
            : text;
    } catch (e) {
        return JSON.stringify({ error: e.message });
    }
};

// Python imports these bridges from the JavaScript global scope.
globalThis.js_approve_tool_call = async (name, argumentsJson, prompt) => {
    try {
        const args = JSON.parse(argumentsJson);
        return window.confirm(
            `Allow tool call "${name}" with arguments:\n${JSON.stringify(args, null, 2)}`
        ) === true;
    } catch (error) {
        return false;
    }
};
```

### Step 7: Load Browser Module

```javascript
const moduleB64 = document.getElementById('amplifier-browser-py').textContent.trim();
const moduleCode = atob(moduleB64);
await pyodide.runPythonAsync(moduleCode);
```

This makes `create_session()` available in Python.

### Step 8: Create Session

```javascript
const systemPrompt = `Your system prompt here...`;

// Escape for Python triple-quoted string
const escapedPrompt = systemPrompt
    .replace(/\\/g, '\\\\')
    .replace(/"""/g, '\\"\\"\\"');

await pyodide.runPythonAsync(`
session = create_session(model_id="${modelId}")
session.set_system_prompt("""${escapedPrompt}""")
await session.initialize()
`);
```

## Error Handling Pattern

```javascript
async function initChat() {
    const steps = [
        { id: 'webgpu', fn: checkWebGPU },
        { id: 'pyodide', fn: loadPyodide },
        { id: 'model', fn: loadModel },
        { id: 'amplifier', fn: initAmplifier }
    ];
    
    for (const step of steps) {
        try {
            updateLoadStep(step.id, 'loading');
            await step.fn();
            updateLoadStep(step.id, 'done');
        } catch (error) {
            updateLoadStep(step.id, 'error');
            showError(`Failed at ${step.id}: ${error.message}`);
            return; // Stop initialization
        }
    }
    
    showChatUI();
}
```

## Timing Expectations

| Step | First Load | Cached |
|------|------------|--------|
| WebGPU check | <100ms | <100ms |
| Pyodide load | 5-10s | 2-3s |
| Package install | 3-5s | 1-2s |
| Model download | 1-5min | 5-15s |
| Session create | <1s | <1s |
| **Total** | **2-6 min** | **10-30s** |

## Parallel Loading (Advanced)

For faster initialization, load Pyodide and WebLLM model in parallel:

```javascript
async function initParallel() {
    // Start both loads
    const pyodidePromise = loadPyodide();
    const modelPromise = loadWebLLMModel();
    
    // Wait for Pyodide first (needed for setup)
    await pyodidePromise;
    await installPackages();
    await installAmplifierCore();
    
    // Wait for model
    await modelPromise;
    
    // Now set up bridges and create session
    await setupBridges();
    await createSession();
}
```

This can reduce total init time by 30-50%.
