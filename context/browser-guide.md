# Browser Amplifier Guide

This document provides context for AI assistants working with browser-based Amplifier applications.

---

## IMPORTANT: Purpose of This Bundle

**This bundle is for building Amplifier applications that run in browsers using Pyodide.**

It is **NOT** for:
- Raw JavaScript WebLLM apps
- Pure JS chat interfaces without Amplifier
- Standalone LLM demos that bypass Amplifier

### The Default Architecture

When someone asks for "WebLLM in browser", "browser AI", or "local LLM chat", the answer is:

```
Amplifier + Pyodide + WebLLM provider
```

**NOT** raw JavaScript calling WebLLM directly.

### Why Amplifier in Browser?

Using Amplifier (via Pyodide) instead of raw JavaScript provides:
- **Session management** - Conversation history, context handling
- **Tool system** - Browser-storage, todo, and custom tools
- **Provider abstraction** - Switch between WebLLM, OpenAI, Anthropic seamlessly
- **Hooks** - Logging, approval gates, observability
- **Consistency** - Same Amplifier patterns work in CLI and browser

### No Exceptions for "Demos" or "Simple" Apps

**Even demos should use Amplifier + Pyodide.** Here's why:

1. **Demos become real apps** - What starts as a demo often grows into production code
2. **Teach the right patterns** - Demos should demonstrate the correct architecture
3. **Amplifier CAN be simple** - A single-file Amplifier app is still simple and portable
4. **Raw JS demos are trivial** - Anyone can ask ChatGPT for raw JS; this bundle exists for Amplifier

**The only time to use raw JavaScript is when the user EXPLICITLY requests it with phrases like "pure JavaScript", "no Python", or "no Amplifier".**

---

## FATAL: Never Read Binary/Encoded Data Into Context

**This WILL cause timeouts and session failures.**

```bash
# ❌ FATAL - dumps 100KB+ of base64 into LLM context, causing timeout
base64 -w0 file.whl > /tmp/encoded.b64
cat /tmp/encoded.b64   # NEVER DO THIS

# ❌ ALSO FATAL - same problem
cat /path/to/file.wasm
cat /path/to/large-base64-file.txt
read_file on any .whl, .wasm, .b64, or minified .js file
```

**Why this kills sessions:** LLM context has token limits. Dumping 100KB of base64 (133K+ tokens) bloats the request to 500KB+, causing 5-minute timeouts.

```bash
# ✅ CORRECT - Write directly to output file, never read back
base64 -w0 file.whl >> output.html

# ✅ CORRECT - Use heredoc with inline base64
cat >> output.html << 'EOF'
<script id="data" type="text/plain">
EOF
base64 -w0 file.whl >> output.html
echo '</script>' >> output.html

# ✅ CORRECT - Check size BEFORE any cat/read
ls -lh file.txt   # If > 10KB, don't cat it
wc -c file.txt    # Check byte count
```

**Rule:** The LLM doesn't need to "see" binary data. It just needs to write code that references it.

---

## CRITICAL: Read This First!

**Browser Amplifier requires THREE components, not one:**

```
┌─────────────────────────────────────────────────────────────────┐
│  YOUR HTML/JS APP                                               │
│       ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  amplifier-browser module (Python adapter layer)         │   │
│  │  • create_session() factory                              │   │
│  │  • WebGPUProvider (bridges to JS WebLLM)                 │   │
│  │  • BrowserAmplifierSession                               │   │
│  │  • Browser-native tools (todo, web)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  amplifier-core wheel (the kernel)                       │   │
│  │  • Provider, Tool, Orchestrator protocols                │   │
│  │  • Message types, ChatRequest, ChatResponse              │   │
│  │  • HookRegistry, events                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pyodide (Python WASM runtime)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Quick Start Checklist

Before writing ANY browser Amplifier code, verify you have:

- [ ] **TWO embedded assets** (not just the wheel!):
  1. `amplifier-core` wheel (base64-encoded `.whl` file)
  2. `amplifier-browser` module (Python source code, base64-encoded)

- [ ] **Correct wheel filename** in Pyodide filesystem:
  ```
  ✗ WRONG: /tmp/amplifier_core.whl
  ✓ RIGHT: /tmp/amplifier_core-1.0.0-py3-none-any.whl
  ```

- [ ] **micropip with deps=False** (to avoid PyYAML conflict):
  ```python
  # MUST use Python, not JS proxy, to pass deps=False
  await pyodide.runPythonAsync(`
      import micropip
      await micropip.install('emfs:/tmp/amplifier_core-1.0.0-py3-none-any.whl', deps=False)
  `)
  ```

- [ ] **JS bridge functions registered** before loading amplifier-browser:
  ```javascript
  // MUST use globalThis, NOT pyodide.globals.set()
  // Python's `from js import X` looks in globalThis, not pyodide.globals
  globalThis.js_llm_complete = async (messagesJson, toolsJson) => {...};
  globalThis.js_llm_stream = async (messagesJson, onChunk) => {...};
  globalThis.js_web_fetch = async (url) => {...};
  ```

- [ ] **Use create_session()** factory (don't wire up internals manually):
  ```python
  session = create_session(model_id="Phi-3.5-mini-instruct-q4f16_1-MLC")
  session.set_system_prompt("You are a helpful assistant.")
  await session.initialize()
  response = await session.execute("Hello!")
  ```

### Common Errors Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find 'Coordinator'` | Wrong class name | Use `ModuleCoordinator` from `amplifier_core.coordinator` |
| `Cannot import 'Message' from models` | Wrong module | Use `amplifier_core.message_models` |
| `pyyaml>=6.0.3 but 6.0.2 installed` | Pyodide bundles old PyYAML | Use `deps=False` when installing |
| `micropip got unexpected kwarg 'deps'` | JS proxy limitation | Use `pyodide.runPythonAsync()` with Python code |
| `Could not parse wheel metadata` | Short wheel filename | Use full: `name-version-py3-none-any.whl` |
| `js_llm_complete is not defined` | Wrong registration method OR missing bridge | Use `globalThis.js_llm_complete = ...` (NOT `pyodide.globals.set()`) |

