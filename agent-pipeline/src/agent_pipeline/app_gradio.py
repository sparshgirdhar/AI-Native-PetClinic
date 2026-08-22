import asyncio

import gradio as gr

from agent_pipeline.agent import build_agent

_agent = None
_agent_lock = asyncio.Lock()


async def get_agent():
	global _agent
	async with _agent_lock:
		if _agent is None:
			_agent = await build_agent()
	return _agent


async def respond(message, history):
	agent = await get_agent()

	# Gradio's `history` is a list of {"role", "content"} dicts already —
	# reuse it directly as the running message transcript.
	messages = history + [{"role": "user", "content": message}]
	response = await agent.ainvoke({"messages": messages})
	return response["messages"][-1].content


demo = gr.ChatInterface(
	fn=respond,
	title="PetClinic AI Assistant",
	description="Ask about owners, pets, visits, or vets — e.g. "
	"\"Schedule a visit for Sparsh Girdhar's dog Coco on November 20th\"",
)

if __name__ == "__main__":
	demo.launch()