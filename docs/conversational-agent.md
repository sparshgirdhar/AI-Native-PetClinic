# Flow 1: Conversational agent

An LLM agent that uses PetClinic on a user's behalf — finding owners, adding
pets, scheduling visits — by calling a hand-built MCP server that wraps
`petclinic-app`'s REST API.

## Architecture

```mermaid
flowchart LR
    User -->|chat| CLI[cli.py / app_gradio.py]
    CLI --> Agent[LangChain create_agent]
    Agent -->|MCP: Streamable HTTP| MCPServer[mcp-server - Java / Spring AI]
    MCPServer -->|REST| PetClinic[petclinic-app]
    PetClinic --> DB[(H2, in-memory)]
```

`mcp-server` is a separate Java process whose only job is translating between
MCP's protocol and `petclinic-app`'s plain REST/JSON API. It holds no business
logic of its own.

## What `mcp-server` exposes

**Tools (actions):** `findOwners`, `getOwner`, `createOwner`, `createPet`,
`updatePet`, `createVisit`, `getVisits`, `getPetTypes`, `getVets`.

**Resources (read-only reference data):** `vets://list`, `pet-types://list` —
registered via `@McpResource`, separate from the tools above per the MCP spec's
distinction between agent-invoked actions and addressable reference data.

Full tool implementation: `mcp-server/src/main/java/org/example/mcpserver/tools/PetClinicTools.java`.

## Design choices worth knowing

- **The agent never handles internal database IDs.** `findOwners`/`getOwner`
  return an owner's full pet list (with names *and* ids) in one call, so the
  agent can resolve "Sparsh Girdhar's dog Coco" to a real `petId` itself,
  without ever surfacing an id to the user.
- **Pet type names, not ids, are the tool's input.** `createPet` accepts a
  human name like `"dog"` and resolves it to petclinic-app's internal type id
  server-side — the LLM should never need to know or guess these ids.
- **Errors are designed to be self-correcting.** Tool methods throw a plain
  exception with a clear, actionable message (e.g. "Invalid date format,
  expected yyyy-MM-dd") rather than crashing — Spring AI's tool-calling layer
  surfaces that message back to the model as tool output, so it can retry with
  a corrected value on its own.
- **The system prompt was hardened through real testing, not written once and
  left alone.** Notable fixes made after observing bad behavior:
  - The agent initially **fabricated a pet's birth date** when the user didn't
    provide one, and presented it as fact. Fixed with an explicit instruction
    never to invent required field values — ask instead.
  - The agent needed to **distinguish an exact-duplicate owner from a
    genuinely ambiguous one** when creating an owner with a name that already
    exists. Asking "is this the same person?" is only a fair question when
    there's actually differing information to compare — if every field
    matches, the agent now says so plainly and asks a yes/no about creating a
    duplicate, rather than asking an unanswerable question.

## Running it

```bash
cd petclinic-app && ./mvnw spring-boot:run       # localhost:8080
cd mcp-server && ./mvnw spring-boot:run           # localhost:8081

cd agent-pipeline
pip install -e .
cp .env.example .env    # fill in OPENAI_API_KEY

python -m agent_pipeline.cli          # terminal chat
# or
python -m agent_pipeline.app_gradio   # browser chat UI
```

Try: *"Find owner Franklin and list his pets"*, then work up to something like
*"Schedule a visit for George Franklin's cat Leo on 2026-11-20 for a checkup"*
to see id-resolution and tool-chaining in action.