### The amplifier-browser Module

**This module is ESSENTIAL for browser apps.** It's located at `src/amplifier_browser.py` in this bundle.

The module provides browser-compatible wrappers around amplifier-core:

| Component | Purpose |
|-----------|---------|
| `WebGPUProvider` | Provider that bridges to JS WebLLM via `js_llm_complete`/`js_llm_stream` |
| `BrowserAmplifierSession` | Full session with orchestrator, tools, context |
| `BrowserContextManager` | In-memory context management |
| `BrowserOrchestrator` | Orchestrator with manual tool calling (WebLLM's native tool calling is WIP) |
| `BrowserTodoTool` | Browser-native todo tool |
| `BrowserWebTool` | Web fetch tool using `js_web_fetch` bridge |
| `create_session()` | Factory function - **USE THIS** |

**To embed it:**
1. Base64-encode the Python source: `base64 < src/amplifier_browser.py`
2. Put in a `<script id="amplifier-browser-py" type="text/plain">` tag
3. Load it after installing amplifier-core:
   ```javascript
   const moduleB64 = document.getElementById('amplifier-browser-py').textContent.trim();
   const moduleCode = atob(moduleB64);
   await pyodide.runPythonAsync(moduleCode);
   ```

---

## What is Browser Amplifier?

Browser Amplifier runs the full Amplifier stack (amplifier-core, tools, providers) inside a web browser using:

- **Pyodide**: Python interpreter compiled to WebAssembly
- **amplifier-core**: The Amplifier kernel running in Pyodide
- **Provider bridge**: JavaScript↔Python communication for LLM calls

This enables:
- Fully client-side AI applications
- Offline-capable AI (with WebLLM)
- No server infrastructure required
- User data stays in browser

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  User's Browser                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │  Your Web App   │      │  LLM Provider               │  │
│  │  (HTML/JS/CSS)  │      │  ┌─────────────────────┐    │  │
│  └────────┬────────┘      │  │ WebLLM (local GPU)  │    │  │
│           │               │  ├─────────────────────┤    │  │
│           ▼               │  │ OpenAI API (fetch)  │    │  │
│  ┌─────────────────┐      │  ├─────────────────────┤    │  │
│  │  Pyodide        │◄────►│  │ Anthropic API       │    │  │
│  │  (Python WASM)  │      │  └─────────────────────┘    │  │
│  │                 │      └─────────────────────────────┘  │
│  │  ┌───────────┐  │                                       │
│  │  │ amplifier │  │      ┌─────────────────────────────┐  │
│  │  │   -core   │  │      │  Browser Storage            │  │
│  │  └───────────┘  │      │  ├── localStorage           │  │
│  └─────────────────┘      │  └── IndexedDB              │  │
│                           └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Available Tools

### tool-browser-storage

Browser-specific storage tool using localStorage and IndexedDB.

**Operations:**
- `storage_get(key)` - Retrieve a value
- `storage_set(key, value)` - Store a value
- `storage_delete(key)` - Remove a value
- `storage_list()` - List all keys
- `storage_clear()` - Clear all storage

**Limits:**
- localStorage: ~5-10MB per origin
- IndexedDB: Much larger (browser-dependent)

### tool-todo

Standard todo tool works in browser (in-memory state).

### NOT Available in Browser

- `tool-filesystem` - No filesystem access
- `tool-bash` - No shell access
- `tool-search` (grep/glob) - No filesystem to search

---

## Provider Options

### Local Inference (WebLLM)

Runs LLMs directly in browser using WebGPU.

**Requirements:**
- WebGPU-capable browser (Chrome 113+, Edge 113+)
- Sufficient VRAM (4GB+ for small models)
- Initial model download (2-8GB depending on model)

**Pros:**
- Fully offline after initial download
- Complete privacy (data never leaves device)
- No API costs

**Cons:**
- Requires modern GPU
- Large initial download
- Limited model selection

### API Providers (OpenAI, Anthropic)

Calls cloud APIs via browser fetch.

**Requirements:**
- User provides API key
- Network connectivity
- CORS-compatible endpoints

**Pros:**
- Powerful models (GPT-4, Claude)
- No local hardware requirements
- Fast responses

**Cons:**
- Requires API key (user must provide)
- Costs money per request
- Requires network

---

## Browser Constraints

### No Filesystem

Browser has no access to local filesystem. Use:
- `tool-browser-storage` for persistent data
- In-memory state for session data
- User file picker for explicit file access

### CORS Restrictions

Browser enforces Cross-Origin Resource Sharing:
- API calls must go to CORS-enabled endpoints
- OpenAI and Anthropic APIs support CORS
- Custom backends need CORS headers

### Memory Limits

Browser tabs have limited memory:
- Typical limit: 2-4GB per tab
- WebLLM models consume significant memory
- Context window size affects memory usage

### Storage Quotas

Browser storage has limits:
- localStorage: ~5-10MB
- IndexedDB: Larger but browser-dependent
- Can be cleared by user or browser

### Content Security Policy

Some sites restrict JavaScript execution:
- May block inline scripts
- May block external script sources
- May block eval() (affects some libraries)

---

## Installing amplifier-core in Pyodide

**IMPORTANT:** `amplifier-core` is NOT on PyPI. You cannot use `micropip.install('amplifier-core')`.

Instead, use one of these patterns depending on your app type:

### Pattern 1: Embedded Wheel (Single-File HTML)

For portable single-file HTML apps, embed the wheel as base64:

```html
<!-- Embed wheel as base64 in a script tag -->
<script id="amplifier-wheel-b64" type="text/plain">
UEsDBBQAAAAIAAAAQlC3l5BdFwMAAFINAAAaAAAAYW1wbGlmaWVyX2NvcmUvX19pbml0X18ucHk...
</script>
```

```javascript
async function installAmplifierCore(pyodide) {
    // 1. Get base64-encoded wheel from HTML
    const wheelB64 = document.getElementById('amplifier-wheel-b64').textContent.trim();
    
    // 2. Decode to bytes
    const wheelBytes = Uint8Array.from(atob(wheelB64), c => c.charCodeAt(0));
    
    // 3. Write to Pyodide's virtual filesystem
    pyodide.FS.writeFile('/tmp/amplifier_core-1.0.0-py3-none-any.whl', wheelBytes);
    
    // 4. Install dependencies from PyPI, then amplifier-core from emfs:
    const micropip = pyodide.pyimport('micropip');
    await micropip.install(['pydantic', 'pyyaml', 'typing-extensions']);
    await micropip.install('emfs:/tmp/amplifier_core-1.0.0-py3-none-any.whl');
}
```

**Key insight:** The `emfs:` protocol tells micropip to install from Pyodide's Emscripten virtual filesystem.

### Pattern 2: Static Asset (Web Apps)

For web apps with multiple files, serve the wheel as a static asset:

```
project/
├── index.html
├── app.js
└── assets/
    └── amplifier_core-1.0.0-py3-none-any.whl
```

```javascript
async function installAmplifierCore(pyodide) {
    const micropip = pyodide.pyimport('micropip');
    
    // Install dependencies from PyPI
    await micropip.install(['pydantic', 'pyyaml', 'typing-extensions']);
    
    // Install amplifier-core from local asset (same origin)
    await micropip.install('/assets/amplifier_core-1.0.0-py3-none-any.whl');
}
```

**Note:** This requires serving from a web server (won't work from `file://` due to CORS).

### Pattern 3: Service Worker Cache (Production PWAs)

For production apps needing offline support:

```javascript
// sw.js - Cache wheels with cache-first strategy
self.addEventListener('fetch', (event) => {
    if (event.request.url.endsWith('.whl')) {
        event.respondWith(
            caches.match(event.request).then(cached => 
                cached || fetch(event.request).then(response => {
                    const clone = response.clone();
                    caches.open('amplifier-wheels-v1').then(cache => 
                        cache.put(event.request, clone)
                    );
                    return response;
                })
            )
        );
    }
});
```

### Which Pattern to Use?

| Scenario | Pattern | Why |
|----------|---------|-----|
| Single HTML file, sharing via email/Slack | Embedded base64 | Self-contained, no server needed |
| Web app with build step | Static asset | Cleaner, cached by browser |
| Production PWA, offline-first | Service worker | Full cache control, updates independently |

---

## CRITICAL: Pyodide Compatibility Issues

### PyYAML Version Conflict

**This is the #1 cause of installation failures. Read carefully.**

**The Problem:**
- Pyodide 0.27.x bundles `pyyaml==6.0.2` (built-in, CANNOT be upgraded)
- `amplifier-core` requires `pyyaml>=6.0.3` in its metadata
- Running `micropip.install()` with dependencies will FAIL:

```
ValueError: Requested 'pyyaml>=6.0.3', but pyyaml==6.0.2 is already installed
```

**The Solution:** Install amplifier-core **without dependency resolution** using `deps=False`:

```python
# Install safe dependencies first
await micropip.install(['pydantic', 'typing-extensions'])

# Install amplifier-core WITHOUT checking dependencies
await micropip.install('emfs:/tmp/amplifier_core.whl', deps=False)
```

**Why this is safe:** The 6.0.2 vs 6.0.3 difference is a minor patch version. There are NO runtime incompatibilities - amplifier-core works perfectly fine with PyYAML 6.0.2. This is purely a package metadata conflict.

### micropip API: JavaScript vs Python

**CRITICAL:** The micropip API behaves differently when called from JavaScript vs Python.

```javascript
// ❌ WRONG - JavaScript object syntax does NOT work for micropip options
const micropip = pyodide.pyimport('micropip');
await micropip.install('package.whl', {deps: false});  // FAILS!

// ❌ ALSO WRONG - Named arguments don't work from JS
await micropip.install('package.whl', undefined, false);  // FAILS!
```

```javascript
// ✅ CORRECT - Run micropip entirely from Python
await pyodide.runPythonAsync(`
    import micropip
    await micropip.install('emfs:/tmp/amplifier_core.whl', deps=False)
`);
```

**Rule of thumb:** For any micropip operation with options (like `deps=False`), use `pyodide.runPythonAsync()` with Python code, not the JavaScript micropip proxy.

### Putting It Together: Correct Installation

```javascript
async function installAmplifierCore(pyodide) {
    // 1. Decode embedded wheel and write to virtual filesystem
    const wheelB64 = document.getElementById('amplifier-wheel-b64').textContent.trim();
    const wheelBytes = Uint8Array.from(atob(wheelB64), c => c.charCodeAt(0));
    pyodide.FS.writeFile('/tmp/amplifier_core.whl', wheelBytes);
    
    // 2. Install everything via Python (NOT JavaScript micropip proxy)
    await pyodide.runPythonAsync(`
        import micropip
        
        # Install dependencies that ARE compatible with Pyodide
        await micropip.install(['pydantic', 'typing-extensions'])
        
        # Install amplifier-core WITHOUT dependency checking
        # This avoids the pyyaml 6.0.2 vs 6.0.3 conflict
        await micropip.install('emfs:/tmp/amplifier_core.whl', deps=False)
        
        print("amplifier-core installed successfully!")
    `);
}
```

---

## Complete Working Example

This is a **verified, copy-paste working** single-file HTML that includes everything:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amplifier + WebLLM Demo</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: system-ui, sans-serif; 
            background: #1a1a2e; 
            color: #eee;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        #status { 
            padding: 20px; 
            text-align: center; 
            background: #16213e;
        }
        #progress-container {
            width: 80%;
            max-width: 400px;
            margin: 10px auto;
            background: #0f3460;
            border-radius: 10px;
            overflow: hidden;
        }
        #progress-bar {
            height: 20px;
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            width: 0%;
            transition: width 0.3s;
        }
        #chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
            padding: 20px;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 80%;
        }
        .user { 
            background: #e94560; 
            margin-left: auto; 
        }
        .assistant { 
            background: #16213e; 
        }
        #input-container {
            display: flex;
            gap: 10px;
            padding: 10px 0;
        }
        #user-input {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: #16213e;
            color: #eee;
            font-size: 16px;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: #e94560;
            color: white;
            cursor: pointer;
            font-size: 16px;
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div id="status">
        <h2>Loading Amplifier + WebLLM...</h2>
        <div id="progress-container">
            <div id="progress-bar"></div>
        </div>
        <p id="status-text">Initializing...</p>
    </div>
    
    <div id="chat-container" class="hidden">
        <div id="messages"></div>
        <div id="input-container">
            <input type="text" id="user-input" placeholder="Type a message..." />
            <button id="send-btn">Send</button>
        </div>
    </div>

    <!-- EMBEDDED AMPLIFIER-CORE WHEEL (base64) -->
    <!-- Generate this with: python scripts/build-wheel.py --source ~/repos/amplifier-core --output ./dist --html-snippet -->
    <script id="amplifier-wheel-b64" type="text/plain">
    <!-- PASTE YOUR BASE64 WHEEL HERE -->
    </script>

    <script src="https://cdn.jsdelivr.net/pyodide/v0.27.0/full/pyodide.js"></script>
    <script type="module">
        import { CreateMLCEngine } from 'https://esm.run/@mlc-ai/web-llm';
        
        const MODEL_ID = 'Phi-3.5-mini-instruct-q4f16_1-MLC';
        
        let pyodide = null;
        let webllmEngine = null;
        
        // UI Elements
        const statusDiv = document.getElementById('status');
        const statusText = document.getElementById('status-text');
        const progressBar = document.getElementById('progress-bar');
        const chatContainer = document.getElementById('chat-container');
        const messagesDiv = document.getElementById('messages');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        
        function updateProgress(pct, text) {
            progressBar.style.width = `${pct}%`;
            statusText.textContent = text;
        }
        
        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            div.textContent = content;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        async function init() {
            try {
                // 1. Load Pyodide
                updateProgress(10, 'Loading Python runtime...');
                pyodide = await loadPyodide();
                
                // 2. Load micropip
                updateProgress(20, 'Loading package manager...');
                await pyodide.loadPackage('micropip');
                
                // 3. Install amplifier-core (with deps=False to avoid PyYAML conflict)
                updateProgress(30, 'Installing Amplifier...');
                
                // Decode and write wheel to virtual filesystem
                const wheelB64 = document.getElementById('amplifier-wheel-b64').textContent.trim();
                if (!wheelB64 || wheelB64.includes('PASTE YOUR')) {
                    throw new Error('Please embed the amplifier-core wheel base64. See scripts/build-wheel.py');
                }
                const wheelBytes = Uint8Array.from(atob(wheelB64), c => c.charCodeAt(0));
                pyodide.FS.writeFile('/tmp/amplifier_core.whl', wheelBytes);
                
                // Install via Python to use deps=False
                await pyodide.runPythonAsync(`
                    import micropip
                    await micropip.install(['pydantic', 'typing-extensions'])
                    await micropip.install('emfs:/tmp/amplifier_core.whl', deps=False)
                    print("amplifier-core installed!")
                `);
                
                // 4. Load WebLLM model
                updateProgress(50, 'Loading AI model (this may take a few minutes)...');
                webllmEngine = await CreateMLCEngine(MODEL_ID, {
                    initProgressCallback: (progress) => {
                        const pct = 50 + Math.round(progress.progress * 40);
                        updateProgress(pct, `Loading model: ${Math.round(progress.progress * 100)}%`);
                    }
                });
                
                // 5. Set up the bridge function for Amplifier to call WebLLM
                updateProgress(95, 'Setting up Amplifier session...');
                
                // Register the JS completion function that Python will call
                // MUST use globalThis for Python's `from js import X` to work
                globalThis.js_webllm_complete = async (messagesJson) => {
                    const messages = JSON.parse(messagesJson);
                    const response = await webllmEngine.chat.completions.create({
                        messages: messages,
                        temperature: 0.7,
                        max_tokens: 1024
                    });
                    return JSON.stringify({
                        content: response.choices[0].message.content,
                        usage: response.usage
                    });
                });
                
                // Initialize Amplifier session with WebLLM provider bridge
                await pyodide.runPythonAsync(`
                    import json
                    from amplifier_core import Coordinator, Session
                    from amplifier_core.types import Message, ProviderResponse
                    
                    # Create a simple WebLLM provider that bridges to JavaScript
                    class WebLLMBridgeProvider:
                        def __init__(self):
                            self.model_id = "${MODEL_ID}"
                        
                        async def complete(self, messages, **kwargs):
                            import js
                            # Convert messages to JSON and call JS
                            msgs_json = json.dumps([{"role": m.role, "content": m.content} for m in messages])
                            result_json = await js.js_webllm_complete(msgs_json)
                            result = json.loads(result_json)
                            return ProviderResponse(
                                content=result["content"],
                                model=self.model_id,
                                usage=result.get("usage", {})
                            )
                    
                    # Create coordinator and session
                    coordinator = Coordinator()
                    provider = WebLLMBridgeProvider()
                    session = Session(coordinator=coordinator)
                    
                    print("Amplifier session ready!")
                `);
                
                // Ready!
                updateProgress(100, 'Ready!');
                setTimeout(() => {
                    statusDiv.classList.add('hidden');
                    chatContainer.classList.remove('hidden');
                    userInput.focus();
                }, 500);
                
            } catch (error) {
                console.error('Initialization error:', error);
                statusText.textContent = `Error: ${error.message}`;
                statusText.style.color = '#e94560';
            }
        }
        
        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            
            userInput.value = '';
            sendBtn.disabled = true;
            addMessage('user', text);
            
            try {
                // Use Amplifier session to handle the message
                const response = await pyodide.runPythonAsync(`
                    import json
                    import asyncio
                    
                    user_msg = Message(role="user", content=${JSON.stringify(text)})
                    session.context.add_message(user_msg)
                    
                    response = await provider.complete(session.context.get_messages())
                    
                    assistant_msg = Message(role="assistant", content=response.content)
                    session.context.add_message(assistant_msg)
                    
                    response.content
                `);
                
                addMessage('assistant', response);
            } catch (error) {
                console.error('Chat error:', error);
                addMessage('assistant', `Error: ${error.message}`);
            }
            
            sendBtn.disabled = false;
            userInput.focus();
        }
        
        // Event listeners
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Start initialization
        init();
    </script>
