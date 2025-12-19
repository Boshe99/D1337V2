<div align="center"><a name="readme-top"></a>

# D1337 Ai

An open-source, modern design AI Agent framework.<br/>
Supports speech synthesis, multi-modal, and extensible plugin system.<br/>
One-click deployment of your private AI chat application.

[![][github-license-shield]][github-license-link]

</div>

<details>
<summary><kbd>Table of contents</kbd></summary>

#### TOC

- [Features](#-features)
- [Self Hosting](#-self-hosting)
- [Local Development](#️-local-development)
- [Contributing](#-contributing)

####

<br/>

</details>

## Features

- **MCP Plugin System** - Connect your AI to external tools, data sources, and services
- **Desktop App** - Full experience without browser limitations
- **Smart Internet Search** - Real-time internet access for up-to-date information
- **Chain of Thought** - Visualize AI reasoning step by step
- **Branching Conversations** - Explore multiple conversation paths
- **File Upload / Knowledge Base** - Upload documents, images, audio, and video
- **Multi-Model Support** - Support for multiple AI model providers
- **Local LLM Support** - Use local models via Ollama
- **TTS & STT** - Voice conversation support
- **Text to Image** - Generate images from text
- **Plugin System** - Extend functionality with plugins
- **Local / Remote Database** - Choose your data storage preference
- **Multi-User Management** - Support for multiple users with authentication
- **PWA Support** - Install as a desktop/mobile app
- **Custom Themes** - Light/dark mode and color customization

## Self Hosting

D1337 Ai provides Self-Hosted Version with Docker. Deploy your own chatbot within minutes.

### Deploying with Docker

```bash
# Create a folder for storage
mkdir d1337-ai-db && cd d1337-ai-db

# Start the service
docker compose up -d
```

### Environment Variables

| Environment Variable | Required | Description                                    |
| -------------------- | -------- | ---------------------------------------------- |
| `OPENAI_API_KEY`     | Yes      | Your OpenAI API key                            |
| `OPENAI_PROXY_URL`   | No       | Custom OpenAI API proxy URL                    |
| `ACCESS_CODE`        | No       | Password to access the service                 |

## Local Development

Clone and run locally:

```bash
git clone https://github.com/Boshe99/D1337V2.git
cd D1337V2
pnpm install
pnpm dev
```

## Contributing

Contributions are welcome! Feel free to check out our GitHub Issues and submit Pull Requests.

---

<details><summary><h4>License</h4></summary>

This project is MIT licensed.

</details>

Copyright © 2025 D1337 Ai.

<!-- LINK GROUP -->

[github-license-link]: https://github.com/Boshe99/D1337V2/blob/main/LICENSE
[github-license-shield]: https://img.shields.io/badge/license-MIT-white?labelColor=black&style=flat-square
