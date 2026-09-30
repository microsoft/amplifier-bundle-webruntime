# Chat Infrastructure Template

This template provides the complete HTML/CSS/JS boilerplate for adding live AI chat to browser applications.

## Complete Chat View HTML

```html
<!-- Chat View -->
<div class="chat-view" id="chat-view">
    <header class="chat-header">
        <button class="chat-header__back" id="chat-back">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M12.5 15L7.5 10L12.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </button>
        <span class="chat-header__title">Chat with Amplifier</span>
        <span class="chat-header__model" id="chat-model-badge">Loading...</span>
    </header>
    
    <div class="chat-loading" id="chat-loading">
        <div class="chat-loading__title">Initializing Amplifier...</div>
        <div class="chat-loading__steps">
            <div class="loading-step" id="load-step-webgpu">
                <div class="loading-step__icon"><span class="loading-step__pending">○</span></div>
                <span class="loading-step__label">Check WebGPU</span>
            </div>
            <div class="loading-step" id="load-step-pyodide">
                <div class="loading-step__icon"><span class="loading-step__pending">○</span></div>
                <span class="loading-step__label">Load Python Runtime</span>
                <span class="loading-step__detail" id="load-step-pyodide-detail"></span>
            </div>
            <div class="loading-step" id="load-step-model">
                <div class="loading-step__icon"><span class="loading-step__pending">○</span></div>
                <span class="loading-step__label">Download LLM Model</span>
                <span class="loading-step__detail" id="load-step-model-detail"></span>
            </div>
            <div class="loading-step" id="load-step-amplifier">
                <div class="loading-step__icon"><span class="loading-step__pending">○</span></div>
                <span class="loading-step__label">Start Amplifier Session</span>
            </div>
        </div>
    </div>
    
    <div class="chat-messages" id="chat-messages" style="display: none;"></div>
    
    <div class="chat-input-area" id="chat-input-area" style="display: none;">
        <input type="text" id="chat-input" placeholder="Ask anything..." disabled>
        <button id="chat-send" disabled>Send</button>
    </div>
</div>
```

## Complete Chat CSS

```css
/* Chat View */
.chat-view {
    position: fixed;
    inset: 0;
    background: #0a0a0a;
    z-index: 300;
    display: none;
    flex-direction: column;
}
.chat-view.active { display: flex; }

/* Header */
.chat-header {
    padding: 16px 20px;
    border-bottom: 1px solid #222;
    display: flex;
    align-items: center;
    gap: 16px;
}
.chat-header__back {
    width: 36px;
    height: 36px;
    background: rgba(255,255,255,0.1);
    border: none;
    border-radius: 8px;
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}
.chat-header__back:hover { background: rgba(255,255,255,0.15); }
.chat-header__title { flex: 1; font-size: 16px; font-weight: 500; }
.chat-header__model {
    font-size: 12px;
    color: rgba(255,255,255,0.5);
    padding: 4px 10px;
    background: rgba(10,132,255,0.2);
    border-radius: 12px;
}

/* Loading */
.chat-loading {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 24px;
    padding: 20px;
}
.chat-loading__title { font-size: 20px; font-weight: 500; }
.chat-loading__steps {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
    max-width: 350px;
}
.loading-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: #1a1a1a;
    border-radius: 10px;
    font-size: 14px;
}
.loading-step__icon {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.loading-step__spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #333;
    border-top-color: #0A84FF;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-step__check { color: #4ade80; font-size: 16px; }
.loading-step__pending { color: #666; }
.loading-step.active .loading-step__label { color: #fff; }
.loading-step.done .loading-step__label { color: #4ade80; }
.loading-step__detail { font-size: 11px; color: #666; margin-left: auto; }

/* Messages */
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.chat-message {
    display: flex;
    gap: 12px;
    max-width: 600px;
}
.chat-message--user {
    align-self: flex-end;
    flex-direction: row-reverse;
}
.chat-message__avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
    flex-shrink: 0;
}
.chat-message--user .chat-message__avatar { background: #0A84FF; }
.chat-message--assistant .chat-message__avatar { background: #5AC8FA; }
.chat-message__content {
    padding: 12px 16px;
    border-radius: 16px;
    line-height: 1.5;
}
.chat-message--user .chat-message__content {
    background: #0A84FF;
    border-bottom-right-radius: 4px;
}
.chat-message--assistant .chat-message__content {
    background: #1a1a1a;
    border-bottom-left-radius: 4px;
}
.chat-message__content code {
    background: rgba(255,255,255,0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 0.9em;
}
.chat-message__content pre {
    background: rgba(255,255,255,0.05);
    padding: 12px 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;
}

/* Typing Indicator */
.chat-message__typing {
    display: flex;
    gap: 4px;
    padding: 16px;
}
.chat-message__typing span {
    width: 8px;
    height: 8px;
    background: #666;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;
}
.chat-message__typing span:nth-child(2) { animation-delay: 0.2s; }
.chat-message__typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-4px); }
}

/* Input Area */
.chat-input-area {
    padding: 16px 20px;
    border-top: 1px solid #222;
    display: flex;
    gap: 12px;
}
.chat-input-area input {
    flex: 1;
    padding: 12px 16px;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 12px;
    color: #fff;
    font-size: 15px;
    outline: none;
}
.chat-input-area input:focus { border-color: #0A84FF; }
.chat-input-area input::placeholder { color: #666; }
.chat-input-area button {
    padding: 12px 20px;
    background: #0A84FF;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
}
.chat-input-area button:hover:not(:disabled) { background: #0070E0; }
.chat-input-area button:disabled {
    background: #333;
    color: #666;
    cursor: not-allowed;
}
```

