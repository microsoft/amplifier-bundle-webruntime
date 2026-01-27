---
bundle:
  name: webruntime
  version: 1.0.0
  description: Run Amplifier sessions in web environments - from single HTML files to full web apps

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: webruntime:behaviors/webruntime
---

# Web Runtime Bundle

**Run Amplifier sessions in web environments.**

Build browser-based Amplifier experiences - from standalone HTML files with embedded AI to full web applications.

## What This Bundle Provides

### Specialist Agent (1)
- **webruntime-developer** - Builds and tests browser Amplifier apps with autonomous Playwright testing

### Capabilities
- **Pyodide Integration** - Run Python amplifier-core in the browser
- **WebLLM Bridge** - Connect browser-based LLMs to Amplifier sessions
- **Autonomous Testing** - Playwright-based testing loop for quality assurance
- **Multiple Formats** - Single HTML files, web apps, React integrations

## Quick Start

```
"Build me a WebLLM chat app as a single HTML file"
"Create a browser-based Amplifier demo with Phi-3.5"
"Make a portable offline AI chat application"
```

---

@webruntime:context/webruntime-guide.md

---

@foundation:context/shared/common-system-base.md
