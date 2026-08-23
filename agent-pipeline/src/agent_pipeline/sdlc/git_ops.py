"""
Local git operations: create a feature branch, commit the changed files, push it.

Runs at the actual git repository root (the monorepo root), not at local_repo_path
(petclinic-app) — petclinic-app is a subfolder, not its own git repo.
"""

import re
import subprocess
from pathlib import Path


def find_git_root(start_path: Path) -> Path:
	"""Walks up from start_path until a .git directory is found."""
	current = start_path.resolve()
	for parent in [current, *current.parents]:
		if (parent / ".git").exists():
			return parent
	raise RuntimeError(f"No .git directory found above {start_path}")


def slugify(text: str, max_len: int = 40) -> str:
	slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
	return slug[:max_len].rstrip("-")


def branch_name_for_issue(issue_number: int, issue_title: str) -> str:
	return f"agent/issue-{issue_number}-{slugify(issue_title)}"


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
	result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
	if result.returncode != 0:
		raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
	return result


def create_branch(branch_name: str, git_root: Path):
	_run_git(["checkout", "-b", branch_name], cwd=git_root)


def commit_files(paths: list[Path], message: str, git_root: Path):
	rel_paths = [str(p.resolve().relative_to(git_root)) for p in paths]
	_run_git(["add", *rel_paths], cwd=git_root)
	_run_git(["commit", "-m", message], cwd=git_root)


def push_branch(branch_name: str, git_root: Path):
	_run_git(["push", "-u", "origin", branch_name], cwd=git_root)
