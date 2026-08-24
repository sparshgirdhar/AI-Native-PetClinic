# Flow 1: Conversational agent

This is an LLM agent that uses PetClinic on a user's behalf (finding owners, addingpets, scheduling visits) by calling a hand-built MCP server that wraps `petclinic-app`'s REST API.  
`mcp-server` turns PetClinic's APIs into callable tools for an LLM, so an agent can do what a person would normally do through the UI, just by asking in plain language.

## Architecture

```mermaid
flowchart TB
    User(["Person"]) -->|chat| CLI["cli.py / app_gradio.py"]

    subgraph python["Python - LangChain"]
        CLI --> Agent["create_agent<br/>+ system prompt"]
    end

    subgraph java["Java - Spring Boot"]
        MCPServer["mcp-server :8081<br/>Spring AI MCP starter"]
        PetClinic["petclinic-app :8080<br/>REST APIs"]
        MCPServer -->|RestClient| PetClinic
        PetClinic --> DB[("H2, in-memory")]
    end

    Agent -->|"MCP · Streamable HTTP"| MCPServer

    classDef py fill:#eef2ff,stroke:#6366f1,color:#1e1b4b
    classDef java fill:#fff7ed,stroke:#f97316,color:#7c2d12
    classDef store fill:#f0fdf4,stroke:#22c55e,color:#14532d
    class CLI,Agent py
    class MCPServer,PetClinic java
    class DB store
```

`mcp-server` is a separate Java process whose only job is translating between MCP's protocol and `petclinic-app`'s plain REST/JSON API. It holds no business logic of its own.

## What `mcp-server` exposes

**Tools (actions the agent can invoke):**
- `findOwners` — search owners by last name
- `getOwner` — fetch a single owner, including their pets and each pet's visit history
- `createOwner` — register a new owner
- `createPet` — add a pet to an owner, resolving a plain name like `"dog"` to petclinic-app's internal type ID itself, so the model never has to know or guess one
- `updatePet` — change a pet's details
- `createVisit` — schedule a visit for a pet
- `getVisits` — list a pet's visit history
- `getPetTypes` — list valid pet types
- `getVets` — list vets and their specialties

**Resources (read-only reference data):** `vets://list`, `pet-types://list`

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
cd petclinic-app && ./mvnw spring-boot:run   # Starts the Spring Boot backend on :8080

cd mcp-server && ./mvnw spring-boot:run      # Starts the Java MCP server on :8081

cd agent-pipeline                            # The Python side

python -m venv .venv                         # Creates an isolated Python environment
source .venv/bin/activate                    # Activates it (Windows: .venv\Scripts\activate)

pip install -e .                             # Installs deps + registers agent_pipeline as
                                              # a package, via pyproject.toml — makes
                                              # `python -m agent_pipeline...` work from
                                              # anywhere. requirements.txt is redundant
                                              # with this, safe to ignore or delete.

cp .env.example .env                         # Then fill in OPENAI_API_KEY

python -m agent_pipeline.cli                 # Terminal chat
# or
python -m agent_pipeline.app_gradio          # Browser chat UI instead
```

Try: *"Find owner Franklin and list his pets"*, then work up to something like *"Schedule a visit for George Franklin's cat Leo on 2026-11-20 for a checkup"* to see id-resolution and tool-chaining in action.
