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

from agent_pipeline.sdlc.schemas import ALLOWED_TARGET_FILES, DOMAIN_FILES, ChangeSpec

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "openai:gpt-4.1-mini")
JAVA_PACKAGE_ROOT = "src/main/java/org/springframework/samples/petclinic"

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
resolve those and it will produce a broken route. Do NOT add any import that is not \
actually used in the code you write — this project's build fails on unused imports. \
If you introduce a helper DTO class, make it public, matching the visibility of the \
surrounding controller class. Output ONLY the raw Java file content — no markdown \
code fences, no explanation, no commentary before or after.
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


def _resolve_path(filename: str, local_repo_path: Path) -> Path:
	"""
	Resolves a file's full path. Known existing files use their entry in
	ALLOWED_TARGET_FILES (API files and domain entities live in different packages).
	Unrecognized filenames are treated as new files — these always go in api/, per
	CODE_GEN_PROMPT_NEW's stated assumption; new domain files are not supported.
	"""
	sub_package = ALLOWED_TARGET_FILES.get(filename, "api")
	return local_repo_path / JAVA_PACKAGE_ROOT / sub_package / filename


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
		current_path = _resolve_path(filename, local_repo_path)
		current_content = current_path.read_text(encoding="utf-8")
		prompt = CODE_GEN_PROMPT_EXISTING.format(
			description=spec.description,
			acceptance_criteria=acceptance_text,
			filename=filename,
			current_content=current_content,
		)
		if filename in DOMAIN_FILES:
			prompt += (
				"\n\nThis is a core domain entity used throughout the application. "
				"Make the SMALLEST possible change that satisfies the acceptance "
				"criteria — prefer adding a single annotation attribute over "
				"restructuring the class. Do not remove or rename any existing "
				"field, getter, or setter."
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
	path = _resolve_path(filename, local_repo_path)
	return path.read_text(encoding="utf-8") if path.exists() else ""


def write_files(file_contents: dict[str, str], local_repo_path: Path) -> list[Path]:
	"""Writes generated content to disk. Returns the list of paths written."""
	written = []
	for filename, content in file_contents.items():
		path = _resolve_path(filename, local_repo_path)
		path.write_text(content, encoding="utf-8")
		written.append(path)
	return written
