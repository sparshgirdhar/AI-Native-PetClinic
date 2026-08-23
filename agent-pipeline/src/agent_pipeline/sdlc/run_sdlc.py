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
from agent_pipeline.sdlc.git_ops import branch_name_for_issue, commit_files, create_branch, find_git_root, push_branch
from agent_pipeline.sdlc.pr_ops import create_pull_request
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
		shell=(os.name == "nt"),  # .cmd/.bat files require the shell to execute on Windows
	)
	if format_result.returncode != 0:
		print("Warning: spring-javaformat:apply failed — you may need to run it manually.")
		print(format_result.stdout[-2000:])
		print(format_result.stderr[-2000:])
	else:
		print("Formatting applied.")

	print(
		"\nRecommended: run './mvnw clean compile' inside petclinic-app now to confirm "
		"the change builds before publishing it."
	)

	# --- Branch + commit + push + PR ---
	if input("\nCreate a branch, commit, push, and open a PR? [y/N] ").strip().lower() != "y":
		print("Not published. Changes remain uncommitted locally — review with 'git diff'.")
		return

	git_root = find_git_root(local_repo_path)
	branch_name = branch_name_for_issue(spec.issue_number, spec.issue_title)
	commit_message = f"{spec.description}\n\nFixes #{spec.issue_number}"
	pr_body = (
		f"{spec.description}\n\n"
		f"**Acceptance criteria:**\n"
		+ "\n".join(f"- {ac}" for ac in spec.acceptance_criteria)
		+ f"\n\nCloses #{spec.issue_number}\n\n"
		f"_Generated by agent_pipeline.sdlc — reviewed and approved before publishing._"
	)

	print(f"\nCreating branch '{branch_name}'...")
	create_branch(branch_name, git_root)

	print("Committing changes...")
	commit_files(written, commit_message, git_root)

	print("Pushing branch...")
	push_branch(branch_name, git_root)

	print("Opening pull request...")
	pr = await create_pull_request(
		owner=args.owner,
		repo=args.repo,
		branch_name=branch_name,
		base_branch="main",
		title=spec.issue_title,
		body=pr_body,
	)
	pr_url = pr.get("html_url") or pr.get("url") or "(URL not found in response — see full response below)"
	print(f"\nPull request opened: {pr_url}")
	if "html_url" not in pr and "url" not in pr:
		print(pr)


if __name__ == "__main__":
	asyncio.run(main())