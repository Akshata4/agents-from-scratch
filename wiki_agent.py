import os

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

HEADERS = {"User-Agent": "WikiResearchAgent/1.0 (learning project; contact@example.com)"}


# --- Structured output shape ---

class ComparisonResult(BaseModel):
    topic_a: str
    topic_b: str
    summary_a: str                # what topic A is
    summary_b: str                # what topic B is
    key_differences: list[str]    # 3-5 concrete differences
    sources: list[str]            # Wikipedia article titles actually read


# --- Agent ---

agent = Agent(
    "google:gemini-3.1-flash-lite",
    output_type=ComparisonResult,
    system_prompt=(
        "You are a Wikipedia comparison assistant. The user gives you two topics to compare.\n\n"
        "Your workflow — follow this order strictly:\n"
        "1. Call search_wikipedia for topic A, then get_article on the best match\n"
        "2. Call search_wikipedia for topic B, then get_article on the best match\n"
        "3. If you need more detail on either, search and read again\n"
        "4. Return a structured ComparisonResult — fill every field\n\n"
        "Rules:\n"
        "- Always read at least one article per topic before answering\n"
        "- key_differences must have 3 to 5 items, each a single clear sentence\n"
        "- sources must list every article title you actually read"
    ),
)


# --- Tools ---

@agent.tool_plain
def search_wikipedia(query: str) -> str:
    """Search Wikipedia and return a list of matching article titles and snippets."""
    resp = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5,
        },
        headers=HEADERS,
        timeout=10,
    )
    if resp.status_code != 200:
        return f"Wikipedia search failed (HTTP {resp.status_code}): {resp.text[:200]}"
    hits = resp.json().get("query", {}).get("search", [])
    if not hits:
        return f"No Wikipedia articles found for: {query}"

    lines = []
    for h in hits:
        snippet = h["snippet"].replace('<span class="searchmatch">', "").replace("</span>", "")
        lines.append(f"- {h['title']}: {snippet}...")
    return "Found articles:\n" + "\n".join(lines)


@agent.tool_plain
def get_article(title: str) -> str:
    """Fetch the intro section of a Wikipedia article by its exact title."""
    resp = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "format": "json",
        },
        headers=HEADERS,
        timeout=10,
    )
    if resp.status_code != 200:
        return f"Could not fetch article '{title}' (HTTP {resp.status_code})."
    pages = resp.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    if "missing" in page:
        return f"Article '{title}' not found on Wikipedia."
    extract = page.get("extract", "No content available.")
    return f"[{page.get('title', title)}]\n\n{extract}"


# --- Helpers ---

def parse_input(raw: str) -> tuple[str, str]:
    """Parse 'X vs Y' or 'X and Y' into (X, Y). Raises ValueError if format is wrong."""
    for sep in (" vs ", " vs. ", " and ", " & "):
        if sep in raw.lower():
            idx = raw.lower().index(sep)
            a = raw[:idx].strip()
            b = raw[idx + len(sep):].strip()
            if a and b:
                return a, b
    raise ValueError("Please use the format: 'X vs Y'  (e.g. 'Python vs JavaScript')")


def print_reasoning(result) -> None:
    print("\n--- Agent Reasoning ---")
    for msg in result.all_messages():
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    print(f"\n>> {part.tool_name}({part.args})")
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    content = str(part.content)
                    preview = content[:300] + "..." if len(content) > 300 else content
                    print(f"   {preview}")
    print("\n--- End Reasoning ---\n")


def print_result(r: ComparisonResult) -> None:
    print("=" * 50)
    print(f"  {r.topic_a.upper()}  vs  {r.topic_b.upper()}")
    print("=" * 50)

    print(f"\n{r.topic_a}")
    print("-" * len(r.topic_a))
    print(r.summary_a)

    print(f"\n{r.topic_b}")
    print("-" * len(r.topic_b))
    print(r.summary_b)

    print("\nKey Differences")
    print("---------------")
    for i, diff in enumerate(r.key_differences, 1):
        print(f"{i}. {diff}")

    print("\nSources read")
    print("------------")
    for src in r.sources:
        print(f"  - {src}")
    print("=" * 50)


# --- Entry point ---

if __name__ == "__main__":
    raw = input("Compare two topics (e.g. 'Python vs JavaScript'): ").strip()

    try:
        topic_a, topic_b = parse_input(raw)
    except ValueError as e:
        print(e)
        raise SystemExit(1)

    print(f"\nComparing '{topic_a}' vs '{topic_b}' ...\n")

    result = agent.run_sync(f"Compare these two topics: {topic_a} vs {topic_b}")

    print_reasoning(result)
    print_result(result.output)
