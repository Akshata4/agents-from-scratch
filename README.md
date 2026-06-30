# Agents from Scratch

A hands-on learning project for building LLM agents using [PydanticAI](https://ai.pydantic.dev/). Contains two agents built progressively — a Wikipedia research agent and a personal finance auditor.

---

## Projects

### 1. Wikipedia Research Agent (`wiki_agent.py`)

A simple agent that researches any topic by searching and reading Wikipedia articles, then returns a structured comparison of two things.

**Tools**
- `search_wikipedia(query)` — finds matching article titles and snippets
- `get_article(title)` — fetches the full intro section of a specific article

**How it works**
The agent searches first, decides which article to read based on the results, reads it, and digs deeper if needed. The loop ends when the model decides it has enough information. Outputs a structured `ComparisonResult` with summaries, key differences, and sources read.

**Run**
```bash
uv run wiki_agent.py
# Enter: Python vs JavaScript
```

---

### 2. Personal Finance Auditor (`finance_agent.py` + `finance_app.py`)

An interactive finance assistant with a Streamlit UI. Upload your bank statement CSV once — then ask anything about your spending in plain English. The agent writes SQL against a local SQLite database to answer each question, keeping the full conversation history across turns.

#### Architecture

```
CSV upload
    │
    ├── LLM maps CSV columns to standard format (date, description, amount)
    ├── Amounts normalised (handles single amount or separate debit/credit columns)
    ├── LLM categorises each unique merchant into a fixed category
    └── Written to local SQLite (transactions.db)

User question (plain English)
    │
    └── Agent writes SQL → execute_query tool → SQLite → plain English answer
```

#### Categories

`Food` · `Transport` · `Shopping` · `Entertainment` · `Utilities` · `Rent` · `Health` · `Subscriptions` · `Other`

#### Tools

| Tool | What it does |
|---|---|
| `execute_query(sql)` | Runs any SELECT query — the agent writes the SQL itself (Text-to-SQL) |
| `find_recurring_charges()` | Detects subscriptions and bills that appear across multiple months |
| `set_budget(category, amount)` | Sets a monthly budget target for a category |
| `get_budget_status()` | Compares actual spending vs budgets for the latest month |
| `explain_merchant(name)` | Looks up an unknown merchant on Wikipedia |
| `convert_currency(amount, from, to)` | Converts amounts using live exchange rates (frankfurter.app) |

#### Read-only guardrail on the database

The `execute_query` tool enforces two layers of protection so the agent can never modify your data:
- **Layer 2 — sqlglot**: parses the SQL and rejects anything that isn't a SELECT
- **Layer 3 — SQLite read-only connection**: the database connection itself is opened in read-only mode, so writes are impossible at the OS level

#### Observability

Agent calls are instrumented with [Logfire](https://logfire.pydantic.dev/) — every run appears as a trace with nested spans showing each LLM call, tool call, latency, and token usage.

**Run**
```bash
uv run streamlit run finance_app.py
```

#### Example questions
- *How much did I spend on food last month?*
- *Compare food spending in April vs May*
- *What subscriptions am I paying for?*
- *What is this ADBE charge?*
- *Convert my total May spending to USD*
- *Am I over budget on transport this month?*

---

## Setup

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/Akshata4/agents-from-scratch
cd agents-from-scratch
uv sync
```

Create a `.env` file with your API keys:
```
GEMINI_API_KEY=your_gemini_key
LOGFIRE_TOKEN=your_logfire_token   # optional, for observability
```

Get a Gemini API key at [aistudio.google.com](https://aistudio.google.com).

---

---

## Stack

| Library | Purpose |
|---|---|
| [PydanticAI](https://ai.pydantic.dev/) | Agent framework |
| [Streamlit](https://streamlit.io/) | UI |
| [SQLite](https://www.sqlite.org/) | Local transaction store |
| [sqlglot](https://sqlglot.com/) | SQL parsing for read-only guardrail |
| [pandas](https://pandas.pydata.org/) | CSV normalisation |
| [Logfire](https://logfire.pydantic.dev/) | LLM observability |
| [httpx](https://www.python-httpx.org/) | HTTP calls (Wikipedia, currency API) |