</body>
</html>
```

**To use this example:**
1. Build the wheel: `python scripts/build-wheel.py --source ~/repos/amplifier-core --output ./dist`
2. Copy contents of `./dist/amplifier_core-*.b64.txt`
3. Paste into the `<script id="amplifier-wheel-b64">` tag
4. Open in a WebGPU-capable browser (Chrome/Edge 113+)

---

## Initialization Patterns

### Basic Initialization (Web App)

```javascript
async function initAmplifier() {
    // 1. Load Pyodide
    const pyodide = await loadPyodide();
    
    // 2. Load micropip
    await pyodide.loadPackage('micropip');
    const micropip = pyodide.pyimport('micropip');
    
    // 3. Install dependencies + amplifier-core
    await micropip.install(['pydantic', 'pyyaml', 'typing-extensions']);
    await micropip.install('/assets/amplifier_core-1.0.0-py3-none-any.whl');
    
    // 4. Set up provider bridge
    // (varies by provider - see provider-specific examples)
    
    // 5. Initialize session
    await pyodide.runPythonAsync(`
        from amplifier_core import AmplifierSession
        # Session setup code
    `);
    
    return pyodide;
}
```

### Basic Initialization (Single-File HTML)

```javascript
async function initAmplifier() {
    // 1. Load Pyodide
    const pyodide = await loadPyodide();
    
    // 2. Load micropip
    await pyodide.loadPackage('micropip');
    const micropip = pyodide.pyimport('micropip');
    
    // 3. Install dependencies from PyPI
    await micropip.install(['pydantic', 'pyyaml', 'typing-extensions']);
    
    // 4. Install amplifier-core from embedded wheel
    const wheelB64 = document.getElementById('amplifier-wheel-b64').textContent.trim();
    const wheelBytes = Uint8Array.from(atob(wheelB64), c => c.charCodeAt(0));
    pyodide.FS.writeFile('/tmp/amplifier_core-1.0.0-py3-none-any.whl', wheelBytes);
    await micropip.install('emfs:/tmp/amplifier_core-1.0.0-py3-none-any.whl');
    
    // 5. Set up provider bridge
    // (varies by provider - see provider-specific examples)
    
    // 6. Initialize session
    await pyodide.runPythonAsync(`
        from amplifier_core import AmplifierSession
        # Session setup code
    `);
    
    return pyodide;
}
```

### With Loading Progress

```javascript
async function initWithProgress(onProgress) {
    onProgress('Loading Python runtime...', 0);
    const pyodide = await loadPyodide();
    
    onProgress('Installing packages...', 30);
    await pyodide.loadPackage('micropip');
    const micropip = pyodide.pyimport('micropip');
    await micropip.install(['pydantic', 'pyyaml', 'typing-extensions']);
    
    onProgress('Installing Amplifier...', 50);
    // Use appropriate pattern: static asset or embedded wheel
    await micropip.install('/assets/amplifier_core-1.0.0-py3-none-any.whl');
    
    onProgress('Setting up provider...', 70);
    // Provider setup...
    
    onProgress('Ready!', 100);
    return pyodide;
}
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `WebGPU not supported` | Browser lacks WebGPU | Use Chrome 113+ or API provider |
| `Out of memory` | Model too large | Use smaller model or quantization |
| `CORS error` | API blocks browser requests | Use CORS-enabled endpoint |
| `micropip.install failed` | Package not available | Check package name and availability |
| `Pyodide loading failed` | Network issue or CSP | Check network and CSP headers |

