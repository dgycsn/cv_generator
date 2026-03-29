import requests
from bs4 import BeautifulSoup

from ollama import chat
import json

model = "qwen2.5:32b"
#%%

# ── NOISE TAGS ────────────────────────────────────────────────────────────────
# These tags never contain job-relevant content.
# We strip them before parsing to avoid polluting the block list.

NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe"]


# ── BLOCK TAGS ────────────────────────────────────────────────────────────────
# HTML elements that typically represent a self-contained chunk of content.
# We use these as our splitting boundaries.

BLOCK_TAGS = ["section", "article", "div", "p", "li", "h1", "h2", "h3", "h4", "span"]


# ── LENGTH FILTER ─────────────────────────────────────────────────────────────
# Blocks shorter than MIN are usually labels or empty containers.
# Blocks longer than MAX are usually giant wrappers containing many sub-blocks
# (we want those sub-blocks individually, not the whole wrapper).

MIN_BLOCK_LEN = 30
MAX_BLOCK_LEN = 2000


def extract_blocks(url: str) -> list[str]:
    # ── 1. FETCH THE PAGE ─────────────────────────────────────────────────────
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(url, headers=headers, timeout=10)
    
    # response = requests.get(url, headers=HEADERS, timeout=10)
    # response.raise_for_status()  # raises HTTPError on 4xx / 5xx

    # ── 2. PARSE HTML ─────────────────────────────────────────────────────────
    soup = BeautifulSoup(response.text, "html.parser")

    # ── 3. STRIP NOISE ────────────────────────────────────────────────────────
    for tag in soup(NOISE_TAGS):
        tag.decompose()  # removes the tag and all its children from the tree

    # ── 4. EXTRACT BLOCK TEXT ─────────────────────────────────────────────────
    raw_blocks = []
    for tag in soup.find_all(BLOCK_TAGS):
        text = tag.get_text(separator=" ", strip=True)

        # Skip blocks that are too short (labels) or too long (wrappers)
        if MIN_BLOCK_LEN < len(text) < MAX_BLOCK_LEN:
            raw_blocks.append(text)

    # ── 5. DEDUPLICATE ────────────────────────────────────────────────────────
    # Nested tags often produce duplicate text (e.g. a <div> and its child <p>
    # with identical content). We preserve order while removing exact duplicates.
    seen = set()
    unique_blocks = []
    for block in raw_blocks:
        if block not in seen:
            seen.add(block)
            unique_blocks.append(block)

    return unique_blocks


#%%

def filter_relevant_blocks(blocks: list[str]) -> list[str]:
    numbered = "\n\n".join(f"[{i}] {b}" for i, b in enumerate(blocks))

    prompt = f"""You are filtering text blocks from a job listing webpage.
Return ONLY a JSON array of indices of relevant blocks.

Relevant: job title, responsibilities, requirements, salary, location,
contract type, company description, application instructions.
Ignore: cookie banners, nav menus, ads, unrelated jobs.

Blocks:
{numbered}

Respond with ONLY a JSON array, e.g.: [0, 2, 5, 7]"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    return [blocks[i] for i in json.loads(response.message.content)]



def filter_title_company(blocks: list[str]) -> list[str]:
    numbered = "\n\n".join(f"[{i}] {b}" for i, b in enumerate(blocks))

    prompt = f"""You are filtering text blocks from a job listing webpage.
Return ONLY a JSON array of job title and company name and what language the application documents should be in.
Remove "(f/m/d)" from job title if it is there
Possible languages are either English (en) or German (de)
Blocks:
{numbered}

Respond with ONLY a JSON array, e.g.: 
    {{job_title:'Senior Engineer AI', company_name:'My Corporation', language:'en'}}"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    response_json = json.loads(response.message.content)[0]
    return response_json["job_title"], response_json["company_name"], response_json["language"]

#%%

def extract_lang(data: dict, lang: str) -> str:
    cleaned = {
        section: {num: items[lang] for num, items in entries.items() if lang in items}
        for section, entries in data.items()
    }
    return json.dumps(cleaned, indent=2, ensure_ascii=False)


#%%

def prepare_cv_fields(blocks: list[str], experience: str) -> list[str]:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))
    
    prompt = f"""
    You are a professional CV writer. Given a numbered list of candidate's experience and a job offer, 
    select which experience best corresponds to the given job. 
    
    # Example json input for experience:
        {{ 
             "EXPERIENCE_1": {{ 
                 "1":"...",
                 "2":"...",
                 }} ,
             "EXPERIENCE_2": {{ 
                 ...}},
             "EDUCATION_1": {{ 
                 ...}}
         }} 
        
    In your output json, return a list of bulletpoint numbers for each experience.
    Aim for at least 5 experiences. If total number is less than required, add other experience
    that makes the candidate look good.
    Additionally, return your reasoning for choosing the relevant experience bulletpoints.
    Finally, return an extra field that describes what experience candidate is missing.
    
    # Example json output for experience:
        {{ 
             "EXPERIENCE_1": {{ 
                 "numbers":[1,2,3],
                 "reason":"..."
                 }},
             "EXPERIENCE_2": {{ 
                 ...}}, 
             "EDUCATION_1": {{ 
                 ...}},
             "EXPERIENCE_MISSING": {{
                 ...}}
         }} 
    
    --- CANDIDATE EXPERIENCE ---
    {experience}
    
    --- JOB OFFER ---
    {job_blocks}
    """
    
    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    fields = json.loads(response.message.content)

    return fields

#%%

if __name__ == "__main__":
    
    with open("experience.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    job_link = "https://www.galaxus.ch/de/joboffer/4140"
    blocks = extract_blocks(job_link)
    
    relevant_blocks = filter_relevant_blocks(blocks)
    
    job_title, company_name, language = filter_title_company(relevant_blocks)
    
    experience = extract_lang(data, "en")

    fields = prepare_cv_fields(relevant_blocks, experience)







