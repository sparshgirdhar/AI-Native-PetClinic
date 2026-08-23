"""
Entrypoint for the SDLC pipeline.

Usage:
    python -m agent_pipeline.sdlc.run_sdlc --owner sparshgirdhar --repo ai-native-petclinic --issue 3

v1 scope so far: fetch issue -> ChangeSpec -> human approval -> generate updated
file(s) -> show diff -> second human approval -> write to disk. Git branch/commit/
push and PR creation are added next, once this is proven on a real issue.
"""

import argparse
import asyncio
import difflib
import os
import subprocess
from pathlib import Path

from agent_pipeline.sdlc.code_agent import generate_all_files, read_current_content, write_files
from agent_pipeline.sdlc.spec_agent import build_change_spec

DEFAULT_LOCAL_REPO_PATH = "../petclinic-app"


def print_spec(spec):
	print("\n" + "=" * 60)
	print(f"Issue #{spec.issue_number}: {spec.issue_title}")
	print("=" * 60)
	print(f"\nDescription:\n  {spec.description}")

	print(f"\nTarget files to modify ({len(spec.target_files)}):")
	for f in spec.target_files:
		print(f"  - {f}")

	if spec.new_files:
		print(f"\nNew files to create ({len(spec.new_files)}):")
		for nf in spec.new_files:
			print(f"  - {nf.filename}: {nf.reason}")

	print(f"\nAcceptance criteria:")
	for i, ac in enumerate(spec.acceptance_criteria, 1):
		print(f"  {i}. {ac}")
	print()


def print_diff(filename: str, old_content: str, new_content: str):
	print(f"\n--- {filename} ---")
	if not old_content:
		print("(new file)")
		print(new_content)
		return

	diff = difflib.unified_diff(
		old_content.splitlines(keepends=True),
		new_content.splitlines(keepends=True),
		fromfile=f"a/{filename}",
		tofile=f"b/{filename}",
	)
	diff_text = "".join(diff)
	print(diff_text if diff_text else "(no textual changes)")


async def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--owner", required=True, help="GitHub repo owner/org")
	parser.add_argument("--repo", required=True, help="GitHub repo name")
	parser.add_argument("--issue", required=True, type=int, help="Issue number to implement")
	parser.add_argument(
		"--local-repo-path",
		default=DEFAULT_LOCAL_REPO_PATH,
		help="Path to the local petclinic-app checkout (default: ../petclinic-app, "
		"assuming the standard monorepo layout)",
	)
	args = parser.parse_args()
	local_repo_path = Path(args.local_repo_path).resolve()

	if not local_repo_path.exists():
		print(f"Local repo path does not exist: {local_repo_path}")
		return

	# --- Spec Agent ---
	print(f"Fetching issue #{args.issue} from {args.owner}/{args.repo}...")
	spec = await build_change_spec(args.owner, args.repo, args.issue)
	print_spec(spec)

	problems = spec.validate_budget()
	if problems:
		print("Spec exceeds the change budget:")
		for p in problems:
			print(f"  - {p}")
		print("\nStopping here — this issue needs a smaller scope or manual handling.")
		return

	if input("Approve this plan? [y/N] ").strip().lower() != "y":
		print("Not approved. Stopping.")
		return

	# --- Code Agent ---
	print("\nGenerating code changes...")
	new_contents = await generate_all_files(spec, local_repo_path)

	print("\n" + "=" * 60)
	print("PROPOSED CHANGES")
	print("=" * 60)
	for filename, new_content in new_contents.items():
		old_content = read_current_content(filename, local_repo_path)
		print_diff(filename, old_content, new_content)

	if input("\nWrite these changes to disk? [y/N] ").strip().lower() != "y":
		print("Not written. Stopping.")
		return

	written = write_files(new_contents, local_repo_path)
	print(f"\nWrote {len(written)} file(s):")
	for p in written:
		print(f"  - {p}")

	print("\nApplying project formatting rules (spring-javaformat:apply)...")
	mvnw = "mvnw.cmd" if os.name == "nt" else "./mvnw"
	format_result = subprocess.run(
		[mvnw, "spring-javaformat:apply"],
		cwd=local_repo_path,
		capture_output=True,
		text=True,
	)
	if format_result.returncode != 0:
		print("Warning: spring-javaformat:apply failed — you may need to run it manually.")
		print(format_result.stdout[-2000:])
		print(format_result.stderr[-2000:])
	else:
		print("Formatting applied.")

	print(
		"\nNext: run './mvnw clean compile' (or 'test') inside petclinic-app to confirm "
		"the change builds, then review the formatted diff with 'git diff'.\n"
		"(Git branch/commit/push and PR creation not yet built — stopping here for now.)"
	)


if __name__ == "__main__":
	asyncio.run(main())