### Error Recovery

```javascript
try {
    await initAmplifier();
} catch (error) {
    if (error.message.includes('WebGPU')) {
        // Fall back to API provider
        await initWithAPIProvider();
    } else if (error.message.includes('memory')) {
        // Try smaller model
        await initWithSmallerModel();
    } else {
        // Show user-friendly error
        showError('Failed to initialize AI. Please try refreshing.');
    }
}
```

---

## Best Practices

### 1. Show Loading Progress

Users expect feedback during the ~10-30 second initialization:

```javascript
const stages = [
    'Loading Python runtime...',
    'Installing packages...',
    'Loading AI model...',
    'Ready!'
];
```

### 2. Handle Offline Gracefully

For WebLLM apps:
- Cache model in browser storage
- Show clear offline/online status
- Queue requests when offline

### 3. Secure API Keys

Never hardcode API keys:

```javascript
// BAD - key exposed in source
const apiKey = 'sk-abc123...';

// GOOD - user provides key
const apiKey = localStorage.getItem('openai_key') || prompt('Enter API key:');
```

### 4. Manage Memory

Monitor and manage memory usage:

```javascript
// Check available memory (Chrome only)
if (navigator.deviceMemory) {
    if (navigator.deviceMemory < 4) {
        console.warn('Low memory device - using smaller model');
    }
}
```

