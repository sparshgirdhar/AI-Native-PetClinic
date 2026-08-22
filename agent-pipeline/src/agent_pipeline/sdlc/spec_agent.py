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
Available target files (petclinic-app/src/main/java/.../api/):
- OwnerRestController.java: owner search/get/create/update endpoints
- PetRestController.java: pet get/create/update endpoints, nested under an owner
- VisitRestController.java: visit get/create endpoints, nested under an owner+pet
- PetTypeRestController.java: read-only pet type list endpoint
- ApiExceptionHandler.java: shared 400/404 error handling for all of the above
"""

SPEC_PROMPT = """You are a software architect turning a GitHub issue into a small, \
bounded implementation plan for a Spring Boot REST API.

{file_menu}

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