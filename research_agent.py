import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
import ollama

# ── Config ────────────────────────────────────────────────────────────────────

MODEL = "qwen2.5:32b"
MAX_CANDIDATES = 15      # max search results to fetch
MIN_READABLE   = 5       # stop once this many pages yield actual content
MIN_PAGE_CHARS = 200     # pages below this char count are considered unreadable
MAX_CHARS      = 3000    # max chars extracted per page (keeps context small)
TIMEOUT        = 10      # seconds per HTTP request


# ── Step 1: Search ────────────────────────────────────────────────────────────

def search(company: str, query_suffix: str = "engineering culture values technology") -> list[dict]:
    query = f"{company} {query_suffix}"
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

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
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
        f"You are helping write a job application motivation letter. "
        f"Using only the source summaries below, extract exactly 4 bullet points about '{company}'. "
        f"Each bullet is one sentence. "
        f"Focus only on: mission, product focus, engineering culture, technology choices, "
        f"or specific challenges they are solving. "
        f"Do NOT include: employee count, revenue, founding year, ownership, stock price, "
        f"or generic praise. "
        f"If a fact would not strengthen a motivation letter, skip it. "
        f"Return only the 4 bullet points, one per line, with no preamble.\n\n"
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


# ── Shared scraping loop ──────────────────────────────────────────────────────

def _scrape_pages(company: str, query_suffix: str) -> list[str]:
    """
    Internal helper: search and scrape pages for a company query.
    Returns a list of per-page summaries.
    """
    print(f"[research] Searching for '{company}' ({query_suffix})...")
    results = search(company, query_suffix)

    summaries = []
    readable  = 0

    for result in results:
        if readable >= MIN_READABLE:
            break

        url   = result.get("href", "")
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

    return summaries


# ── Public API ────────────────────────────────────────────────────────────────

def research(company: str) -> str:
    """
    Run a full research pass on a company.
    Returns 4 bullet points about culture, mission, and technology —
    suitable for use in the COMPANY_PARAGRAPH of a motivation letter.
    """
    summaries = _scrape_pages(company, "engineering culture values technology")
    print(f"[research] Synthesizing brief from {len(summaries)} sources...")
    return synthesize(company, summaries)


def get_company_address(company: str) -> str:
    """
    Search for a company's official postal address.
    Returns a plain multiline string address, or "" if not found.
    """
    summaries = _scrape_pages(company, "headquarters address contact office")
    print(f"[research] Extracting address from {len(summaries)} sources...")
    return synthesize_address(company, summaries)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    company = "Digitec Galaxus"

    brief   = research(company)
    print("\n── Company Brief ─────────────────────────────────────────\n")
    print(brief)

    address = get_company_address(company)
    print("\n── Company Address ───────────────────────────────────────\n")
    print(address or "(not found)")
    print("\n──────────────────────────────────────────────────────────\n")