### 5. Provide Fallbacks

Not all users have WebGPU:

```javascript
async function initProvider() {
    if (await checkWebGPUSupport()) {
        return initWebLLM();
    } else {
        console.log('WebGPU not available, using API provider');
        return initAPIProvider();
    }
}
```

---

## Integration Patterns

### Single-File HTML

Everything in one file - great for sharing, demos, quick prototypes.

### ES Module App

Separate JS modules - better for larger applications.

### React/Vue/Svelte Component

Framework integration - for existing web applications.

### Web Worker

Run Amplifier in a worker - keeps UI responsive.

### Service Worker + PWA

Full offline capability - installable web app.

---

## Session Management

### In-Memory Session (Default)

Session state lives only in memory, lost on page refresh.

### Persistent Session

Use browser storage to persist across page loads:

```javascript
// Save session state
const state = await pyodide.runPythonAsync(`
    session.export_state()
`);
localStorage.setItem('amplifier_session', state);

// Restore on next load
const saved = localStorage.getItem('amplifier_session');
if (saved) {
    await pyodide.runPythonAsync(`
        session.import_state('${saved}')
    `);
}
```

---

## Debugging Tips

### Console Logging

Enable verbose logging in development:

```javascript
// Log all Amplifier events
globalThis.debug_log = console.log;
```

