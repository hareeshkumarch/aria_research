# 🤖 ARIA POC — Autonomous Research & Intelligence Agent

> A working POC of an agentic AI system using **free-tier LLMs** (Groq, Gemini Flash, or Ollama).  
> Give ARIA a goal → watch it plan, search, and synthesize in real time.

![Stack](https://img.shields.io/badge/LLM-Groq%20%7C%20Gemini%20%7C%20Ollama-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20LangGraph-green)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20ReactFlow-cyan)
![Free](https://img.shields.io/badge/Cost-100%25%20Free%20Tier-brightgreen)

---

## ✨ What This POC Does

1. You type a research goal (e.g. *"What are the latest breakthroughs in quantum computing?"*)
2. ARIA's **Planner** decomposes it into 3–5 subtasks using an LLM
3. Each subtask is executed by the **Executor** — searches DuckDuckGo (no API key needed!)
4. The **Synthesizer** streams a comprehensive markdown report token by token
5. The entire pipeline is visualized as a live **node graph** in the browser

---

## 🏗️ Architecture

```
Goal Input (React)
      │
      ▼
FastAPI POST /api/v1/runs
      │
      ▼
LangGraph Pipeline:
  [Planner] → [Executor x N] → [Synthesizer]
      │               │               │
      └───────────────┴───────────────┘
                      │
               asyncio.Queue
                      │
              SSE Stream → React UI
                      │
             Live Node Graph + Thought Stream + Output
```

---

## 🚀 Quick Start (Local Dev — Recommended)

### Prerequisites
- Python 3.11+
- Node.js 20+
- A free API key from **Groq** OR **Google AI Studio** (or Ollama installed locally)

### 1. Clone & configure

```bash
git clone <repo-url> aria-poc
cd aria-poc
cp .env.example .env
```

Edit `.env` and add your API key:

```bash
# For Groq (fastest, recommended):
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here   # free at console.groq.com

# OR for Gemini Flash:
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_key_here     # free at aistudio.google.com

# OR for Ollama (fully local):
LLM_PROVIDER=ollama
# Make sure: ollama pull llama3.2
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy .env to backend directory
cp ../.env .env

uvicorn app.main:app --reload --port 8000
```

Backend running at: http://localhost:8000  
API docs at: http://localhost:8000/docs

### 3. Start the frontend

```bash
cd frontend
npm install                       # or: pnpm install
npm run dev
```

Frontend running at: http://localhost:5173

### 4. Open and run!

Go to **http://localhost:5173**, type a goal, and click **Run ARIA**. 🎉

---

## 🐳 Docker (Alternative)

```bash
cp .env.example .env
# Edit .env with your API key

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

> ⚠️ For Ollama with Docker, set `OLLAMA_BASE_URL=http://host.docker.internal:11434`

---

## 🔑 Free Tier API Keys

| Provider | Free Limit | Get Key |
|----------|------------|---------|
| **Groq** ⭐ Recommended | 6,000 req/day, 30/min | [console.groq.com](https://console.groq.com) |
| **Gemini Flash** | 1,500 req/day, 15/min | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| **Ollama** | Unlimited (local) | [ollama.ai](https://ollama.ai) |

---

## 📁 Project Structure

```
aria-poc/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── llm.py            # LLM provider abstraction
│   │   ├── agent/
│   │   │   ├── state.py      # LangGraph state definition
│   │   │   ├── nodes.py      # Planner / Executor / Synthesizer nodes
│   │   │   ├── tools.py      # DuckDuckGo search tool
│   │   │   └── graph.py      # LangGraph pipeline + run orchestrator
│   │   └── api/
│   │       └── runs.py       # REST API + SSE streaming
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── App.tsx            # Main layout
        ├── store.ts           # Zustand global state
        ├── types.ts           # TypeScript types
        ├── hooks/
        │   └── useRunStream.ts  # SSE hook
        └── components/
            ├── GoalInput.tsx    # Goal bar + run button
            ├── GraphCanvas.tsx  # React Flow live graph
            ├── ThoughtStream.tsx # Agent log terminal
            └── OutputPanel.tsx  # Streaming markdown output
```

---

## 🔧 Switching LLM Providers

Just change one line in `.env` and restart the backend:

```bash
# Use Groq (default, recommended)
LLM_PROVIDER=groq

# Use Gemini Flash
LLM_PROVIDER=gemini

# Use local Ollama
LLM_PROVIDER=ollama
```

---

## 🗺️ What's Next (Full Version)

This POC can be extended to the full ARIA spec:

| Feature | POC | Full |
|---------|-----|------|
| LLM | ✅ Groq/Gemini/Ollama | Claude API |
| Search | ✅ DuckDuckGo | Tavily |
| Memory | ❌ | ChromaDB |
| Code execution | ❌ | E2B Sandbox |
| Persistence | ❌ | PostgreSQL |
| Task queue | ❌ | Celery + Redis |
| Auth | ❌ | JWT |
| History | ❌ | Full run replay |

---

## 🐛 Troubleshooting

**DuckDuckGo rate limited?**  
The search tool has automatic retry. If it fails, wait a minute and try again.

**Groq rate limit hit?**  
Groq's free tier is generous (6k/day) but if you hit the 30/min limit, switch to Gemini or Ollama.

**React Flow not rendering?**  
Make sure `reactflow/dist/style.css` is imported — it's in `src/index.css`.

**CORS errors?**  
Verify `CORS_ORIGINS` in `.env` includes your frontend URL.

---

## 📄 License

MIT — build on top of this freely.
