"""
Entrypoint for the (currently partial) SDLC pipeline.

Usage:
    python -m agent_pipeline.sdlc.run_sdlc --owner sparshgirdhar --repo ai-native-petclinic --issue 3

v1 scope: fetch the issue, build a ChangeSpec, validate it against the change
budget, show it to the human, get approval. Code Agent / git ops / PR creation are
added in later stages, once this part is proven on a real issue.
"""

import argparse
import asyncio

from agent_pipeline.sdlc.spec_agent import build_change_spec


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


async def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--owner", required=True, help="GitHub repo owner/org")
	parser.add_argument("--repo", required=True, help="GitHub repo name")
	parser.add_argument("--issue", required=True, type=int, help="Issue number to implement")
	args = parser.parse_args()

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

	answer = input("Approve this plan? [y/N] ").strip().lower()
	if answer != "y":
		print("Not approved. Stopping.")
		return

	print("\nApproved. (Code Agent / PR creation not yet built — stopping here for now.)")


if __name__ == "__main__":
	asyncio.run(main())
