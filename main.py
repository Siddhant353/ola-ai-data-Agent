from Agents.Data_agent import data_agent
from langchain_core.messages import HumanMessage

if __name__ == "__main__":

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("exit", "quit"):
            break

        if not user_input:
            continue

        response = data_agent.invoke(
            {"messages": [HumanMessage(content=user_input)],
             "route_response": ""   # This is the initial value for the route response
            }
        )

        print(response["messages"][-1].content)