"""
Spec Agent.

Deliberately NOT an open-ended tool-calling agent loop — we already know exactly
which issue to read (the user passes --issue on the command line), so there's no
"decide which tool to call" reasoning needed. This is two plain steps instead:
  1. Call get_issue directly, once, to fetch the issue's title/body.
  2. A single structured-output LLM call maps that text (+ the known file menu)
     into a ChangeSpec.
This keeps token usage and moving parts to a minimum for a stage that doesn't need
multi-turn reasoning.
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from agent_pipeline.sdlc.github_client import get_github_tools
from agent_pipeline.sdlc.schemas import ALLOWED_TARGET_FILES, ChangeSpec

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "openai:gpt-4.1-mini")

# One-line description of each allowed file's responsibility, so the LLM can pick
# sensibly without needing to read the actual source first.
FILE_MENU = """
Available target files (petclinic-app/src/main/java/.../api/), with their class-level
@RequestMapping prefix — a new endpoint's URL MUST start with that exact prefix,
since Spring appends @GetMapping paths onto it and cannot escape it:

- OwnerRestController.java (@RequestMapping("/api/owners")): owner search/get/create/update,
  and any endpoint of the form /api/owners/{ownerId}/... that is NOT specific to one pet
- PetRestController.java (@RequestMapping("/api/owners/{ownerId}/pets")): pet get/create/update
- VisitRestController.java (@RequestMapping("/api/owners/{ownerId}/pets/{petId}/visits")):
  visit get/create for ONE SPECIFIC pet — cannot host any route without a petId segment
- PetTypeRestController.java (no class-level mapping, @GetMapping("/api/pettypes") directly
  on the method): read-only pet type list endpoint
- ApiExceptionHandler.java (@RestControllerAdvice, not a controller): shared 400/404 error
  handling for all of the above — never a target_file for a new endpoint

Also available (petclinic-app/src/main/java/.../owner/) — core JPA domain entities, NOT
REST controllers. Only propose one of these as a target_file when the change genuinely
requires it (e.g. a JPA mapping/cascade behavior change) — never for adding a new
endpoint, which always belongs in one of the api/ files above instead:
- Owner.java: the Owner JPA entity, including its @OneToMany pets collection mapping
- Pet.java: the Pet JPA entity, including its @OneToMany visits collection mapping
- Visit.java: the Visit JPA entity
- PetType.java: the PetType JPA entity

IMPORTANT domain gotcha: Owner.pets is mapped with cascade = CascadeType.ALL but
WITHOUT orphanRemoval = true. This means removing a Pet from Owner.getPets() and
saving does NOT delete it from the database — it only disassociates it (sets its
owner_id to NULL), leaving an orphaned row behind. If an issue asks to actually
DELETE a pet (not just remove/hide it), you MUST include Owner.java in target_files
alongside the controller file, to add orphanRemoval = true to that mapping — a
controller-only change will compile and return success but silently fail to delete
anything.

Caution: domain entity changes have a much wider blast radius than a controller change —
they affect every endpoint that touches that entity, not just one. Prefer the smallest
possible change (e.g. adding a single annotation attribute) over restructuring.
"""

ROUTING_RULE = """
Critical routing rule: choose target_files based on which file's class-level
@RequestMapping prefix the new endpoint's URL actually falls under, as listed above.
NEVER propose a relative-path escape trick like "/../../something" to add a route
outside a class's mapped prefix — Spring does not support this and it silently
produces a broken/incorrect route, not the intended URL. If no existing file's
prefix is a real match for the new endpoint, propose a new file in new_files instead
of forcing it into a file whose prefix doesn't fit.
"""

SPEC_PROMPT = """You are a software architect turning a GitHub issue into a small, \
bounded implementation plan for a Spring Boot REST API.

{file_menu}
{routing_rule}

Rules:
- Only pick target_files from the list above, by exact filename.
- Prefer extending an existing file over creating a new one. Only propose a new \
file if the change genuinely doesn't belong in any existing file (e.g. a new \
resource type with no existing controller).
- Maximum 3 existing files, maximum 1 new file.
- acceptance_criteria must be concrete and checkable (e.g. "GET /api/owners/{{id}}/visits \
returns 404 if the owner does not exist"), not vague goals.

GitHub issue #{issue_number}: {issue_title}

{issue_body}
"""


async def fetch_issue(owner: str, repo: str, issue_number: int) -> dict:
	"""Fetches one issue's title/body via the GitHub MCP issue_read tool."""
	import json

	tools = await get_github_tools({"issue_read"})
	get_issue_tool = tools[0]

	result = await get_issue_tool.ainvoke(
		{"owner": owner, "repo": repo, "issue_number": issue_number, "method": "get"}
	)

	# MCP tool results commonly come back as a list of content blocks
	# (e.g. [{"type": "text", "text": "<json>"}]) rather than a plain dict/string.
	if isinstance(result, list):
		text_parts = []
		for item in result:
			if isinstance(item, dict) and "text" in item:
				text_parts.append(item["text"])
			elif isinstance(item, str):
				text_parts.append(item)
		result = "\n".join(text_parts)

	if isinstance(result, str):
		result = json.loads(result)

	return result


async def build_change_spec(owner: str, repo: str, issue_number: int) -> ChangeSpec:
	"""Fetches the issue and produces a structured ChangeSpec from it."""
	issue = await fetch_issue(owner, repo, issue_number)
	issue_title = issue.get("title", "")
	issue_body = issue.get("body", "") or "(no description provided)"

	model = init_chat_model(MODEL_NAME)
	structured_model = model.with_structured_output(ChangeSpec)

	prompt = SPEC_PROMPT.format(
		file_menu=FILE_MENU,
		routing_rule=ROUTING_RULE,
		issue_number=issue_number,
		issue_title=issue_title,
		issue_body=issue_body,
	)

	spec = await structured_model.ainvoke(prompt)
	# Belt-and-suspenders: fill these in from what we actually fetched, in case the
	# model omits or alters them.
	spec.issue_number = issue_number
	spec.issue_title = issue_title
	return spec