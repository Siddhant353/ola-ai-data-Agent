# OLA AI Data Agent

A multi-agent data assistant built with LangGraph. Ask a question in plain English; a router decides whether it needs a **SQL analyst** (query a Postgres database of ride-hailing data) or an **ETL analyst** (extract, transform and save CSV data), and the right agent handles it.

Built as a hands-on project to learn agentic AI patterns: routing, tool use, structured state, and defense-in-depth for LLM-generated SQL.

## How it works

![Top-level graph](data_agent_graph.png)

The top-level graph routes each question to one of two sub-agents.

| Agent | What it does | Graph |
|---|---|---|
| SQL analyst | Writes a SQL query against Postgres, checks it is safe, runs it, and summarises the result | ![SQL graph](sql_analyst_graph.png) |
| ETL analyst | Reads a CSV, applies a transformation, and writes the output file | ![ETL graph](etl_analyst_graph.png) |

Models are chosen per task through `utils/llm_pick.py` (low / medium / high tiers) and can be changed in `.env` without touching code.

## Safety: three layers for LLM-written SQL

An LLM that can write SQL can also write `DELETE` or `DROP`. This project does not trust any single check:

1. **Read-only database role.** The agent connects as a Postgres user with `SELECT`-only grants, `default_transaction_read_only = on` and a `statement_timeout`. Privileges are the hard barrier: even if every other layer failed, the database rejects writes.
2. **Deterministic guard** (`utils/sql_guard.py`). Allows exactly one `SELECT`/`WITH` statement and blocks write and DDL keywords, with no LLM involved.
3. **LLM judge.** A model reviews the generated query for safety before it runs.

Both the guard and the role are tested:

```bash
uv run python utils/check_sql_guard.py   # 5 allowed + 7 blocked queries
uv run python utils/check_readonly.py    # SELECT works; DELETE / CREATE / DROP are rejected by Postgres
```

## Data

Five synthetic tables, loaded from `Data/*.csv`: `users`, `rides`, `vehicles`, `payments`, `ratings`. All data is synthetic (e.g. `user1@example.com`); no real customer data is included.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/), plus a Postgres database and an OpenAI API key.

```bash
git clone https://github.com/Siddhant353/ola-ai-data-agent.git
cd ola-ai-data-agent
uv sync
cp .env.example .env      # Windows PowerShell: Copy-Item .env.example .env
```

Fill in `.env`:

- `OPENAI_API_KEY`
- `host`, `port`, `database`, `user`, `password`: an admin account, used only to load the data
- `readonly_user`, `readonly_password`: the restricted account the agent uses
- optional: `LLM_LOW`, `LLM_MEDIUM`, `LLM_HIGH` to override model names

Load the data, then create the read-only role (run as an admin; adjust names and password):

```sql
CREATE ROLE agent_readonly LOGIN PASSWORD 'choose-a-password';
GRANT USAGE ON SCHEMA public TO agent_readonly;
GRANT SELECT ON users, rides, vehicles, payments, ratings TO agent_readonly;
ALTER ROLE agent_readonly SET default_transaction_read_only = on;
ALTER ROLE agent_readonly SET statement_timeout = '10s';
```

```bash
uv run python utils/feed_db.py   # load the CSVs into Postgres
uv run python main.py            # start the agent
```

## Example questions

- "How many payments are in the database?"
- "Which city has the most active riders?"
- "Extract the CSV in Data/extract and save a filtered copy to Data/transform."

## Known limitations

- The ETL analyst runs model-generated Python, which is not sandboxed. Treat it as a demo and do not point it at sensitive files.
- The LLM judge is a probabilistic check; the read-only role and SQL guard are what actually enforce safety.
- Single-turn questions only; no conversation memory across runs.
- Built and tested on synthetic data with one Postgres setup.

## Tech

Python · LangGraph · LangChain · OpenAI · PostgreSQL · Pydantic · pandas · uv
