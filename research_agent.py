import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
import ollama
 
# ── Config ────────────────────────────────────────────────────────────────────
 
MODEL = "qwen2.5:32b"       # any model you have pulled in Ollama
MAX_CANDIDATES = 15      # max search results to fetch (upper bound of pages to try)
MIN_READABLE = 5         # stop once this many pages yield actual content
MIN_PAGE_CHARS = 200     # pages with less text than this are considered unreadable
MAX_CHARS = 3000         # max chars extracted per page (keeps context small)
TIMEOUT = 10             # seconds per HTTP request
 
 
# ── Step 1: Search ────────────────────────────────────────────────────────────
 
def search(company: str) -> list[dict]:
    query = f"{company} engineering culture values technology"
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=MAX_CANDIDATES))
    return results
 
 
# ── Step 2: Scrape ────────────────────────────────────────────────────────────
 
def scrape(url: str) -> str:
    """Fetch a URL and return cleaned visible text, or empty string if unreadable."""
    try:
        response = httpx.get(
            url,
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (research-bot/1.0)"},
        )
        response.raise_for_status()
    except Exception:
        return ""
 
    soup = BeautifulSoup(response.text, "html.parser")
 
    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
 
    text = soup.get_text(separator=" ", strip=True)
 
    # Collapse whitespace and truncate
    text = " ".join(text.split())
    return text[:MAX_CHARS]
 
 
# ── Step 3: Summarize each page ───────────────────────────────────────────────
 
def summarize_page(company: str, page_text: str, source_title: str) -> str:
    """Ask Ollama to summarize a single page about the company."""
    prompt = (
        f"You are a research assistant. Based on the following webpage content, "
        f"extract only the facts relevant to the company '{company}'. "
        f"Write 2-3 concise sentences. If the page is not about this company, say 'Not relevant'.\n\n"
        f"Source: {source_title}\n"
        f"Content: {page_text}"
    )
 
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()
 
 
# ── Step 4: Synthesize final brief ────────────────────────────────────────────
 
def synthesize(company: str, summaries: list[str]) -> str:
    combined = "\n\n".join(
        f"Source {i+1}: {s}" for i, s in enumerate(summaries) if "Not relevant" not in s
    )

    if not combined:
        return f"Could not find sufficient information about '{company}'."

    prompt = (
        f"You are helping write a job application motivation letter. "
        f"Using only the source summaries below, extract exactly 4 bullet points about '{company}'. "
        f"Each bullet is one sentence. Focus only on: mission, product focus, engineering culture, "
        f"technology choices, or specific challenges they are solving. "
        f"Do NOT include: employee count, revenue, founding year, ownership, stock price, or generic praise. "
        f"If a fact is not useful for a motivation letter, skip it. "
        f"Return only the 4 bullet points, nothing else.\n\n"
        f"{combined}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()
 
 
# ── Main: research() ──────────────────────────────────────────────────────────
 
def research(company: str) -> str:
    """
    Run a full research pass on a company.
    Tries up to MAX_CANDIDATES pages, stopping once MIN_READABLE yield actual content.
    Returns a brief string summary suitable for use in a larger workflow.
    """
    print(f"[research] Searching for '{company}'...")
    results = search(company)
 
    summaries = []
    readable = 0
 
    for result in results:
        if readable >= MIN_READABLE:
            break
 
        url = result.get("href", "")
        title = result.get("title", url)
        print(f"[research] Scraping: {title[:60]}")
        page_text = scrape(url)
 
        if len(page_text) < MIN_PAGE_CHARS:
            print(f"[research] Skipped (unreadable): {title[:60]}")
            continue
 
        readable += 1
        print(f"[research] Readable {readable}/{MIN_READABLE}: {title[:60]}")
        summary = summarize_page(company, page_text, title)
        summaries.append(summary)
 
    print(f"[research] Synthesizing from {len(summaries)} sources...")
    brief = synthesize(company, summaries)
    return brief
 
 
# ── CLI entry point ───────────────────────────────────────────────────────────
 
if __name__ == "__main__":
 
    company = "Digitec Galaxus"
    brief = research(company)
    print("\n── Company Brief ─────────────────────────────────────────\n")
    print(brief)
    print("\n──────────────────────────────────────────────────────────\n")