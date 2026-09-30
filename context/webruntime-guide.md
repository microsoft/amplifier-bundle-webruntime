# Browser Amplifier Guide

This document provides context for AI assistants working with browser-based Amplifier applications.

---

## The New Architecture: AmplifierBrowser

**Browser Amplifier now has a simple facade that handles all complexity internally.**

### Before (Complex - 9 failure points)
```html
<!-- OLD: Manual wheel installation, bridge setup, etc. -->
<script id="amplifier-wheel-b64">...</script>
<script id="amplifier-browser-py">...</script>
<!-- 100+ lines of initialization code -->
```

### After (Simple - 1 failure point)
```html
<!-- NEW: Single JS file handles everything -->
<script src="amplifier-browser.js"></script>
<script type="module">
  import { CreateMLCEngine } from 'https://esm.run/@mlc-ai/web-llm';
  window.CreateMLCEngine = CreateMLCEngine;
  
  const amp = new AmplifierBrowser({
    model: 'Phi-3.5-mini-instruct-q4f16_1-MLC',
    onProgress: (stage, pct, msg) => console.log(msg)
  });
  
  await amp.init();
  const result = await amp.execute('Hello!');
</script>
```

---

## How to Build Browser Amplifier Apps

### Step 1: Get the amplifier-browser.js file

**Option A: Build from source (recommended)**
```bash
cd amplifier-bundle-browser
python scripts/build-bundle.py \
  --core-wheel /path/to/amplifier_core-X.X.X-py3-none-any.whl \
  --foundation-wheel /path/to/amplifier_foundation-X.X.X-py3-none-any.whl
```

This generates `dist/amplifier-browser.js` with all assets embedded.

**Option B: Use pre-built (if available)**
Copy `dist/amplifier-browser.js` from the bundle.

### Step 2: Create your HTML

**For server-based apps:**
```html
<script src="amplifier-browser.js"></script>
```

**For standalone/portable HTML:**
```html
<script>
/* Paste contents of amplifier-browser.js here */
</script>
```

### Step 3: Initialize and use

```javascript
const amp = new AmplifierBrowser({
  model: 'Phi-3.5-mini-instruct-q4f16_1-MLC',
  systemPrompt: 'You are a helpful assistant.',
  onProgress: (stage, percent, message) => updateUI(stage, percent, message),
  onError: (error) => showError(error)
});

await amp.init();

// Simple execution
const result = await amp.execute('Hello!');
console.log(result.content);

// Streaming execution
await amp.executeStreaming('Tell me a story', (chunk) => {
  if (chunk.type === 'content' || chunk.type === 'delta') {
    appendToChat(chunk.delta || chunk.content);
  }
});
```

---

## What AmplifierBrowser Handles Internally

You do NOT need to worry about:

| Complexity | Handled By |
|------------|------------|
| Pyodide loading | `AmplifierBrowser.init()` |
| micropip installation | `AmplifierBrowser.init()` |
| Wheel installation with `deps=False` | `AmplifierBrowser.init()` |
| Wheel filename format | Embedded with correct names |
| JS bridge registration order | `AmplifierBrowser.init()` |
| `globalThis` vs `pyodide.globals` | Handled correctly |
| amplifier_browser.py loading | Embedded and auto-loaded |
| Session creation | `AmplifierBrowser.init()` |

---

## API Reference

### Constructor Options

```typescript
new AmplifierBrowser({
  // Required for WebLLM
  model: 'Phi-3.5-mini-instruct-q4f16_1-MLC',
  
  // Optional
  systemPrompt: 'You are a helpful assistant.',
  onProgress: (stage, percent, message) => {},
  onError: (error) => {},
  debug: false,
  
  // Advanced: Load Amplifier bundle
  bundle: './my-bundle.yaml',
  // or
  bundleContent: '---\nbundle:\n...',
  
  // Advanced: Skip WebLLM (for API providers)
  skipWebLLM: false,

  // Required to approve any tool call
  approveToolCall: async ({ name, arguments, prompt }) => {
    return window.confirm(
      `Allow tool call "${name}" with arguments:\n${JSON.stringify(arguments, null, 2)}`
    ) === true;
  },
});
```

