import asyncio

from agent_pipeline.agent import build_agent


async def main():
	print("Connecting to mcp-server and loading tools...")
	agent = await build_agent()
	print("Ready. Type a message (or 'exit' to quit).\n")

	messages = []
	while True:
		user_input = input("you> ").strip()
		if user_input.lower() in {"exit", "quit"}:
			break
		if not user_input:
			continue

		messages.append({"role": "user", "content": user_input})
		response = await agent.ainvoke({"messages": messages})

		# response["messages"] is the full running transcript, including any
		# intermediate tool calls — print just the final assistant reply.
		final_message = response["messages"][-1]
		print(f"\nagent> {final_message.content}\n")

		messages = response["messages"]


if __name__ == "__main__":
	asyncio.run(main())
