# amplifier-bundle-browser

Browser runtime for Amplifier - run AI agents entirely in web browsers.

## Overview

This bundle enables running Amplifier applications in web browsers using:

- **Pyodide** - Python interpreter compiled to WebAssembly
- **amplifier-core** - The Amplifier kernel running in Pyodide
- **Browser-specific tools** - Storage, fetch, and other browser APIs

**Provider-agnostic**: This bundle provides the runtime infrastructure. Compose it with your choice of provider:

- [amplifier-bundle-webllm](https://github.com/microsoft/amplifier-bundle-webllm) - Local inference via WebGPU
- OpenAI/Anthropic - Cloud APIs (user provides key)

## Quick Start

**See the working example:** [`examples/minimal-webllm-chat.html`](examples/minimal-webllm-chat.html)

This example is a single-file, copy-paste ready HTML that works out of the box.

### Key Requirements

Browser Amplifier requires **THREE components**:

1. **Pyodide** - Python runtime in WebAssembly
2. **amplifier-core wheel** - The kernel (embedded as base64, NOT available on PyPI)
3. **amplifier-browser module** - Browser adapter layer (in `src/amplifier_browser.py`)

### Critical Gotchas

```javascript
// ❌ WRONG - amplifier-core is NOT on PyPI
await micropip.install('amplifier-core');

// ❌ WRONG - JS proxy doesn't support kwargs
await micropip.install('wheel.whl', {deps: false});

// ✅ CORRECT - Embed wheel, use Python for deps=False
pyodide.FS.writeFile('/tmp/amplifier_core-1.0.0-py3-none-any.whl', wheelBytes);
await pyodide.runPythonAsync(`
    import micropip
    await micropip.install('emfs:/tmp/amplifier_core-1.0.0-py3-none-any.whl', deps=False)
`);
```

### Building Your Own

1. Build the amplifier-core wheel: `python scripts/build-wheel.py --source ~/repos/amplifier-core --output ./dist`
2. Base64-encode `src/amplifier_browser.py`
3. Embed both in your HTML (see example)
4. Set up JS bridge functions BEFORE loading amplifier-browser
5. Use `create_session()` factory function

See [`context/browser-guide.md`](context/browser-guide.md) for complete documentation.

## What's Included

### Tools

| Tool | Description |
|------|-------------|
| `tool-browser-storage` | localStorage/IndexedDB access |
| `tool-todo` | Task tracking (in-memory) |

### Agents

| Agent | Description |
|-------|-------------|
| `browser-developer` | Expert for building browser Amplifier integrations |

### Context

- `browser-guide.md` - Browser capabilities, constraints, and patterns

## Directory Structure

```
amplifier-bundle-browser/
├── bundle.yaml                 # Main entry point
├── behaviors/
│   └── browser-runtime.yaml    # Core browser behavior
├── agents/
│   └── browser-developer.md    # Integration expert
├── context/
│   └── browser-guide.md        # Browser-specific guidance
└── modules/
    └── tool-browser-storage/   # Browser storage tool
```

## Browser Requirements

| Browser | Support |
|---------|---------|
| Chrome 113+ | ✅ Full (WebGPU for local inference) |
| Edge 113+ | ✅ Full |
| Safari 18+ | ✅ Full |
| Firefox | ⚠️ WebGPU behind flag |

## Constraints vs Desktop Amplifier

| Feature | Desktop | Browser |
|---------|---------|---------|
| Filesystem access | ✅ Full | ❌ None |
| Shell commands | ✅ Full | ❌ None |
| Persistent storage | ✅ Files | ⚠️ localStorage/IndexedDB |
| Memory | ✅ System RAM | ⚠️ Tab limit (~2-4GB) |
| Network | ✅ Full | ⚠️ CORS restrictions |

## Composition Examples

### With WebLLM (Local Inference)

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-browser@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-webllm@main
```

### With OpenAI (Cloud API)

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-browser@main

providers:
  - module: provider-openai
    source: git+https://github.com/microsoft/amplifier-module-provider-openai@main
    config:
      api_key: ${OPENAI_API_KEY}  # User provides at runtime
```

## Development

### Using the browser-developer Agent

The `browser-developer` agent can help you build browser Amplifier integrations:

```
"Help me create a browser chat interface with WebLLM"
"Debug why my browser Amplifier app isn't loading"
"Show me how to add persistent storage to my browser app"
```

### Testing Locally

```bash
# Serve the examples directory
cd examples
python -m http.server 8080

# Open http://localhost:8080 in browser
```

## License

MIT

## Related

- [amplifier-bundle-webllm](https://github.com/microsoft/amplifier-bundle-webllm) - WebLLM provider
- [amplifier-core](https://github.com/microsoft/amplifier-core) - Amplifier kernel
- [Pyodide](https://pyodide.org/) - Python in WebAssembly
- [WebLLM](https://webllm.mlc.ai/) - Browser-based LLM inference
