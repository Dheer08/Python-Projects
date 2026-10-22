from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


from dotenv import load_dotenv
load_dotenv()

import asyncio

# You have to run the mathserver.py and weather_server.py before running this client code.
# Find it out

async def main():
    client = MultiServerMCPClient(
        {
            "math": {
                "command" : "python",
                "args" : ["mathserver.py"],
                "transport" : "stdio", # Path to the mathserver.py file
            },
            "weather": {
                "url" : "http://localhost:8000/mcp", # URL of the weather server
                "transport" : "streamable-http",
            }
        }
    )

    import os
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    tools = await client.get_tools()
    #print(tools)

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    agent = create_agent(
        model=model,
        tools=tools,
    )

    math_response = await agent.ainvoke(
        {"messages": [HumanMessage(content="What is (3+5)*2?")]}
    )
    print("math response:",math_response["messages"][-1].content)

    weather_response = await agent.ainvoke(
        {"messages": [HumanMessage(content="What is the weather in New York?")]}
    )
    print("weather response:",weather_response["messages"][-1].content)

asyncio.run(main())  # Run the main function