### Network Tab

Check for:
- Failed model downloads
- API call errors
- CORS issues

### Memory Profiler

In Chrome DevTools:
- Memory tab shows heap usage
- Identify memory leaks
- Monitor model memory consumption

### Performance Timeline

Check initialization timing:
- Pyodide load time
- Package installation
- Model loading

---

## Advanced Patterns (from amplifier-web)

These patterns are derived from the production amplifier-web project and adapted for browser-based Pyodide implementations.

### Web Worker Architecture

**Run Pyodide in a Web Worker to keep the UI responsive:**

```
┌─────────────────────────────────────────────────────────────┐
│  Main Thread (UI)                                           │
│  ├─ React/Vue/vanilla JS                                   │
│  ├─ State management (Zustand/Redux)                       │
│  └─ postMessage ↔ worker                                   │
├─────────────────────────────────────────────────────────────┤
│  Web Worker                                                 │
│  ├─ Pyodide runtime                                        │
│  ├─ amplifier-core session                                 │
│  └─ Provider bridge (WebLLM or API)                        │
└─────────────────────────────────────────────────────────────┘
```

**Why Web Workers:**
- Python execution doesn't block UI
- Model inference runs in background
- UI stays responsive during long operations
- Clean separation of concerns

**Worker Setup:**

```javascript
// main.js - Main thread
const worker = new Worker('amplifier-worker.js', { type: 'module' });

worker.onmessage = (event) => {
    const message = event.data;
    switch (message.type) {
        case 'content_delta':
            appendToChat(message.delta);
            break;
        case 'tool_call':
            showToolProgress(message.tool_name);
            break;
        case 'approval_request':
            showApprovalModal(message);
            break;
        // ... handle other message types
    }
};

function sendPrompt(text) {
    worker.postMessage({ type: 'prompt', content: text });
}
```

```javascript
// amplifier-worker.js - Web Worker
importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.0/full/pyodide.js');

let pyodide = null;

async function init() {
    pyodide = await loadPyodide();
    await pyodide.loadPackage('micropip');
    await pyodide.runPythonAsync(`
        import micropip
        await micropip.install('amplifier-core')
    `);
    
    // Set up bridge to post messages back to main thread
    // MUST use globalThis for Python's `from js import X` to work
    globalThis.post_to_ui = (msgJson) => {
        self.postMessage(JSON.parse(msgJson));
    });
    
    self.postMessage({ type: 'ready' });
}

self.onmessage = async (event) => {
    const message = event.data;
    if (message.type === 'prompt') {
        await pyodide.runPythonAsync(`
            await session.execute("${message.content.replace(/"/g, '\\"')}")
        `);
    }
};

init();
```

---

### Message Protocol Types

**TypeScript types for Worker ↔ UI communication (adapted from amplifier-web):**

```typescript
// Worker → UI messages
export type WorkerMessage =
    | ContentStartMessage
    | ContentDeltaMessage
    | ContentEndMessage
    | ToolCallMessage
    | ToolResultMessage
    | ApprovalRequestMessage
    | ErrorMessage
    | ReadyMessage;

// UI → Worker messages  
export type UIMessage =
    | PromptMessage
    | ApprovalResponseMessage
    | CancelMessage;

// Streaming content
interface ContentStartMessage {
    type: 'content_start';
    block_type: 'text' | 'thinking' | 'tool_use';
    index: number;
}

interface ContentDeltaMessage {
    type: 'content_delta';
    index: number;
    delta: string;
    block_type?: string;
}

interface ContentEndMessage {
    type: 'content_end';
    index: number;
    content: string;
    block_type?: string;
}

// Tool lifecycle
interface ToolCallMessage {
    type: 'tool_call';
    tool_name: string;
    tool_call_id: string;
    arguments: Record<string, unknown>;
    status: 'pending' | 'running' | 'complete' | 'error';
}

interface ToolResultMessage {
    type: 'tool_result';
    tool_call_id: string;
    output: string;
    success: boolean;
    error?: string;
}

// Approval flow
interface ApprovalRequestMessage {
    type: 'approval_request';
    id: string;
    prompt: string;
    options: string[];
    timeout: number;
    default: string;
}

interface ApprovalResponseMessage {
    type: 'approval_response';
    id: string;
    choice: string;
}

// User input
interface PromptMessage {
    type: 'prompt';
    content: string;
    images?: string[];
}

interface CancelMessage {
    type: 'cancel';
    immediate?: boolean;
}
```

