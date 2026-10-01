import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # add parent dir to path

from utils.llm_pick import pick_llm    # import the function to pick the LLM
from Models.schema import AgentSchema, JudgeSchema  # import the schema for the agent
from langchain_core.messages import HumanMessage  # import the necessary classes from langchain

llm = pick_llm("medium")                 # pick the LLM based on the level of the question
llm_judge = llm.with_structured_output(JudgeSchema)

SQL_Query = "SELECT * FROM users WHERE age > 30;"

prompt = f"""
Your are a SQL judge for data security. Your task is to determine whether the generated SQL query is safe to execute or not.
The SQL query should only be used for data retreaval and should not modify the databse, shuch as insert, update, or delete.
If the query is safe, return "YES", otherwise return "NO" and provide a comment. Additionally, provide comments explaining the reasoning behind your decision.
Here is the SQL query to be evaluated: {SQL_Query}
"""
response = llm_judge.invoke(prompt).model_dump()  # get the structured output as a dictionary
print(response)  # print the response