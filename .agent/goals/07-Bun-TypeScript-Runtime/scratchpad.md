# Goal 07 — Bun + TypeScript Runtime (LangGraph JS)

Status: ⚪ Not Started  
Priority: High  
Owner: You  
Created: 2026-01-30  
Last Updated: 2026-01-30  
Depends On: Goal 06 (Robyn Runtime) — Complete first to validate API shape

---

## Objective

After proving the LangGraph/CopilotKit API parity with Robyn (Python + Rust), reimplement the entire runtime in TypeScript running on Bun with LangGraph JS under the hood.

### Why Bun + TypeScript?

1. **JIT Performance** — Compiled TypeScript → JavaScript benefits from V8/JSC JIT optimization, often faster than interpreted Python
2. **Bun Native Performance** — Anton Putra's benchmarks show Bun outperforming Python for:
   - HTTP server throughput
   - Database connections (native SQLite, Postgres drivers)
   - File I/O operations
3. **Single Runtime** — Bun includes bundler, test runner, package manager — no toolchain fragmentation
4. **LangGraph JS** — Official LangChain/LangGraph TypeScript SDK with full feature parity
5. **Type Safety** — Compile-time type checking reduces runtime errors
6. **Modern Ecosystem** — Better async/await, native fetch, Web APIs

### Performance Reference

- [Anton Putra: Bun vs Python Performance](https://www.youtube.com/watch?v=...) — Shows Bun advantages for:
  - HTTP request handling
  - Database connections
  - JSON serialization
  - File system operations

---

## Context

### Prerequisite: Goal 06 (Robyn Runtime)

Complete the Robyn implementation first because:
1. Validates the API shape we need to replicate
2. Creates test harnesses that work with both runtimes
3. Documents edge cases and schema requirements
4. Robyn is faster to prototype (Python familiarity)

### API Surface to Replicate

Same as Goal 06 — LangGraph Runtime API parity:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/assistants` | POST/GET/PATCH/DELETE | Assistant CRUD |
| `/threads` | POST/GET/DELETE | Thread CRUD |
| `/threads/{id}/runs` | POST/GET | Run management |
| `/threads/{id}/runs/wait` | POST | Synchronous execution |
| `/threads/{id}/state` | GET | Current state |
| `/threads/{id}/history` | GET | Run history |

Plus CopilotKit compatibility endpoints (TBD based on Goal 06 learnings).

---

## Tech Stack

### Core
- **Bun** — JavaScript runtime (faster than Node.js)
- **TypeScript** — Type-safe JavaScript
- **LangGraph JS** — `@langchain/langgraph` for agent orchestration
- **Hono** or **Elysia** — Bun-native HTTP framework (fast, type-safe)

### Database
- **Bun SQLite** — Native, zero-dependency (for local dev)
- **Postgres** — Via Bun's native driver or `postgres` package (for Supabase)

### Auth
- **Supabase JS** — `@supabase/supabase-js` for JWT verification

### LLM
- **LangChain OpenAI** — `@langchain/openai` for vLLM/Azure/OpenAI

---

## Proposed Directory Structure

```
bun_server/
├── package.json
├── tsconfig.json
├── bun.lockb
├── src/
│   ├── index.ts           # Entry point
│   ├── config.ts          # Environment configuration
│   ├── auth/
│   │   └── supabase.ts    # JWT verification middleware
│   ├── storage/
│   │   ├── memory.ts      # In-memory storage
│   │   └── postgres.ts    # Supabase Postgres storage
│   ├── models/
│   │   ├── assistant.ts
│   │   ├── thread.ts
│   │   └── run.ts
│   ├── routes/
│   │   ├── assistants.ts
│   │   ├── threads.ts
│   │   └── runs.ts
│   ├── agent/
│   │   ├── graph.ts       # LangGraph JS agent definition
│   │   └── tools.ts       # Tool definitions
│   └── executor.ts        # Agent execution wrapper
└── tests/
    └── e2e.test.ts        # Bun test runner
```

---

## Task Breakdown (Tentative)

### Task 01 — Bun Project Setup
- Initialize Bun project with TypeScript
- Add dependencies: `@langchain/langgraph`, `@langchain/openai`, `@supabase/supabase-js`
- Choose HTTP framework (Hono vs Elysia)
- Basic health endpoint

### Task 02 — Port Agent Graph to LangGraph JS
- Translate `tools_agent/agent.py` to TypeScript
- Implement custom endpoint support (vLLM)
- Test with local vLLM server

### Task 03 — Auth Middleware
- Port Supabase JWT verification
- Integrate with Bun HTTP framework

### Task 04 — Storage Layer
- In-memory implementation
- Postgres implementation for Supabase

### Task 05 — API Endpoints
- Assistants CRUD
- Threads CRUD
- Runs lifecycle
- State/History retrieval

### Task 06 — Integration Testing
- Port `test_with_auth_vllm.py` to TypeScript/Bun test
- Validate API parity with Robyn version

### Task 07 — Streaming & SSE
- Server-Sent Events for real-time responses
- Token streaming

### Task 08 — CopilotKit Compatibility
- Research CopilotKit protocol
- Implement required endpoints

### Task 09 — Performance Benchmarking
- Compare Robyn vs Bun throughput
- Document results

### Task 10 — Documentation
- README with Bun setup
- API documentation
- Performance comparison

---

## Success Criteria

### Must Have
- [ ] Bun server boots and serves health endpoint
- [ ] LangGraph JS agent executes with vLLM backend
- [ ] Supabase JWT auth works
- [ ] Pass same E2E tests as Robyn version
- [ ] API responses match Robyn/LangGraph schema

### Should Have
- [ ] SSE streaming for responses
- [ ] Postgres persistence via Supabase
- [ ] Performance metrics showing improvement over Python

### Nice to Have
- [ ] CopilotKit protocol compatibility
- [ ] Multi-worker scaling
- [ ] OpenAPI documentation generation

---

## Dependencies

### NPM Packages (via Bun)
```json
{
  "dependencies": {
    "@langchain/langgraph": "^0.2.0",
    "@langchain/openai": "^0.3.0",
    "@langchain/core": "^0.3.0",
    "@supabase/supabase-js": "^2.45.0",
    "hono": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/bun": "latest"
  }
}
```

---

## Risks & Mitigations

### Risk 1: LangGraph JS feature parity
**Mitigation**: Check LangGraph JS docs for `create_react_agent` equivalent, may need custom graph

### Risk 2: MCP tool integration in JS
**Mitigation**: Research `@modelcontextprotocol/sdk` for TypeScript MCP client

### Risk 3: Learning curve (Bun + new frameworks)
**Mitigation**: Start after Robyn proves the API shape, reducing unknowns

### Risk 4: Debugging compiled JS vs Python
**Mitigation**: Use TypeScript source maps, Bun's built-in debugger

---

## References

- [Bun Documentation](https://bun.sh/docs)
- [LangGraph JS](https://js.langchain.com/docs/langgraph)
- [Hono Framework](https://hono.dev/)
- [Elysia Framework](https://elysiajs.com/)
- [Anton Putra Performance Benchmarks](https://www.youtube.com/@AntonPutra)
- [Supabase JS Client](https://supabase.com/docs/reference/javascript)

---

## Notes

- This goal depends on Goal 06 completion — Robyn validates the API contract first
- Consider running both runtimes in parallel during transition
- Bun's native test runner eliminates need for Jest/Vitest
- TypeScript strict mode recommended for better type safety