---

### Event-to-Message Mapping

**Map Amplifier events to UI messages (Python side in worker):**

```python
def map_event_to_message(event: str, data: dict) -> dict | None:
    """
    Map Amplifier event to Worker message format.
    Called from hook that observes session events.
    """
    
    # Content block streaming
    if event == "content_block:start":
        block_type = data.get("block_type", "text")
        index = data.get("block_index", 0)
        return {
            "type": "content_start",
            "block_type": block_type,
            "index": index
        }
    
    elif event == "content_block:delta":
        index = data.get("block_index", 0)
        delta = data.get("delta", {})
        text = delta.get("text", "") if isinstance(delta, dict) else str(delta)
        return {
            "type": "content_delta",
            "index": index,
            "delta": text
        }
    
    elif event == "content_block:end":
        index = data.get("block_index", 0)
        block = data.get("block", {})
        content = block.get("text", "") if isinstance(block, dict) else ""
        return {
            "type": "content_end",
            "index": index,
            "content": content
        }
    
    # Tool lifecycle
    elif event == "tool:pre":
        return {
            "type": "tool_call",
            "tool_name": data.get("tool_name", "unknown"),
            "tool_call_id": data.get("tool_call_id", ""),
            "arguments": data.get("tool_input", {}),
            "status": "running"
        }
    
    elif event == "tool:post":
        result = data.get("result", {})
        return {
            "type": "tool_result",
            "tool_call_id": data.get("tool_call_id", ""),
            "output": result.get("output", ""),
            "success": result.get("success", True)
        }
    
    return None
```

**Hook to bridge events to UI:**

```python
import json

class WorkerBridgeHook:
    """Hook that forwards Amplifier events to the UI via postMessage."""
    
    def __init__(self, post_fn):
        self.post_fn = post_fn  # JavaScript function to call
    
    async def __call__(self, event: str, data: dict):
        message = map_event_to_message(event, data)
        if message:
            self.post_fn(json.dumps(message))
        return None  # Don't modify event flow
```

---

### Approval System Pattern

**Async approval handling with timeout (JavaScript side):**

```javascript
class ApprovalManager {
    constructor(worker) {
        this.worker = worker;
        this.pending = new Map();  // id -> { resolve, reject, timer }
        this.cache = new Map();    // prompt hash -> choice (for "always" decisions)
    }
    
    // Called when worker requests approval
    handleRequest(request) {
        const { id, prompt, options, timeout, default: defaultChoice } = request;
        
        // Check cache for "Allow always" decisions
        const cacheKey = this.hashPrompt(prompt, options);
        if (this.cache.has(cacheKey)) {
            this.respond(id, this.cache.get(cacheKey));
            return;
        }
        
        // Show UI and wait for response
        this.showApprovalUI(request);
        
        // Set timeout
        const timer = setTimeout(() => {
            this.respond(id, this.resolveDefault(defaultChoice, options));
            this.hideApprovalUI();
        }, timeout * 1000);
        
        this.pending.set(id, { timer });
    }
    
    // Called when user clicks an option
    userRespond(id, choice) {
        const pending = this.pending.get(id);
        if (pending) {
            clearTimeout(pending.timer);
            this.pending.delete(id);
        }
        
        // Cache "always" decisions
        if (choice.toLowerCase().includes('always')) {
            // Would need to store the original prompt to cache properly
        }
        
        this.respond(id, choice);
        this.hideApprovalUI();
    }
    
    respond(id, choice) {
        this.worker.postMessage({
            type: 'approval_response',
            id: id,
            choice: choice
        });
    }
    
    resolveDefault(defaultAction, options) {
        for (const option of options) {
            const lower = option.toLowerCase();
            if (defaultAction === 'allow' && (lower.includes('allow') || lower.includes('yes'))) {
                return option;
            }
            if (defaultAction === 'deny' && (lower.includes('deny') || lower.includes('no'))) {
                return option;
            }
        }
        return defaultAction === 'deny' ? options[options.length - 1] : options[0];
    }
    
    hashPrompt(prompt, options) {
        return `${prompt}:${options.join(',')}`;
    }
}
```

---

### UI State Management (Zustand Pattern)

**Manage chat state with Zustand (React example):**

```typescript
import { create } from 'zustand';

interface ContentBlock {
    type: 'text' | 'thinking' | 'tool_use';
    content: string;
    isStreaming?: boolean;
    order?: number;
}

interface ToolCall {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    status: 'pending' | 'running' | 'complete' | 'error';
    result?: string;
    order?: number;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: ContentBlock[];
    toolCalls?: ToolCall[];
    timestamp: Date;
}

interface ChatStore {
    messages: Message[];
    isStreaming: boolean;
    
    addUserMessage: (text: string) => void;
    startAssistantMessage: () => void;
    appendToCurrentBlock: (delta: string) => void;
    endCurrentBlock: (content: string) => void;
    addToolCall: (toolCall: ToolCall) => void;
    updateToolCall: (id: string, update: Partial<ToolCall>) => void;
    setStreaming: (streaming: boolean) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
    messages: [],
    isStreaming: false,
    
    addUserMessage: (text) => set((state) => ({
        messages: [...state.messages, {
            id: crypto.randomUUID(),
            role: 'user',
            content: [{ type: 'text', content: text }],
            timestamp: new Date()
        }]
    })),
    
    startAssistantMessage: () => set((state) => ({
        messages: [...state.messages, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: [],
            toolCalls: [],
            timestamp: new Date()
        }],
        isStreaming: true
    })),
    
    appendToCurrentBlock: (delta) => set((state) => {
        const messages = [...state.messages];
        const last = messages[messages.length - 1];
        if (last?.role === 'assistant') {
            const blocks = [...last.content];
            if (blocks.length > 0) {
                blocks[blocks.length - 1] = {
                    ...blocks[blocks.length - 1],
                    content: blocks[blocks.length - 1].content + delta
                };
            }
            messages[messages.length - 1] = { ...last, content: blocks };
        }
        return { messages };
    }),
    
    // ... additional methods
    
    setStreaming: (streaming) => set({ isStreaming: streaming })
}));
```

