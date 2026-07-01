# AI Assistant — Frontend & Mobile Contract

> Contract for the **implemented** AI endpoints (source of truth: `app/ai`).
> Phase-2 feature. See `docs/ARCHITECTURE.md` §3 (AI assistant).

## Context
A retrieval-augmented (RAG) assistant that answers user questions **grounded in
BarriApp's own knowledge base** (FAQs, policies) and, optionally, the user's order
status. Admins curate the knowledge base; any authenticated user chats. Answers
are in Spanish.

**How it works:** the question is embedded, the most relevant knowledge chunks are
retrieved, and an LLM composes a grounded answer. With `ANTHROPIC_API_KEY` set the
LLM is **Claude**; otherwise a deterministic fallback composes the answer from the
top source (so the feature works offline/in dev). Retrieval is in-app cosine today;
Atlas Vector Search (`$vectorSearch`) is the production path.

## Endpoints

### POST `/api/v1/ai/knowledge`  (super_admin)
Ingest a knowledge item (embedded on write). Request:
```json
{ "content": "Puedes pagar en efectivo o con Wompi al recibir tu pedido.",
  "source_type": "faq", "metadata": {} }
```
`source_type`: `faq` | `policy` | `store` | `product`. Response `201`: `{ id, source_type, content }`.

### POST `/api/v1/ai/chat`  (auth)
Ask the assistant. Request:
```json
{ "message": "¿Cómo puedo pagar mi pedido?", "conversation_id": null, "order_id": null }
```
- `conversation_id` (optional): continue an existing conversation.
- `order_id` (optional): if it's the caller's order, its status is added to the
  context (e.g. "¿dónde está mi pedido?").
Response `200`:
```json
{ "answer": "Según la información de BarriApp: Puedes pagar en efectivo o con Wompi...",
  "conversation_id": "665f...",
  "sources": [{ "id": "665e...", "source_type": "faq", "snippet": "Puedes pagar..." }] }
```

### GET `/api/v1/ai/conversations/{id}`  (auth — owner)
Full conversation history: `{ id, messages: [{role, content, at}], created_at }`.
Errors: `403 forbidden`, `404 not_found`.

## Notes for the client
- Render `answer`; optionally show `sources` for transparency ("based on…").
- Keep `conversation_id` to maintain a threaded chat.
- Pass `order_id` from the current order screen so "where is my order?" is answered
  with the real status.

## Not yet implemented (planned)
Real LLM tool-calling loop (the assistant autonomously querying the API), Atlas
Vector Search retrieval at scale, streaming responses, automatic knowledge
ingestion from stores/products, and multi-turn context windowing.
