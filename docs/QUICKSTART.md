# Browser Amplifier Quickstart

Build browser-based AI applications with Amplifier in minutes.

## Two Paths

### Easy Path (90% of users)

1. **Build the bundle** (one-time setup):
   ```bash
   cd amplifier-bundle-browser
   python scripts/build-bundle.py \
       --core-wheel /path/to/amplifier_core-X.X.X-py3-none-any.whl \
       --foundation-wheel /path/to/amplifier_foundation-X.X.X-py3-none-any.whl
   ```

2. **Use in your project**:
   ```html
   <!-- Copy amplifier-browser.js to your project -->
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
     console.log(result.content);
   </script>
   ```

3. **Or use the template**: Copy `templates/quickstart.html` and customize.

### Advanced Path (custom bundles, tools, providers)

See [CUSTOMIZATION.md](./CUSTOMIZATION.md) for:
- Adding custom tools
- Using different providers (OpenAI, Anthropic)
- Loading Amplifier bundles
- Building custom JS bundles

## API Reference

### Constructor

```javascript
const amp = new AmplifierBrowser({
  // Model (required for WebLLM)
  model: 'Phi-3.5-mini-instruct-q4f16_1-MLC',
  
  // Optional: System prompt
  systemPrompt: 'You are a helpful assistant.',
  
  // Optional: Progress callback
  onProgress: (stage, percent, message) => { },
  
  // Optional: Error callback
  onError: (error) => { },
  
  // Optional: Enable debug logging
  debug: false,
  
  // Optional: Load an Amplifier bundle
  bundle: './my-bundle.yaml',
  // or
  bundleContent: '---\nbundle:\n...',
  
  // Optional: Skip WebLLM (for API providers only)
  skipWebLLM: false,

  // Required to approve any tool call
  approveToolCall: async ({ name, arguments, prompt }) => {
    return window.confirm(
      `Allow tool call "${name}" with arguments:\n${JSON.stringify(arguments, null, 2)}`
    ) === true;
  },
});
```

Tool calls are schema-validated and limited to one call per user request. Every
tool call is denied unless `approveToolCall` is a function that resolves to
exactly `true` for that invocation; missing callbacks, non-functions, malformed
arguments, and callback failures deny the call. Browser fetches omit credentials
and reject same-origin requests and redirects.

### Methods

| Method | Description |
|--------|-------------|
| `init()` | Initialize the runtime (load Pyodide, model, etc.) |
| `execute(prompt)` | Send a message, get complete response |
| `executeStreaming(prompt, onChunk)` | Send a message with streaming response |
| `setSystemPrompt(prompt)` | Update the system prompt |
| `getHistory()` | Get conversation history |
| `clearHistory()` | Clear conversation history |
| `registerTool(pythonCode)` | Add a custom tool |
| `dispose()` | Clean up resources |

### Properties

| Property | Description |
|----------|-------------|
| `isReady` | Whether initialization is complete |
| `isExecuting` | Whether a prompt is currently executing |
| `sessionId` | Current session ID |

### Error Handling

```javascript
try {
  await amp.init();
} catch (e) {
  if (e instanceof AmplifierError) {
    switch (e.code) {
      case 'WEBGPU_NOT_SUPPORTED':
        // Show browser upgrade message
        break;
      case 'MODEL_LOAD_FAILED':
        // Try smaller model
        break;
      default:
        console.error(e.message, e.suggestion);
    }
  }
}
```

### Error Codes

| Code | Description | Recoverable |
|------|-------------|-------------|
| `WEBGPU_NOT_SUPPORTED` | Browser lacks WebGPU | No |
| `PYODIDE_LOAD_FAILED` | Failed to load Python runtime | Yes (retry) |
| `WHEEL_INSTALL_FAILED` | Failed to install Amplifier | Yes (retry) |
| `MODEL_LOAD_FAILED` | WebLLM model loading failed | Yes (try smaller model) |
| `SESSION_CREATE_FAILED` | Failed to create session | No |
| `EXECUTION_FAILED` | Error during prompt | Yes |
| `NOT_INITIALIZED` | Called method before init() | Yes (call init) |

## Requirements

- **Browser**: Chrome 113+, Edge 113+, or Safari 18+ (WebGPU required)
- **GPU**: 4GB+ VRAM for small models, 8GB+ for larger models

## File Structure

```
amplifier-bundle-browser/
├── dist/
│   └── amplifier-browser.js    # Built bundle (generated)
├── scripts/
│   ├── build-bundle.py         # Build script
│   └── build-examples.py       # Example generator
├── src/
│   ├── amplifier_browser.py    # Python runtime
│   └── js/
│       └── amplifier-browser.src.js  # JS source
├── templates/
│   └── quickstart.html         # Ready-to-use template
└── docs/
    ├── QUICKSTART.md           # This file
    └── CUSTOMIZATION.md        # Advanced usage
```