---

### Timeline Rendering Pattern

**Interleave content blocks and tool calls chronologically:**

```typescript
type TimelineItem =
    | { kind: 'content'; block: ContentBlock; order: number }
    | { kind: 'tool'; toolCall: ToolCall; order: number };

function buildTimeline(message: Message): TimelineItem[] {
    const items: TimelineItem[] = [];
    
    // Add content blocks
    message.content.forEach((block, index) => {
        items.push({
            kind: 'content',
            block,
            order: block.order ?? index
        });
    });
    
    // Add tool calls
    message.toolCalls?.forEach((toolCall, index) => {
        items.push({
            kind: 'tool',
            toolCall,
            order: toolCall.order ?? (1000 + index)
        });
    });
    
    // Sort by order for chronological display
    return items.sort((a, b) => a.order - b.order);
}

// In React component
function MessageBubble({ message }: { message: Message }) {
    const timeline = buildTimeline(message);
    
    return (
        <div className="message">
            {timeline.map((item, i) => (
                item.kind === 'content' 
                    ? <ContentBlockView key={i} block={item.block} />
                    : <ToolCallView key={i} toolCall={item.toolCall} />
            ))}
        </div>
    );
}
```

---

### Tool Call UI Pattern

**Collapsible tool calls with smart previews:**

```typescript
function ToolCallView({ toolCall }: { toolCall: ToolCall }) {
    const [expanded, setExpanded] = useState(false);
    
    const statusIcon = {
        pending: '⏳',
        running: '⏳', 
        complete: '✓',
        error: '✗'
    }[toolCall.status];
    
    // Smart preview based on tool type
    function getPreview(name: string, args: Record<string, unknown>): string {
        switch (name) {
            case 'bash':
                return truncate(String(args.command || ''), 60);
            case 'read_file':
                return String(args.file_path || '');
            case 'web_search':
                return `"${truncate(String(args.query || ''), 40)}"`;
            default:
                return Object.keys(args).join(', ');
        }
    }
    
    return (
        <div className="tool-call">
            <button onClick={() => setExpanded(!expanded)}>
                <span>{expanded ? '▼' : '▶'}</span>
                <span>{statusIcon}</span>
                <span className="tool-name">{toolCall.name}</span>
                {!expanded && (
                    <span className="preview">{getPreview(toolCall.name, toolCall.arguments)}</span>
                )}
            </button>
            {expanded && (
                <div className="tool-details">
                    <pre>{JSON.stringify(toolCall.arguments, null, 2)}</pre>
                    {toolCall.result && <pre>{toolCall.result}</pre>}
                </div>
            )}
        </div>
    );
}
```

---

## Reference: amplifier-web

These patterns are adapted from [amplifier-web](https://github.com/bkrabach/amplifier-web), a server-based Amplifier UI. While amplifier-web uses a Python backend with WebSocket, the patterns translate well to browser-based Pyodide with Web Workers:

| amplifier-web | Browser Equivalent |
|---------------|-------------------|
| WebSocket | postMessage to Worker |
| FastAPI backend | Pyodide in Worker |
| Python hooks | Same hooks, different transport |
| React frontend | Same React patterns |

The key insight: **The message protocol and UI patterns are transport-agnostic** - they work whether the Python runs on a server or in a browser via Pyodide.

---

## Design Expectations

**Do NOT just copy the minimal example.** Use examples as REFERENCE for the technical patterns, but create your own design.

### Minimum UI Requirements

Every browser Amplifier app should include:

| Requirement | Why |
|-------------|-----|
| **Markdown rendering** | LLM responses include code blocks, lists, bold text |
| **Streaming indicator** | Users need feedback while model generates |
| **Welcome message** | Explain what the app does and its capabilities |
| **Error handling UI** | WebGPU failures, OOM errors need clear messages |
| **Model info display** | Show which model is loaded |

### Markdown Rendering (Required)

**At minimum, support these patterns:**

```javascript
// Simple markdown renderer for chat (no library needed)
function renderMarkdown(text) {
    return text
        // Code blocks (```lang ... ```)
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
        // Inline code (`code`)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold (**text**)
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        // Italic (*text*)
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        // Links [text](url)
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Line breaks
        .replace(/\n/g, '<br>');
}

// Use innerHTML with the rendered markdown
messageDiv.innerHTML = renderMarkdown(response);
```

**For richer rendering**, include marked.js via CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
    messageDiv.innerHTML = marked.parse(response);
</script>
```

### Streaming Cursor CSS

```css
/* Add blinking cursor while streaming */
.streaming::after {
    content: '▋';
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}
```

### Reference Implementations

Use these for **design inspiration** (not copy-paste):

| File | What It Demonstrates |
|------|---------------------|
| `webllm-chat-analysis.html` | CSS variables, error screens, streaming cursor, responsive design |
| `amplifier-in-action.html` | Gradient accents, avatars, model selector, polished styling |
| `amplifier-web/frontend/` | Full React patterns for markdown, tool calls, sub-sessions |

### Design Checklist

Before considering a browser app complete:

- [ ] Markdown renders correctly (code blocks, bold, links at minimum)
- [ ] Streaming shows visual feedback (cursor or animation)
- [ ] Welcome message explains the app
- [ ] Errors display user-friendly messages (not raw exceptions)
- [ ] Model name is visible somewhere
- [ ] Mobile-responsive (test at 375px width)
- [ ] CSS uses variables for easy theming
- [ ] Unique visual identity (not a copy of the example)
