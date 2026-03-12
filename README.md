# Recall AI Agent — Meeting Memory Agent

Upload meeting recordings and automatically get transcripts, summaries, action items, decisions, and issues — powered by OpenAI Whisper + GPT-4o and orchestrated with LangGraph.

## Features

- **Async processing**: Upload returns immediately (202); processing runs in the background
- **Full pipeline**: validate → transcribe → summarize → extract → embed → persist
- **Structured extraction**: action items (with owner, due date, status), decisions, issues
- **Semantic search**: embeddings stored via sqlite-vec for future similarity queries
- **Graceful degradation**: each node is fault-tolerant; persist always runs regardless of failures

## Architecture

```
POST /meetings (multipart)
        │
        ▼
  Save audio file
  Insert DB row (status=pending)
  asyncio.create_task()
        │
        ▼
  LangGraph Workflow
  ┌─────────────┐
  │  validate   │─── invalid ──────────────────┐
  └──────┬──────┘                               │
         │ valid                                │
  ┌──────▼──────┐                               │
  │ transcribe  │─── error ────────────────┐   │
  └──────┬──────┘                          │   │
         │                                 │   │
  ┌──────▼──────┐                          │   │
  │  summarize  │─── error ───────────┐   │   │
  └──────┬──────┘                     │   │   │
         │                            │   │   │
  ┌──────▼──────┐                     │   │   │
  │   extract   │─── no summary ─┐   │   │   │
  └──────┬──────┘                 │   │   │   │
         │                       │   │   │   │
  ┌──────▼──────┐                 │   │   │   │
  │    embed    │                 │   │   │   │
  └──────┬──────┘                 │   │   │   │
         └────────────────────────┴───┴───┴───┤
                                              ▼
                                         ┌─────────┐
                                         │ persist │
                                         └─────────┘
```

**Stack**
| Component | Technology |
|-----------|-----------|
| API | FastAPI |
| Workflow | LangGraph |
| Transcription | OpenAI Whisper (`whisper-1`) |
| Summarization / Extraction | OpenAI GPT-4o |
| Embeddings | OpenAI `text-embedding-3-small` |
| Database | SQLite + sqlite-vec (aiosqlite) |
| Container | Docker / Docker Compose |

## API Reference

### `POST /meetings`
Upload a meeting recording and start async processing.

**Form fields**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Meeting title |
| `audio` | file | Yes | Audio/video file |
| `project_id` | string | No | Project identifier |
| `participants` | JSON array string | No | e.g. `["Alice","Bob"]` |

**Supported formats**: wav, mp3, mp4, m4a, webm, ogg, flac

**Response** `202 Accepted`
```json
{ "meeting_id": "uuid" }
```

---

### `GET /meetings`
List meetings with optional filters.

**Query params**: `project_id`, `status` (`pending`/`processing`/`done`/`failed`), `limit` (default 20), `offset`

---

### `GET /meetings/{meeting_id}`
Get full meeting detail including transcript, summary, action items, decisions, and issues.

**Response fields** (when processing is complete)
- `transcript` — full text from Whisper
- `summary` — GPT-4o generated summary
- `topics` — list of main topics discussed
- `action_items` — `[{owner, task, due_date, status, confidence}]`
- `decisions` — `[{decision_text}]`
- `issues` — `[{issue_text, status}]`

---

### `PATCH /actions/{action_id}`
Update an action item.

**Body** (all fields optional)
```json
{
  "status": "open | in_progress | done",
  "task": "updated task description",
  "owner": "name",
  "due_date": "YYYY-MM-DD"
}
```

---

### `GET /health`
```json
{ "status": "ok", "version": "0.1.0" }
```

## Getting Started

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Setup

1. Clone the repository:
   ```bash
   git clone git@github.com:dhdlswhd34/Recall-ai-agent.git
   cd Recall-ai-agent
   ```

2. Create a `.env` file:
   ```bash
   OPENAI_API_KEY=your_key_here
   ```

3. Start the service:
   ```bash
   docker compose up --build
   ```

   The API is available at `http://localhost:8000`.

4. View interactive docs: `http://localhost:8000/docs`

### Example Usage

```bash
# Upload a meeting
curl -X POST http://localhost:8000/meetings \
  -F "title=Sprint Planning" \
  -F "audio=@meeting.mp3" \
  -F 'participants=["Alice","Bob","Charlie"]'

# Poll until done
curl http://localhost:8000/meetings/{meeting_id}

# Update an action item
curl -X PATCH http://localhost:8000/actions/{action_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

## Configuration

Environment variables (via `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required. OpenAI API key |
| `DB_PATH` | `/data/db/meetings.db` | SQLite database path |
| `UPLOAD_DIR` | `/data/uploads` | Audio file storage |
| `MAX_UPLOAD_SIZE_MB` | `25` | Max upload size in MB |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `[]` | Allowed CORS origins (e.g. `["https://yourapp.com"]`). Empty = deny all |

## Project Structure

```
.
├── app/
│   ├── api/
│   │   ├── meetings.py      # /meetings endpoints
│   │   ├── actions.py       # /actions endpoints
│   │   └── router.py
│   ├── workflow/
│   │   ├── graph.py         # LangGraph pipeline definition
│   │   ├── state.py         # MeetingState TypedDict
│   │   └── nodes/
│   │       ├── validate.py
│   │       ├── transcribe.py
│   │       ├── summarize.py
│   │       ├── extract.py
│   │       ├── embed.py
│   │       └── persist.py
│   ├── models/schemas.py    # Pydantic models
│   ├── database.py          # DB init & connection
│   ├── config.py            # Settings
│   └── main.py              # FastAPI app
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Development

- [`CODE_STYLE.md`](./CODE_STYLE.md) — 코드 스타일 및 규칙 (새 코드 작성 전 참조)
- [`PROGRESS.md`](./PROGRESS.md) — 기능 개발 진행 상황 체크리스트

## License

MIT