## Complete Chat JavaScript

```javascript
import { CreateMLCEngine } from '@mlc-ai/web-llm';
import { marked } from 'marked';

marked.setOptions({ breaks: true, gfm: true });

const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.0/full/';
let pyodide = null, llmEngine = null, chatInitialized = false, isGenerating = false;

// Customize these
const modelId = 'Phi-3.5-mini-instruct-q4f16_1-MLC';
const SYSTEM_PROMPT = `Your system prompt here...`;

function updateLoadStep(id, status, detail = '') {
    const step = document.getElementById(id);
    if (!step) return;
    const icon = step.querySelector('.loading-step__icon');
    const detailEl = step.querySelector('.loading-step__detail');
    step.classList.remove('active', 'done');
    if (status === 'loading') {
        step.classList.add('active');
        icon.innerHTML = '<span class="loading-step__spinner"></span>';
    } else if (status === 'done') {
        step.classList.add('done');
        icon.innerHTML = '<span class="loading-step__check">✓</span>';
    }
    if (detailEl && detail) detailEl.textContent = detail;
}

async function initChat() {
    try {
        // Step 1: Check WebGPU
        updateLoadStep('load-step-webgpu', 'loading');
        if (!navigator.gpu) throw new Error('WebGPU not supported');
        const adapter = await navigator.gpu.requestAdapter();
        if (!adapter) throw new Error('No WebGPU adapter');
        updateLoadStep('load-step-webgpu', 'done');

        // Step 2: Load Pyodide
        updateLoadStep('load-step-pyodide', 'loading', 'Loading runtime...');
        const script = document.createElement('script');
        script.src = `${PYODIDE_URL}pyodide.js`;
        document.head.appendChild(script);
        await new Promise((resolve, reject) => {
            script.onload = resolve;
            script.onerror = () => reject(new Error('Failed to load Pyodide'));
        });
        pyodide = await window.loadPyodide({ indexURL: PYODIDE_URL });
        
        // Install packages
        await pyodide.loadPackage('micropip');
        const micropip = pyodide.pyimport('micropip');
        for (const pkg of ['pydantic', 'pyyaml', 'typing-extensions']) {
            updateLoadStep('load-step-pyodide', 'loading', `Installing ${pkg}...`);
            await micropip.install(pkg);
        }
        
        // Install amplifier-core from embedded wheel
        updateLoadStep('load-step-pyodide', 'loading', 'Installing amplifier...');
        const wheelB64 = document.getElementById('amplifier-wheel-b64').textContent.trim();
        const wheelBytes = Uint8Array.from(atob(wheelB64), c => c.charCodeAt(0));
        pyodide.FS.writeFile('/tmp/amplifier_core-1.0.0-py3-none-any.whl', wheelBytes);
        await micropip.install('emfs:/tmp/amplifier_core-1.0.0-py3-none-any.whl');
        updateLoadStep('load-step-pyodide', 'done');

        // Step 3: Load LLM Model
        updateLoadStep('load-step-model', 'loading', '0%');
        llmEngine = await CreateMLCEngine(modelId, {
            initProgressCallback: (p) => {
                if (p.progress !== undefined) {
                    updateLoadStep('load-step-model', 'loading', `${Math.round(p.progress * 100)}%`);
                }
            }
        });
        updateLoadStep('load-step-model', 'done');

        // Step 4: Initialize Amplifier Session
        updateLoadStep('load-step-amplifier', 'loading');
        
        // Set up JS bridges
        globalThis.js_llm_complete = async (messagesJson, toolsJson) => {
            const messages = JSON.parse(messagesJson);
            const response = await llmEngine.chat.completions.create({
                messages,
                temperature: 0.7,
                max_tokens: 2048
            });
            return JSON.stringify({
                content: response.choices[0].message.content || '',
                usage: response.usage
            });
        };
        
        globalThis.js_llm_stream = async (m, c) => {
            return globalThis.js_llm_complete(m, null);
        };
        
        globalThis.js_web_fetch = async (url) => {
            try {
                const parsed = new URL(url);
                if (parsed.protocol !== 'https:' || parsed.username || parsed.password) {
                    throw new Error('Only absolute HTTPS URLs without credentials are allowed');
                }
                if (globalThis.location && parsed.origin === globalThis.location.origin) {
                    throw new Error('Same-origin requests are not allowed');
                }
                const r = await fetch(parsed.href, {
                    credentials: 'omit',
                    mode: 'cors',
                    redirect: 'error',
                    referrerPolicy: 'no-referrer'
                });
                return r.ok ? await r.text() : JSON.stringify({error: r.status});
            } catch(e) {
                return JSON.stringify({error: e.message});
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

        // Load amplifier-browser module
        const moduleB64 = document.getElementById('amplifier-browser-py').textContent.trim();
        await pyodide.runPythonAsync(atob(moduleB64));
        
        // Create session with system prompt
        const escapedPrompt = SYSTEM_PROMPT.replace(/\\/g, '\\\\').replace(/"""/g, '\\"\\"\\"');
        await pyodide.runPythonAsync(`
