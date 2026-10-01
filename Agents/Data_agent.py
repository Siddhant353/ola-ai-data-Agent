import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # add parent dir to path

from utils.llm_pick import pick_llm    # import the function to pick the LLM
from utils.etl_tools import ETLTools   # import the ETL tools class
from Models.schema import RouterSchema,DataAgentSchema  # import the schema for the agent
from langchain_core.messages import AIMessage,HumanMessage,ToolMessage  # import the necessary classes from langchain
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from Agents.ETL_analyst import etl_analyst
from Agents.SQL_analyst import sql_analyst

llm = pick_llm("medium")                 # pick the LLM based on the level of the question

llm_router = llm.with_structured_output(RouterSchema)

#----------------------------------------Data Agent graph-----------------------------------------------#

def router_node(state: DataAgentSchema) :
    messages = state.messages[-1].content

    route_response = llm_router.invoke(messages).model_dump()['answer']
    
    state.route_response = route_response

    return state


def etl_node(state: DataAgentSchema) :

    messages = state.messages[-1].content

    response = etl_analyst.invoke(
            {"messages": [HumanMessage (content = f"""
                {messages}
                """)
    
            ]}
        )

    state.messages = state.messages + [AIMessage(content=response["messages"][-1].content)]

    return state

def sql_node(state: DataAgentSchema) :

    messages = state.messages[-1].content

    input_schema = {
            "messages" : [],
            "user_question" : f"{messages}",
            "curated_ques" : "",
            "prompt_query_context" : "",
            "generated_sql_query" : "",
            "is_safe" : "NO",
            "comments" : "",
            "sql_query_execution_result" : "",
            "final_answer" : ""
        }

    response = sql_analyst.invoke(input_schema)
    
    state.messages = state.messages + [AIMessage(content=response["final_answer"])]

    return state

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    return "etl_node" if state.route_response == "etl" else "sql_node"

data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "etl_node": "etl_node",
        "sql_node": "sql_node",
    },
)

data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("sql_node", END)

data_agent = data_agent_graph.compile()


if __name__ == "__main__":

    from IPython.display import display, Image
    img = Image(data_agent.get_graph().draw_mermaid_png())
    with open("data_agent_graph.png", "wb") as f:
    
        f.write(img.data)
        response = data_agent.invoke(
            {"messages" : [HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon/'. Save it to a extracted.csv file in the 'Data/extract' folder and then I want the extracted data to be transformed in a way where only bulbasaur and charmander pokemons are shown and the data should be saved to a pokemon.csv file in the 'Data/transform' folder.")],
             "route_response" : ""   # This is the initial value for the route response
            }
        )

    print(response)