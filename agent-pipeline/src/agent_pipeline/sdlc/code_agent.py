"""
Code Agent.

Single-shot generation, same discipline as the Spec Agent: no file-exploration tool
loop, no multi-turn reasoning about the codebase. The Spec Agent already decided
exactly which file(s) to touch; this stage's only job is, for each one, read its
current content and generate the complete replacement.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from agent_pipeline.sdlc.schemas import ChangeSpec

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "openai:gpt-4.1-mini")
API_PACKAGE_RELATIVE = "src/main/java/org/springframework/samples/petclinic/api"

CODE_GEN_PROMPT_EXISTING = """You are a senior Java/Spring Boot engineer making a small, \
precise change to an existing file.

Known domain classes — import these from EXACTLY these packages, do not guess a \
different package even if it seems plausible:
- Owner, Pet, PetType, Visit, OwnerRepository, PetTypeRepository: \
org.springframework.samples.petclinic.owner

Change description:
{description}

Acceptance criteria:
{acceptance_criteria}

Current content of {filename}:
```java
{current_content}
```

Return the COMPLETE updated content of {filename}, implementing the change above. \
Follow the exact coding style, formatting, and conventions already used in this file \
(indentation, brace style, import ordering, Javadoc style, error-handling patterns). \
Do not make unrelated changes. Any @GetMapping/@PostMapping/etc. path must be a \
normal relative path segment appended to this class's existing @RequestMapping — \
never use ".." or any other relative-path escape trick, since Spring does not \
resolve those and it will produce a broken route. Output ONLY the raw Java file \
content — no markdown code fences, no explanation, no commentary before or after.
"""

CODE_GEN_PROMPT_NEW = """You are a senior Java/Spring Boot engineer creating a new file.

Known domain classes — import these from EXACTLY these packages, do not guess a \
different package even if it seems plausible:
- Owner, Pet, PetType, Visit, OwnerRepository, PetTypeRepository: \
org.springframework.samples.petclinic.owner

Change description:
{description}

Acceptance criteria:
{acceptance_criteria}

New file to create: {filename}
Reason it's a new file rather than an addition to an existing one: {reason}

This file belongs in package org.springframework.samples.petclinic.api, alongside \
existing REST controllers in that package (which follow standard Spring Boot \
@RestController conventions, tab indentation, and use ResponseEntity for responses). \
Output ONLY the raw Java file content — no markdown code fences, no explanation, no \
commentary before or after.
"""


def _api_dir(local_repo_path: Path) -> Path:
	return local_repo_path / API_PACKAGE_RELATIVE


def _strip_fences(text: str) -> str:
	"""Defensively removes markdown code fences if the model added them despite instructions."""
	text = text.strip()
	if text.startswith("```"):
		lines = text.splitlines()
		if lines and lines[0].startswith("```"):
			lines = lines[1:]
		if lines and lines[-1].strip() == "```":
			lines = lines[:-1]
		text = "\n".join(lines)
	return text.strip() + "\n"


async def _generate_one(
	spec: ChangeSpec, filename: str, local_repo_path: Path, is_new: bool, reason: str = ""
) -> str:
	model = init_chat_model(MODEL_NAME)
	acceptance_text = "\n".join(f"- {c}" for c in spec.acceptance_criteria)

	if is_new:
		prompt = CODE_GEN_PROMPT_NEW.format(
			description=spec.description,
			acceptance_criteria=acceptance_text,
			filename=filename,
			reason=reason,
		)
	else:
		current_path = _api_dir(local_repo_path) / filename
		current_content = current_path.read_text(encoding="utf-8")
		prompt = CODE_GEN_PROMPT_EXISTING.format(
			description=spec.description,
			acceptance_criteria=acceptance_text,
			filename=filename,
			current_content=current_content,
		)

	response = await model.ainvoke(prompt)
	return _strip_fences(response.content)


async def generate_all_files(spec: ChangeSpec, local_repo_path: Path) -> dict[str, str]:
	"""
	Generates new content for every file in the spec, WITHOUT writing to disk.
	Returns {filename: new_content} so the caller can show a diff before deciding
	whether to actually write anything.
	"""
	results = {}
	for filename in spec.target_files:
		results[filename] = await _generate_one(spec, filename, local_repo_path, is_new=False)
	for nf in spec.new_files:
		results[nf.filename] = await _generate_one(
			spec, nf.filename, local_repo_path, is_new=True, reason=nf.reason
		)
	return results


def read_current_content(filename: str, local_repo_path: Path) -> str:
	"""Empty string for new files (nothing to diff against)."""
	path = _api_dir(local_repo_path) / filename
	return path.read_text(encoding="utf-8") if path.exists() else ""


def write_files(file_contents: dict[str, str], local_repo_path: Path) -> list[Path]:
	"""Writes generated content to disk. Returns the list of paths written."""
	api_dir = _api_dir(local_repo_path)
	written = []
	for filename, content in file_contents.items():
		path = api_dir / filename
		path.write_text(content, encoding="utf-8")
		written.append(path)
	return written