The runtime validates every tool call against its `ToolSpec` and permits at
most one tool execution per user request. Every tool call is denied unless
`approveToolCall` is a function that resolves to exactly `true` for that
invocation; missing callbacks, non-functions, malformed arguments, and callback
failures deny the call. Web fetches omit credentials and block same-origin
requests and redirects.

### Methods

| Method | Description |
|--------|-------------|
| `init()` | Initialize runtime (async) |
| `execute(prompt)` | Send message, get complete response (async) |
| `executeStreaming(prompt, onChunk)` | Send message with streaming (async) |
| `setSystemPrompt(prompt)` | Update system prompt |
| `getHistory()` | Get conversation history (async) |
| `clearHistory()` | Clear history (async) |
| `registerTool(pythonCode)` | Add custom tool (async) |
| `dispose()` | Clean up resources (async) |

### Properties

| Property | Description |
|----------|-------------|
| `isReady` | Whether init() completed |
| `isExecuting` | Whether a prompt is running |
| `sessionId` | Current session ID |

### Error Codes

| Code | Meaning | Recoverable |
|------|---------|-------------|
| `WEBGPU_NOT_SUPPORTED` | Browser lacks WebGPU | No |
| `PYODIDE_LOAD_FAILED` | Python runtime failed | Retry |
| `WHEEL_INSTALL_FAILED` | Amplifier install failed | Retry |
| `MODEL_LOAD_FAILED` | WebLLM model failed | Try smaller model |
| `EXECUTION_FAILED` | Prompt failed | Retry |
| `NOT_INITIALIZED` | Called before init() | Call init() |

---

## Templates

Use the template in `templates/quickstart.html` as a starting point.

---

## CRITICAL: What NOT to Do

### Never read binary/base64 files into context

```bash
# ❌ FATAL - causes session timeout
cat amplifier-browser.js  # If it contains base64
cat *.whl
cat *.wasm
```

**Why:** The JS file contains ~270KB of embedded base64. Reading it into LLM context causes timeouts.

**Instead:** Just reference the file, don't read it.

### Never manually handle wheels or bridges

```javascript
// ❌ OLD WAY - Don't do this anymore
pyodide.FS.writeFile('/tmp/wheel.whl', bytes);
await micropip.install('emfs:/tmp/wheel.whl', deps=False);
globalThis.js_llm_complete = ...;
```

**Instead:** Use `AmplifierBrowser` - it handles all of this.

---

## Browser Requirements

- **Chrome 113+** or **Edge 113+** (recommended)
- **Safari 18+** (macOS Sonoma+)
- **Firefox** (behind flag: `dom.webgpu.enabled`)

GPU memory requirements:
- Small models (1-3B): 4GB VRAM
- Medium models (7-8B): 8GB VRAM
- Large models (13B+): 16GB+ VRAM

---

## Troubleshooting

### "WebGPU not supported"

Use Chrome 113+ or Edge 113+. Safari 18+ also works on macOS.

### "Model load failed" / "Out of memory"

Try a smaller model:
```javascript
new AmplifierBrowser({ model: 'Llama-3.2-1B-Instruct-q4f16_1-MLC' })
```

### "Not initialized"

Call `init()` before other methods:
```javascript
const amp = new AmplifierBrowser({...});
await amp.init();  // MUST call this first
await amp.execute('Hello');
```

---

## Advanced: Custom Tools

```javascript
await amp.registerTool(`
class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"
    
    def get_spec(self) -> ToolSpec:
        return ToolSpec(
            name="calculator",
            description="Evaluate math expressions",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"}
                },
                "required": ["expression"]
            }
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        expr = kwargs.get("expression", "")
        try:
            result = eval(expr)
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, output=str(e))

session.register_tool(CalculatorTool())
`);
```

All tools require an `approveToolCall` callback that returns exactly `true` for
the specific invocation.

---

## Advanced: Loading Bundles

```javascript
const amp = new AmplifierBrowser({
  bundle: './my-assistant.yaml',  // Fetch from URL
  onProgress: (stage, pct, msg) => updateUI(stage, pct, msg)
});

// Or inline:
const amp = new AmplifierBrowser({
  bundleContent: `
---
bundle:
  name: my-assistant
  version: 1.0.0
---
# My Assistant
You are a specialized assistant for...
  `
});
```
