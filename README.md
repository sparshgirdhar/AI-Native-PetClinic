# AI-Native PetClinic

A demo project built to demonstrate AI-native Java engineering: a Spring Boot
backend, a hand-built MCP server exposing it to LLM agents, and an agentic SDLC
pipeline that turns a GitHub issue into a reviewed, tested, merged pull request.

Built on top of [`spring-projects/spring-petclinic`](https://github.com/spring-projects/spring-petclinic).

## Why this project exists

Built to demonstrate hands-on experience with:
- Java 17 / Spring Boot REST APIs, layered cleanly on top of an existing MVC app
- Building and deploying an **MCP server** exposing a Java backend to LLM agents
- **Agent orchestration** (LangChain's `create_agent`) with real tool-use, self-correction, and disambiguation logic
- An **agentic SDLC pipeline**: spec drafting → human approval → AI code generation → diff review → build validation → git/PR automation → CI
- Integrating agentic workflows with **GitHub via MCP**
- Critically evaluating AI-generated code and catching real correctness bugs before they ship

## Two independent flows

This project has two separate agentic flows. They share `petclinic-app` as the
underlying application, but connect to it in different ways for different
purposes — worth understanding as two distinct systems, not one pipeline.

| | Flow 1: Conversational agent | Flow 2: SDLC pipeline |
|---|---|---|
| **Purpose** | Let an LLM *use* the running app on a user's behalf (find owners, schedule visits, etc.) | Let an LLM *change the app's own code*, from a GitHub issue to a merged PR |
| **MCP server** | `mcp-server/` — hand-built in Java, wraps petclinic-app's REST API | GitHub's official hosted MCP server — used as-is, not built by this project |
| **Where it lives** | `agent-pipeline/src/agent_pipeline/agent.py`, `cli.py`, `app_gradio.py` | `agent-pipeline/src/agent_pipeline/sdlc/` |
| **What's running while it works** | `petclinic-app` + `mcp-server`, both live | `petclinic-app` on disk (read/written directly), no `mcp-server` involved |
| **Details** | [`docs/conversational-agent.md`](docs/conversational-agent.md) | [`docs/sdlc-pipeline.md`](docs/sdlc-pipeline.md) |

## Repo structure

```
ai-native-petclinic/
├── petclinic-app/          Spring Boot app (fork of spring-petclinic) + REST API layer
├── mcp-server/              Java MCP server exposing petclinic-app to LLM agents (Flow 1 only)
├── agent-pipeline/          Python — both flows live here
│   └── src/agent_pipeline/
│       ├── agent.py, cli.py, app_gradio.py    Flow 1: conversational agent
│       └── sdlc/                              Flow 2: SDLC pipeline
├── docs/
│   ├── conversational-agent.md
│   └── sdlc-pipeline.md
└── .github/workflows/       CI (path-scoped per component)
```

## Quick start

**Prerequisites:** Java 17, Maven, Python 3.10+, an OpenAI API key. Flow 2 also
needs a GitHub fine-grained PAT (`Issues: Read-only`, `Pull requests: Read and
write`, `Contents: Read-only`).

```bash
git clone <this repo> && cd ai-native-petclinic
cd petclinic-app && ./mvnw spring-boot:run          # localhost:8080 — needed by both flows
```

Then jump to whichever flow you want:
- **[Conversational agent →](docs/conversational-agent.md)**
- **[SDLC pipeline →](docs/sdlc-pipeline.md)**

## Design decisions worth knowing

- **Why no Filesystem MCP for local file access in the SDLC pipeline:** the
  Spec Agent already resolves *which* files to touch before the Code Agent
  runs — there's no dynamic, multi-turn exploration for an MCP tool to add
  value to, so plain `pathlib` I/O does the same job without the protocol
  overhead.
- **Why GitHub MCP toolsets are restricted** (`issues`, `pull_requests` only,
  further filtered to 2 specific tools in code): GitHub MCP's full tool schema
  costs real context tokens; scoping it down keeps the pipeline's own token
  budget under control.
- **Why the SDLC pipeline uses single-shot generation, not an open coding-agent
  loop:** cost and predictability. A bounded, single-shot design with
  mandatory diff review makes every change auditable and keeps the model
  requirement modest (`gpt-4.1-mini` throughout, no frontier model needed).

## Known v1 limitations / what's deferred to v2

- No automated CI-failure diagnose-and-retry loop in the SDLC pipeline.
- `mvn compile`/`test` after code generation is a manual step, not an
  automatic gate.
- No RAG layer over docs — deferred as a nice-to-have.
- SDLC pipeline uses a fixed 9-file allowlist, not open repository
  exploration — a deliberate cost/predictability tradeoff, not a technical
  ceiling.
