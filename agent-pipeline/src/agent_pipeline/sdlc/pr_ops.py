"""
Opens the pull request via GitHub MCP — the only place this pipeline touches
GitHub's write API for PRs. Branch/commit/push already happened locally via git_ops.
"""

import json

from agent_pipeline.sdlc.github_client import get_github_tools


def _unwrap_mcp_result(result):
	"""Same defensive unwrapping used in spec_agent.fetch_issue — MCP tool results
	often come back as a list of content blocks rather than a plain dict."""
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


async def create_pull_request(
	owner: str, repo: str, branch_name: str, base_branch: str, title: str, body: str
) -> dict:
	tools = await get_github_tools({"create_pull_request"})
	tool = tools[0]

	print(f"[debug] create_pull_request expects args: {tool.args}")

	result = await tool.ainvoke(
		{
			"owner": owner,
			"repo": repo,
			"title": title,
			"body": body,
			"head": branch_name,
			"base": base_branch,
		}
	)
	return _unwrap_mcp_result(result)
