import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # add parent dir to path

from utils.llm_pick import pick_llm    # import the function to pick the LLM
from utils.database import DatabaseUtil # import the database utility class
from utils.sql_guard import check_select_only  # deterministic SELECT-only check
from Models.schema import AgentSchema, JudgeSchema  # import the schema for the agent
from langchain_core.messages import AIMessage,HumanMessage  # import the necessary classes from langchain
from langgraph.graph import StateGraph, START, END

#----------------------------------------AI Agent Code-----------------------------------------------#

def curate_ques(state: AgentSchema) -> AgentSchema:  # First node function to curate the question

    User_Question = state.user_question  # get the user question

    llm_obj = pick_llm("low")                 # pick the LLM based on the level of the question

    response = llm_obj.invoke(f"Curate the following question: {User_Question}")

    state.curated_ques = response.content             # update the state with the curated question
    state.messages = state.messages + [HumanMessage(content=f"{response}")]  # add the curated question to the messages

    return state

def prompt_query_context(state: AgentSchema) -> AgentSchema:  # Second node function to prompt the query context
    
    Curated_Question = state.curated_ques     # get the curated question

    conn_details = {
        "host": os.environ['host'],            # os.environ['host'] is the host name of the database server
        "port": int(os.environ['port']),       # int is used to convert the port number to integer
        "database": os.environ['database'],    # os.environ['database'] is the name of the database
        "user": os.environ['readonly_user'],    # os.environ['readonly_user'] is the username of the database
        "password": os.environ['readonly_password'],    # os.environ['readonly_password'] is the password of the database
    }

    obj = DatabaseUtil(conn_details)          # create a database utility object

    schema_info = obj.schema_details("public")  # fetch the schema information for the public schema

    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided with the user's original query 
    and the schema details of the database,  including the tables, columns, and data types, and sample data for each
    table so that you can understand the structure of the database and generate the SQL query. Unless user
    explicitly asks for specific number of rows, always limit the output to 10 rows. Note - Just generate
    the SQL query without any explaination or additional text because this query will be executed directly on the database.
    So, the output should be SQL ready to be executed without any modifications.

    User's original query: {Curated_Question}

    Database schema information: {schema_info}
    """
    state.prompt_query_context = prompt

    return state

# generate SQL query node
def generate_sql(state: AgentSchema) -> AgentSchema:  # Third node function to generate the SQL query
    prompt = state.prompt_query_context
    llm = pick_llm("medium")                 # pick the LLM based on the level of the question
    generated_sql_query = llm.invoke(prompt).content # generate the SQL query
    state.generated_sql_query = generated_sql_query
    return state



# is safe node 
def is_safe_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    allowed, reason = check_select_only(sql_query)   # layer 2: deterministic check, no LLM needed
    if not allowed:
        state.is_safe = "NO"
        state.comments = reason
        return state

    llm = pick_llm("medium")                 # pick the LLM based on the level of the question
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
    Your are a SQL judge for data security. Your task is to determine whether the generated SQL query is safe to execute or not.
    The SQL query should only be used for data retreaval and should not modify the databse, shuch as insert, update, or delete.
    If the query is safe, return "YES", otherwise return "NO" and provide a comment. Additionally, provide comments explaining the reasoning behind your decision.
    Here is the SQL query to be evaluated: {sql_query}"""

    response = llm_judge.invoke(prompt).model_dump()  # get the structured output as a dictionary
    state.is_safe = response["answer"]
    state.comments = response["comments"]
    
    return state


#canceled sql query node
def canceled_sql(state: AgentSchema) -> AgentSchema:

    comments = state.comments

    state.final_answer = f"The SQL query is canceled because {comments}"
    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")]  # add the final answer to the messages

    return state


# execute the sql query node
def execute_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    comm_details = {
        "host": os.environ['host'],            # os.environ['host'] is the host name of the database server
        "port": int(os.environ['port']),       # int is used to convert the port number to integer
        "database": os.environ['database'],    # os.environ['database'] is the name of the database
        "user": os.environ['readonly_user'],
        "password": os.environ['readonly_password'],
    }

    obj = DatabaseUtil(comm_details)          # create a database utility object

    execution_result = obj.execute_sql(sql_query)  # execute the sql query

    state.sql_query_execution_result = execution_result

    return state

#represent the final answer node
def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_execution_result
    curated_ques = state.curated_ques

    llm = pick_llm("low")                 # pick the LLM based on the level of the question

    prompt = f"""
    Your are an SQL Agent. Your task is to represent the final answer to the curated question {curated_ques} in a precise and clear manner.
    The final answer should be concise, clear, and directly address the user's query. Avoid including any SQL code or
    technical details in the final answer. The final answer should be in a format that can be easily understood by the user.\n
    Here is the curated question: {curated_ques}\n
    Here is the final answer: {execution_result}
    """

    llm_response = llm.invoke(prompt).content  # get the final answer from the LLM
    
    state.final_answer = llm_response
    state.messages = state.messages + [AIMessage(content=f"{llm_response}")]  # add the final answer to the messages

    return state


#-----------------------------------------------Graph Building Code-----------------------------------------------#

sql_agent_graph = StateGraph(AgentSchema)

# Nodes
sql_agent_graph.add_node(curate_ques, name="curate_ques")
sql_agent_graph.add_node(prompt_query_context, name="prompt_query_context")
sql_agent_graph.add_node(generate_sql, name="generate_sql")
sql_agent_graph.add_node(is_safe_sql, name="is_safe_sql")
sql_agent_graph.add_node(canceled_sql, name="canceled_sql")
sql_agent_graph.add_node(execute_sql, name="execute_sql")
sql_agent_graph.add_node(represent_final_answer, name="represent_final_answer")

# Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")

# Coditional Edge Function
def is_safe_sql_edge(state: AgentSchema) -> str:
    is_safe = state.is_safe

    if is_safe.lower() == "yes":
        return "execute_sql"
    else:
        return "canceled_sql"

sql_agent_graph.add_conditional_edges("is_safe_sql", is_safe_sql_edge,
                                        {
                                            "execute_sql" : "execute_sql",
                                            "canceled_sql" : "canceled_sql"
                                        })

# sql_agent_graph.add_edge("is_safe_sql", "execute_sql")
# sql_agent_graph.add_edge("is_safe_sql", "canceled_sql")

sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)

sql_analyst = sql_agent_graph.compile()

if __name__ == "__main__":
#-----------------------------------------------Graph Compilation Code-----------------------------------------------#
    

    from IPython.display import display, Image
    img = Image(sql_analyst.get_graph().draw_mermaid_png())
    with open("sql_analyst_graph.png", "wb") as f:
        f.write(img.data)

    input_schema = {
        "messages" : [],
        "user_question" : "What are the different types of payment methods we have in our database?",
        "curated_ques" : "",
        "prompt_query_context" : "",
        "generated_sql_query" : "",
        "is_safe" : "NO",
        "comments" : "",
        "sql_query_execution_result" : "",
        "final_answer" : ""
    }

    # Execute the Graph
    sql_analyst_response = sql_analyst.invoke(input_schema)
    print("message count:", len(sql_analyst_response['messages']))
    print(sql_analyst_response['messages'])   # Print the final output of the graph execution
    print("************************************************************************")

    print(sql_analyst_response['generated_sql_query'])   # Print the generated SQL query
    print("************************************************************************")

    print(sql_analyst_response['sql_query_execution_result'])   # Print the result of executing the SQL query
    print("************************************************************************")

    print(sql_analyst_response['prompt_query_context'])   # Print the prompt query context