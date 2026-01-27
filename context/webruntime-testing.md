# Autonomous Browser Testing with Playwright

## The Key Insight

**You can test browser apps autonomously without user involvement.**

Playwright with WebGPU flags lets you:
- Run headless Chrome with WebGPU support
- Capture all console output to files
- Take screenshots on failure
- Iterate until the app works
- THEN deliver to user

## Required Setup

```bash
pip install playwright
playwright install chromium
```

## The Autonomous Debug Loop

```
1. Generate HTML with data-status attributes
           ↓
2. Generate Playwright test script
           ↓
3. Run: python test_app.py
           ↓
    ┌──────┴──────┐
    ↓ FAIL        ↓ PASS
Read console.log  Switch to target model
Fix the issue     Test again
    ↓             ↓
  (back to 3)   Deliver to user
```

## Playwright Test Template

Save as `test_app.py` alongside your HTML:

```python
import asyncio
from playwright.async_api import async_playwright

async def test_app():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--enable-unsafe-webgpu',
                '--enable-features=Vulkan',
                '--use-angle=vulkan',
                '--disable-gpu-sandbox',
            ]
        )
        
        page = await (await browser.new_context()).new_page()
        
        # Capture ALL console output
        logs = []
        page.on('console', lambda m: logs.append(f"[{m.type}] {m.text}"))
        page.on('pageerror', lambda e: logs.append(f"[PAGE ERROR] {e}"))
        
        try:
            await page.goto('file:///path/to/app.html')
            
            # Wait for ready state (3 min timeout for model loading)
            await page.wait_for_selector('[data-status="ready"]', timeout=180000)
            print("✅ App ready")
            
            # Test chat
            await page.fill('#input', 'Hello!')
            await page.click('#send')
            await page.wait_for_selector('.assistant', timeout=60000)
            print("✅ Chat works")
            
        except Exception as e:
            print(f"❌ FAILED: {e}")
            with open('console.log', 'w') as f:
                f.write('\n'.join(logs))
            await page.screenshot(path='failure.png')
            raise
        finally:
            await browser.close()

asyncio.run(test_app())
```

## Required HTML Patterns

### 1. Data-Status Attributes (CRITICAL)

Your HTML MUST have testable state indicators:

```html
<div id="status" data-status="loading">Loading...</div>
```

Update status programmatically:
```javascript
function updateStatus(status, message) {
    const el = document.getElementById('status');
    el.dataset.status = status;  // This is what Playwright waits for
    el.textContent = message;
    console.log(`[STATUS] ${status}: ${message}`);
}
```

### 2. Status Values to Implement

| Status | When to Set |
|--------|-------------|
| `loading` | Initial page load |
| `pyodide-loading` | Loading Pyodide |
| `model-loading` | Loading WebLLM model |
| `ready` | Ready for user input |
| `thinking` | Processing a message |
| `error` | Error occurred |

### 3. Testable UI Elements

```html
<!-- Input must have id="input" -->
<input type="text" id="input" placeholder="Type...">

<!-- Send button must have id="send" -->
<button id="send">Send</button>

<!-- Messages must have role classes -->
<div class="user">User message</div>
<div class="assistant">Assistant response</div>
```

## Debug Workflow

### On Test Failure

1. **Read console.log** - Contains all browser console output
2. **View failure.png** - Shows visual state at failure
3. **Check the specific error** - Usually clear from logs
4. **Fix and re-run** - Don't ask user, just iterate

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `WebGPU not supported` | Headless without flags | Add `--enable-unsafe-webgpu` |
| `micropip.install() unexpected keyword` | JS syntax in Python | Use `deps=False` not `{deps: false}` |
| `amplifier-core not found` | Tried PyPI | Use embedded wheel or URL |
| `Timeout waiting for ready` | App stuck | Check console.log for where it stopped |
| `js_llm_complete not defined` | Bridge not registered | Use `globalThis.X = fn` before Pyodide loads module |

## Model Selection for Testing

**Use FP32 models for Playwright testing** - more compatible with headless WebGPU:

```javascript
// TESTING - Use this first
const testModel = 'Llama-3.2-1B-Instruct-q4f32_1-MLC';

// PRODUCTION - Switch after tests pass
const prodModel = 'Phi-3.5-mini-instruct-q4f16_1-MLC';
```

## Complete Workflow Example

```bash
# 1. Agent generates app.html and test_app.py

# 2. Run test
python test_app.py

# 3. If failed, read logs
cat console.log

# 4. Fix issue in app.html

# 5. Re-run test
python test_app.py

# 6. Once passing with test model, switch to target model in app.html

# 7. Run test again
python test_app.py

# 8. Deliver working app to user
```

## Key Principle

**Never deliver untested code to the user.** 

The Playwright test is your quality gate. If it doesn't pass, the app isn't ready. Fix it yourself, don't ask the user to debug.
