import httpx
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from ddgs import DDGS
import ollama

# ── Config ────────────────────────────────────────────────────────────────────

MODEL          = "qwen2.5:32b"
MAX_CANDIDATES = 15      # max search results to fetch
MIN_READABLE   = 5       # stop once this many pages yield actual content
MIN_PAGE_CHARS = 200     # pages below this char count are considered unreadable
MAX_CHARS      = 3000    # max chars extracted per page (keeps context small)
TIMEOUT        = 10      # seconds per HTTP request
MAX_RETRIES    = 2       # retry attempts on transient timeouts


# ── Step 1: Search ────────────────────────────────────────────────────────────

def search(company: str, query_suffix: str) -> list[dict]:
    query = f"{company} {query_suffix}"
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=MAX_CANDIDATES))
    return results


# ── Step 2: Scrape ────────────────────────────────────────────────────────────

def scrape(url: str) -> str:
    """
    Fetch a URL and return cleaned visible text, or empty string if unreadable.
    Prefers <main> or <article> content to avoid nav/hero boilerplate.
    Retries on timeout up to MAX_RETRIES times.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = httpx.get(
                url,
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (research-bot/1.0)"},
            )
            response.raise_for_status()
            break
        except httpx.TimeoutException:
            if attempt < MAX_RETRIES:
                continue
            return ""
        except Exception:
            return ""

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Prefer semantic content containers over full body
    content_node = soup.find("main") or soup.find("article") or soup
    text = content_node.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    return text[:MAX_CHARS]


# ── Step 3: Summarize each page ───────────────────────────────────────────────

def summarize_page(company: str, page_text: str, source_title: str) -> str:
    """Summarize a single scraped page, keeping only facts relevant to the company."""
    prompt = (
        f"You are a research assistant. Based on the following webpage content, "
        f"extract only the facts relevant to the company '{company}'. "
        f"Write 2-3 concise sentences. "
        f"If the page is not about this company, reply with exactly 'Not relevant'.\n\n"
        f"Source: {source_title}\n"
        f"Content: {page_text}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()


# ── Step 4a: Synthesize culture/tech brief ────────────────────────────────────

def synthesize(company: str, summaries: list[str]) -> str:
    """
    Produce 4 bullet points about the company's mission, culture, and technology.
    Suitable for use in the COMPANY_PARAGRAPH of a motivation letter.
    """
    combined = "\n\n".join(
        f"Source {i+1}: {s}"
        for i, s in enumerate(summaries)
        if "Not relevant" not in s
    )

    if not combined:
        return f"Could not find sufficient information about '{company}'."

    prompt = (
        f"You are helping write a job application motivation letter for a technical role at '{company}'.\n"
        f"Using only the source summaries below, extract exactly 4 bullet points.\n"
        f"Each bullet must be one concrete, specific sentence a candidate could directly reference in a letter.\n\n"
        f"Priority order — fill as many as the sources support:\n"
        f"1. A specific technical problem or product challenge the company is actively solving\n"
        f"2. A concrete technology choice, stack decision, or engineering practice they use\n"
        f"3. A specific product area, user-facing feature, or data challenge they work on\n"
        f"4. A stated engineering value or working principle (only if concrete, not generic praise)\n\n"
        f"STRICT rules:\n"
        f"- Do NOT include: employee count, revenue, founding year, ownership, stock price\n"
        f"- Do NOT include vague praise: 'innovative', 'leading', 'passionate', 'best-in-class'\n"
        f"- If a fact cannot be cited in one sentence of a motivation letter, skip it\n"
        f"- If fewer than 4 concrete facts exist in the sources, return fewer bullets — do not pad\n\n"
        f"Return only the bullet points, one per line, no preamble, no bullet symbols.\n\n"
        f"{combined}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()


# ── Step 4b: Extract company address ─────────────────────────────────────────

def synthesize_address(company: str, summaries: list[str]) -> str:
    """
    Extract the company's official postal address from scraped page summaries.
    Returns a plain string address, or "" if not found.
    """
    combined = "\n\n".join(
        f"Source {i+1}: {s}"
        for i, s in enumerate(summaries)
        if "Not relevant" not in s
    )

    if not combined:
        return ""

    prompt = (
        f"You are extracting a mailing address for a formal letter. "
        f"From the source summaries below, find the official postal address of '{company}'. "
        f"Return only the address as plain text in this format:\n"
        f"Street and number\nCity and postal code\nCountry\n\n"
        f"If no address is found, return exactly an empty string.\n\n"
        f"{combined}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    result = response["message"]["content"].strip()
    return "" if result.lower() in ("", "none", "not found") else result


# ── Shared scraping loop (parallel) ──────────────────────────────────────────

def _scrape_pages(company: str, query_suffix: str) -> list[str]:
    """
    Search for pages, scrape them in parallel, then summarize sequentially.
    Returns a list of per-page summaries.
    """
    print(f"[research] Searching for '{company}' ({query_suffix})...")
    results = search(company, query_suffix)

    # Filter to URLs that are worth fetching
    candidates = [r for r in results if r.get("href")][:MAX_CANDIDATES]

    # Scrape all candidates in parallel
    print(f"[research] Scraping {len(candidates)} pages in parallel...")
    scraped: dict[str, tuple[str, str]] = {}  # url -> (title, text)

    def fetch(result: dict) -> tuple[str, str, str]:
        url   = result["href"]
        title = result.get("title", url)
        text  = scrape(url)
        return url, title, text

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch, r): r for r in candidates}
        for future in as_completed(futures):
            url, title, text = future.result()
            if len(text) >= MIN_PAGE_CHARS:
                scraped[url] = (title, text)
                print(f"[research] ✓ Readable: {title[:60]}")
            else:
                print(f"[research] ✗ Skipped:  {title[:60]}")

    # Summarize readable pages (sequential — LLM calls are stateful)
    summaries = []
    for url, (title, text) in list(scraped.items())[:MIN_READABLE]:
        summary = summarize_page(company, text, title)
        summaries.append(summary)

    return summaries


# ── Public API ────────────────────────────────────────────────────────────────

def research_full(company: str) -> tuple[str, str]:
    """
    Single-pass research: scrapes once and derives both the culture/tech brief
    and the postal address from the same set of pages.

    Returns:
        brief   — 4 bullet points about culture, mission, technology
        address — plain multiline postal address string, or ""

    Use this instead of calling research() and get_company_address() separately,
    which would double the scraping cost.
    """
    # Combined query hits both culture/tech and address signals in one search
    summaries = _scrape_pages(company, "engineering culture values technology headquarters address contact")

    print(f"[research] Synthesizing brief from {len(summaries)} sources...")
    brief = synthesize(company, summaries)

    print(f"[research] Extracting address from {len(summaries)} sources...")
    address = synthesize_address(company, summaries)

    return brief, address


# ── Legacy single-purpose functions (kept for backward compatibility) ──────────

def research(company: str) -> str:
    """
    Deprecated: use research_full() to avoid a double scraping pass.
    Run a full research pass on a company.
    Returns 4 bullet points about culture, mission, and technology.
    """
    summaries = _scrape_pages(company, "engineering culture values technology")
    print(f"[research] Synthesizing brief from {len(summaries)} sources...")
    return synthesize(company, summaries)


def get_company_address(company: str) -> str:
    """
    Deprecated: use research_full() to avoid a double scraping pass.
    Search for a company's official postal address.
    Returns a plain multiline string address, or "" if not found.
    """
    summaries = _scrape_pages(company, "headquarters address contact office")
    print(f"[research] Extracting address from {len(summaries)} sources...")
    return synthesize_address(company, summaries)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    company = "Digitec Galaxus"

    brief, address = research_full(company)

    print("\n── Company Brief ─────────────────────────────────────────\n")
    print(brief)

    print("\n── Company Address ───────────────────────────────────────\n")
    print(address or "(not found)")
    print("\n──────────────────────────────────────────────────────────\n")