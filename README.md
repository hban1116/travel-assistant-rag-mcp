# AI Travel Planning Assistant — Singapore

A context-aware travel assistant combining a Retrieval-Augmented Generation (RAG)
knowledge base with live information from MCP tools. Built with LangChain, FAISS,
Groq, and Streamlit.

---

## Architecture

```
┌───────────────────────────┐
│  Streamlit UI (app.py)    │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│  agent.py (router)        │  ← classifies query via Groq LLM
└──┬──────────────────┬─────┘
   │                  │
   ▼                  ▼
┌────────────┐  ┌────────────────────────┐
│ rag.py     │  │ mcp_clients.py         │
│  FAISS     │  │  (stdio transport)     │
│  + Groq    │  │                        │
└─────┬──────┘  └────────┬───────────────┘
      │                  │
      ▼                  ▼
 4 KB docs        ┌──────────────┐  ┌──────────────┐
 (markdown)       │ weather_srv  │  │ currency_srv │
                  │ (FastMCP)    │  │ (FastMCP)    │
                  │ Open-Meteo   │  │ frankfurter  │
                  └──────────────┘  └──────────────┘
```

---

## Knowledge Base Sources

| Title | URL | Reuse |
|-------|-----|-------|
| Singapore Attractions | https://www.visitsingapore.com/ | Public web content |
| Singapore Transport | https://www.lta.gov.sg/ | Public web content |
| Singapore Food & Culture | https://www.visitsingapore.com/dining-drinks/ | Public web content |
| Singapore Itineraries | https://www.visitsingapore.com/see-do-itineraries/ | Public web content |

Each markdown file begins with metadata:
```html
<!-- source_title: <title> | source_url: <url> -->
```

---

## RAG Workflow

1. **Ingest** (`ingest.py`) — reads all `data/knowledge_base/*.md` files, splits with
   `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)`.
2. **Embed** — `sentence-transformers/all-MiniLM-L6-v2` (local, no API key).
3. **Store** — FAISS index saved to `./faiss_index/`.
4. **Retrieve** — top-4 chunks per question via `similarity_search`.
5. **Generate** — Groq `openai/gpt-oss-20b` answers using only retrieved context.
6. **Cite** — every KB fact carries a `[KB: <source_title>]` marker; if the KB is
   insufficient, the assistant replies exactly:
   *"I don't have enough information in the knowledge base to answer this reliably."*

---

## MCP Tools

| Tool | Server | Transport | API |
|------|--------|-----------|-----|
| `get_forecast(city, days)` | `mcp_servers/weather_server.py` | stdio (FastMCP) | Open-Meteo |
| `convert(amount, from_currency, to_currency)` | `mcp_servers/currency_server.py` | stdio (FastMCP) | frankfurter.dev |

The client (`mcp_clients.py`) spawns each server as a subprocess via
`stdio_client` + `ClientSession`, calls the required tool, and returns structured
JSON. Failures return `{"error": "..."}` and **never fabricate data**.

---

## Prompt & Context Strategy

| Prompt | Purpose |
|--------|---------|
| `ROUTER_PROMPT` | Classifies the query into KB / WEATHER / CURRENCY / COMBINED / NONE |
| `RAG_PROMPT` | Forces context-only answers with `[source_title]` citations |
| `COMBINED_PROMPT` | Merges KB + MCP outputs, labels every fact with its origin, builds day-wise plans |
| `SYSTEM_PROMPT` | Global rules: cite KB and MCP, refuse hallucinations, preserve preferences |

**Context retention:** `app.py` stores the full message history in
`st.session_state.messages`. `agent.py` prepends the last 6 turns to the
`COMBINED_PROMPT` via the `{history}` slot, so follow-ups like *"Make day 2 indoor only"*
modify the previous plan correctly.

**Factual vs. AI-generated:** Every statement is labelled:
- `[KB: <source_title>]` — from the knowledge base
- `[Source: MCP weather tool]` / `[Source: MCP currency tool]` — from live tools
- Unmarked text is the LLM's own synthesis (clearly separable from the above)

---

## Setup

Requires Python 3.11–3.13. Groq API key (free tier).

```powershell
cd travel_assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set:
```
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Build the vector index:
```powershell
python ingest.py
```

Test MCP tools:
```powershell
python mcp_clients.py
```

Test the agent:
```powershell
python agent.py
```

Launch the UI:
```powershell
streamlit run app.py
```

Open `http://localhost:8501`.

---

## Sample Questions

Try these in order to exercise every code path:

1. `What are the must-visit attractions in Singapore?` — RAG only
2. `What's the weather in Singapore for the next 3 days?` — MCP weather
3. `Convert INR 50000 to SGD` — MCP currency
4. `Plan a 3-day Singapore itinerary for next week and adjust for weather` — combined RAG + MCP
5. `Make day 2 indoor only` — multi-turn context
6. `Convert my 60000 INR budget to SGD and suggest a 3-day plan` — combined currency + itinerary
7. `What's the best ramen shop in Tokyo?` — KB-insufficiency guardrail

Full transcripts in `sample_conversations.md`.

---

## Acceptance Criteria Mapping

| Criterion | Where |
|-----------|-------|
| KB from 3+ sources | `data/knowledge_base/` (4 files) |
| Embedding-based retrieval | `ingest.py`, `rag.py` (FAISS + MiniLM) |
| Grounded answers with sources | `prompts.py` RAG_PROMPT + citations |
| Weather via MCP | `mcp_servers/weather_server.py` |
| Currency via MCP | `mcp_servers/currency_server.py` |
| Combined RAG + MCP response | Q4 in `sample_conversations.md` |
| Multi-turn context | `agent.py` `_history_str()` + Q5 |
| Tool selection by intent | `ROUTER_PROMPT` + `_classify()` |
| Missing-knowledge handling | Q7 (refusal) |
| Tool-failure handling | `_safe_tool_call()` + Q8 |
| Simple UI | `app.py` (Streamlit chat) |

---

## Notes

- Groq models: use `openai/gpt-oss-20b` or `openai/gpt-oss-120b`. The older
  `llama-3.x` names were deprecated by Groq.
- MCP SDK pinned to `mcp>=1.2,<2` for the v1 API (`FastMCP`).
- FAISS index is small (~9 chunks) and loads in under a second.
- All tools are read-only; no booking, payment, or reservation logic.


# AI Travel Planning Assistant — Singapore

**Source code:** https://github.com/hban1116/travel-assistant-rag-mcp

A context-aware travel assistant combining a Retrieval-Augmented Generation (RAG)
knowledge base with live information from MCP tools. Built with LangChain, FAISS,
Groq, and Streamlit.