session = create_session(model_id="${modelId}")
session.set_system_prompt("""${escapedPrompt}""")
await session.initialize()
`);
        updateLoadStep('load-step-amplifier', 'done');

        // Show chat UI
        document.getElementById('chat-loading').style.display = 'none';
        document.getElementById('chat-messages').style.display = 'flex';
        document.getElementById('chat-input-area').style.display = 'flex';
        document.getElementById('chat-input').disabled = false;
        document.getElementById('chat-send').disabled = false;
        document.getElementById('chat-model-badge').textContent = 'Phi 3.5 Mini';
        
        // Welcome message
        addMsg('assistant', "Hello! I'm running **real amplifier-core** in your browser. How can I help?");
        chatInitialized = true;

    } catch (e) {
        console.error('Chat init error:', e);
        addMsg('assistant', `Error initializing: ${e.message}`);
    }
}

function addMsg(role, content) {
    const msgs = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-message chat-message--${role}`;
    const rendered = role === 'assistant' ? marked.parse(content) : content.replace(/</g, '&lt;');
    div.innerHTML = `
        <div class="chat-message__avatar">${role === 'user' ? 'U' : 'A'}</div>
        <div class="chat-message__content">${rendered}</div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

function addTyping() {
    const msgs = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-message chat-message--assistant';
    div.id = 'typing';
    div.innerHTML = `
        <div class="chat-message__avatar">A</div>
        <div class="chat-message__content">
            <div class="chat-message__typing">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

async function sendMsg() {
    if (isGenerating || !pyodide) return;
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    
    input.value = '';
    isGenerating = true;
    document.getElementById('chat-send').disabled = true;
    
    addMsg('user', msg);
    const typing = addTyping();
    
    try {
        const escapedMsg = JSON.stringify(msg);
        const resultJson = await pyodide.runPythonAsync(`
import json
async def _exec():
    response = await session.execute(${escapedMsg})
    return json.dumps({"content": response})
await _exec()
`);
        const result = JSON.parse(resultJson);
        typing.remove();
        addMsg('assistant', result.content);
    } catch (e) {
        typing.remove();
        addMsg('assistant', `Error: ${e.message}`);
    } finally {
        isGenerating = false;
        document.getElementById('chat-send').disabled = false;
        document.getElementById('chat-input').focus();
    }
}

// Event listeners
document.getElementById('chat-send').addEventListener('click', sendMsg);
document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMsg();
    }
});
document.getElementById('chat-back').addEventListener('click', () => {
    document.getElementById('chat-view').classList.remove('active');
});
```

## Required Import Map

```html
<script type="importmap">
{
    "imports": {
        "@mlc-ai/web-llm": "https://esm.run/@mlc-ai/web-llm@0.2.79",
        "marked": "https://esm.run/marked@15.0.6"
    }
}
</script>
```

## Chat Button (Optional)

Add a floating button to open the chat:

```html
<button class="chat-btn" id="chat-btn" onclick="showChatView()">💬 Chat</button>
```

```css
.chat-btn {
    position: fixed;
    bottom: 30px;
    left: 40px;
    background: #0A84FF;
    border: none;
    border-radius: 24px;
    padding: 12px 20px;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    z-index: 100;
    transition: transform 0.2s, box-shadow 0.2s;
}
.chat-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 20px rgba(10,132,255,0.4);
}
.chat-btn.hidden { display: none; }
```

```javascript
window.showChatView = function() {
    document.getElementById('chat-view').classList.add('active');
    document.getElementById('chat-btn').classList.add('hidden');
    if (!chatInitialized) initChat();
};
```
