import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # add parent dir to path

from utils.llm_pick import pick_llm    # import the function to pick the LLM
from utils.etl_tools import ETLTools   # import the ETL tools class
from Models.schema import ETLAgentSchema  # import the schema for the agent
from langchain_core.messages import AIMessage,HumanMessage,ToolMessage  # import the necessary classes from langchain
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
from langchain_openai import ChatOpenAI

#----------------------------------------ETL Agent tools-----------------------------------------------#

@tool
def extract_load_tool(url:str,output_folder:str, format:str) -> str:
    """
    This tool will extract the data from the API(url) and loads it  into the desired location(output_folder)
    
    Args:
        url (str): The URL of the API to extract the data from.
        output_folder (str): The folder to load the extracted data into.
        format (str): The format in which to save the extracted data(csv, json, parquet).

    Returns:
        str: A message indicating the success or failure of the extraction and loading process.
    """
    etl_tools = ETLTools()
    return etl_tools.extract_load(url,output_folder,format)

@tool
def transform_load_tool(input_file_path:str, output_folder:str, output_format:str, user_question:str) -> str:
    """
    This tool will transform the extracted data and load it into the desired location(output_folder)
    
    Args:
        input_file_path (str): The path to the extracted data file.
        output_folder (str): The folder to load the transformed data into.
        output_format (str): The format in which to save the transformed data(csv, json, parquet).

    Returns:
        str: A message indicating the success or failure of the transformation and loading process.
    """
    etl_tools = ETLTools()

    top_3_rows = etl_tools.transform_load_context(input_file_path)

    llm = pick_llm("medium")                 # pick the LLM based on the level of the question
    prompt = f"""
    You are a python Data Analyst who uses Pandas to analyze data. You need to provide only the pandas code
    that will help to perform the right ETL operations as per user's requirements. Do not provide any explaination or comments, only the code should be provided.
    The code should be in a format that can be executed in a Python environment with pandas installed.
    Don't write anything else than pandas code. \n

    Create a pandas dataframe from the extracted data file {input_file_path} and thereafter perform the following operations:
    1. Load the data into a pandas dataframe.
    2. Transform the data as per the user's requirements.
    3. Save the transformed data into a file in the {output_folder} folder with the name {output_format}.

    Here's the user's requirements: {user_question}\n
    Here's the context of the data you will be analyzing: {top_3_rows}\n
    """

    pandas_code = llm.invoke(prompt).content
    results = etl_tools.execute_code(pandas_code)
    
    return f"The data is transformed and saved into the {output_folder} folder with the name {output_format}. Details: {results}"

# Toolkit for the ETL Agent
tools = [extract_load_tool, transform_load_tool]

llm = pick_llm("medium")                 # pick the LLM based on the level of the question
llm_bind = llm.bind_tools(tools)



#----------------------------------------Agent Graph Code-----------------------------------------------#

def llm_node(state: ETLAgentSchema) : 
    messages = state.messages

    prompt = f"""
        You are a python data analyst who has access to tools that can  extract and load,
        transform and load data from APIs into a pandas dataframe. You will be provided with 
        a user's question and you would need to perform the right ETL operations as per the user's 
        requirements. If the operation is performed then inform the user and end the conversation.

        Here's the chat history: {messages}\n
        """
    final_answer = llm_bind.invoke(prompt)

    state.messages = [final_answer]

    return state



def tool_node(state: ETLAgentSchema) : 
    """
    This node is responsible for invoking the appropriate tool based on the user's question and the tools available.
    """
    
    tools_results = []

    tools_by_name = {t.name: t for t in tools}

    tool_calls = state.messages[-1].tool_calls

    for tool_call in tool_calls:

        selected_tool = tools_by_name[tool_call['name']]
        observation = selected_tool.invoke(tool_call['args'])

        tools_results.append(ToolMessage(content=observation, tool_call_id=tool_call['id']))

    state.messages = tools_results

    return state


# Nodes and Edges
etl_analyst_graph = StateGraph(ETLAgentSchema)
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node)

etl_analyst_graph.add_edge(START, "llm_node")

def is_tool_call(state:ETLAgentSchema) : 
    tool_calls = state.messages[-1].tool_calls

    if tool_calls:
        return "tool_node"
    else:
        return "end"
etl_analyst_graph.add_conditional_edges(
    "llm_node",
    is_tool_call,
    {
        "tool_node" : "tool_node",
        "end" : END
    }
)

etl_analyst_graph.add_edge("tool_node", "llm_node")

etl_analyst = etl_analyst_graph.compile()

if __name__ == "__main__":
    

    from IPython.display import display, Image
    img = Image(etl_analyst.get_graph().draw_mermaid_png())
    with open("etl_analyst_graph.png", "wb") as f:
        f.write(img.data)


    # response = etl_analyst.invoke(
    #     {"messages" : [HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon/'. Save it to a csv file in the 'Data/extract' folder.")]}
    # )
    
    response = etl_analyst.invoke(
        {"messages": [HumanMessage (content = f"""
            I want to transform the data stored in the 'Data/extract/extracted_data.csv' 
            file into a pandas dataframe and save it to a pokemon.csv file in the 'Data/transform' folder.
            The transformation should filter the data to show charmander only.
            """)

        ]})
    
    print(response)