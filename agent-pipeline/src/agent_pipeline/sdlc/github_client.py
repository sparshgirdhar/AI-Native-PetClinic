"""
GitHub MCP connection for the SDLC pipeline.

Deliberately minimal: connects to the hosted GitHub MCP server, but never hands an
agent more tools than that specific stage needs — e.g. the Spec Agent only ever sees
get_issue, never create_pull_request, even though both exist on the server.
"""

import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

GITHUB_PAT = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")

# If the hosted endpoint returns 401/403 (some accounts don't have remote MCP access
# enabled yet), switch to running the server locally instead:
#   docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=<token> ghcr.io/github/github-mcp-server
# and point GITHUB_MCP_URL / transport at that local process instead — everything
# downstream of get_github_tools() stays the same either way.


def _client() -> MultiServerMCPClient:
	return MultiServerMCPClient(
		{
			"github": {
				"transport": "http",
				"url": GITHUB_MCP_URL,
				"headers": {"Authorization": f"Bearer {GITHUB_PAT}"},
			}
		}
	)


async def get_github_tools(allowed_tool_names: set[str]):
	"""
	Connects to GitHub MCP and returns only the tools named in allowed_tool_names.

	The server itself may expose far more (issues, pull_requests toolsets bring in
	things like add_issue_comment, merge_pull_request, etc.) — filtering here, in our
	own code, guarantees a given agent literally cannot see or call anything beyond
	what we explicitly hand it, regardless of what the server-side toolset loaded.
	"""
	if not GITHUB_PAT:
		raise RuntimeError(
			"GITHUB_PERSONAL_ACCESS_TOKEN is not set. Add it to agent-pipeline/.env "
			"(see .env.example)."
		)

	client = _client()
	all_tools = await client.get_tools()

	filtered = [t for t in all_tools if t.name in allowed_tool_names]

	found_names = {t.name for t in filtered}
	missing = allowed_tool_names - found_names
	if missing:
		available = sorted(t.name for t in all_tools)
		raise RuntimeError(
			f"Requested tool(s) not found on the GitHub MCP server: {missing}. "
			f"Available tools include: {available[:20]}{'...' if len(available) > 20 else ''}"
		)

	return filtered
