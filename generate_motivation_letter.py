from datetime import datetime
from fill_translation_placeholders import generate_document
from helpers import apply_defaults
from ollama import chat
import json
 
model = "qwen2.5:32b"
 
 
# ── Step 1: Extract recipient info from job page ───────────────────────────────
 
def extract_recipient(relevant_blocks: list[str], model: str) -> tuple[str, str]:
    """
    Extract the recipient name and title from the job listing blocks.
    Returns ("", "") if not found — these fields are optional in the template.
    """
    numbered = "\n\n".join(f"[{i}] {b}" for i, b in enumerate(relevant_blocks))
 
    prompt = f"""You are extracting contact information from a job listing.
Look for a named recruiter, HR contact, or hiring manager — someone the applicant should address the letter to.
 
Return ONLY a JSON object with exactly these two keys:
- "RECIPIENT_NAME": the full name of the contact person, or "" if not found
- "RECIPIENT_TITLE": their job title (e.g. "HR Manager", "Recruiter"), or "" if not found
 
Do NOT invent names. If no specific person is mentioned, return empty strings.
 
Blocks:
{numbered}
 
Respond with ONLY a JSON object, e.g.:
{{"RECIPIENT_NAME": "Anna Müller", "RECIPIENT_TITLE": "HR Manager"}}"""
 
    response = chat(model=model, messages=[{"role": "user", "content": prompt}])
    result = json.loads(response.message.content)
    return result.get("RECIPIENT_NAME", ""), result.get("RECIPIENT_TITLE", "")
 
 
# ── Step 2: Assess job fit before generating ──────────────────────────────────
 
def assess_fit(bullets_text: str, job_offer_text: str, model: str) -> dict:
    """
    Score how well the selected experience matches the job offer.
    Returns a dict with keys: score (0-10), strengths (list), gaps (list).
    Prints a warning if score is low.
    """
    prompt = f"""You are evaluating how well a candidate's experience matches a job offer.
 
CANDIDATE EXPERIENCE (selected bullets):
{bullets_text}
 
JOB OFFER:
{job_offer_text}
 
Assess the match and return ONLY a JSON object with exactly these keys:
- "score": integer from 0 to 10 (10 = perfect match)
- "strengths": list of up to 3 short strings — specific overlaps between bullets and job requirements
- "gaps": list of up to 3 short strings — job requirements not covered by any bullet
 
Return ONLY valid JSON, no preamble:
{{"score": 7, "strengths": ["..."], "gaps": ["..."]}}"""
 
    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    result = json.loads(response.message.content)
 
    score = result.get("score", 0)
    print(f"[CL] Fit score: {score}/10")
    if result.get("strengths"):
        print(f"[CL] Strengths: {', '.join(result['strengths'])}")
    if result.get("gaps"):
        print(f"[CL] Gaps:      {', '.join(result['gaps'])}")
    if score < 5:
        print("[CL] ⚠  Low fit score — consider reviewing your selected bullets or skipping this application.")
 
    return result
 
 
# ── Step 3: Generate letter body paragraphs ───────────────────────────────────
 
def generate_paragraphs(
    filled_experience: dict,
    relevant_blocks: list[str],
    company_name: str,
    job_title: str,
    company_research: str,
    model: str,
) -> dict[str, str]:
    """
    Uses the LLM to generate the four letter body paragraphs.
    Returns a dict with keys: OPENING_PARAGRAPH, EXPERIENCE_PARAGRAPH,
    COMPANY_PARAGRAPH, CLOSING_PARAGRAPH — values are the final text strings.
    """
    # Flatten experience bullets into a readable list
    bullets = [
        text
        for block_data in filled_experience.values()
        for text in block_data.values()
    ]
    bullets_text = "\n".join(f"- {b}" for b in bullets)
 
    # Flatten job page blocks into a readable job offer summary
    job_offer_text = "\n\n".join(relevant_blocks)
 
    prompt = f"""You are writing a motivation letter. You must follow all constraints exactly.
 
══════════════════════════════════════════════
EXAMPLE — FOR STRUCTURE REFERENCE ONLY
DO NOT use any names, companies, facts, or claims from this example in your output.
The example exists only to show the required sentence structure and JSON format.
══════════════════════════════════════════════
 
EXAMPLE INPUTS:
 
SELECTED BULLETS:
- Delivered end-to-end LLM and RAG solutions including document search and metadata extraction for enterprise clients
- Managed data processing pipelines with focus on data security, compliance, and MLOps governance
- Worked within CI/CD pipelines using Jenkins and GitHub Actions, adhering to ISO 27001 standards
- Developed backend services and APIs, delivering user stories from implementation through testing
 
JOB OFFER:
Title: Senior Data Engineer, Analytics and AI
Company: Digitec Galaxus AG
Top needs: production ML pipelines, scalable ETL/ELT data flows, Python and SQL expertise, CI/CD
 
COMPANY RESEARCH:
- Digitec Galaxus is Switzerland's largest e-commerce platform, using behavioral data to drive shop features
- Their team focuses on building clean data ecosystems to power ML and Generative AI applications
- They value simplicity and autonomy, avoiding unnecessary process in favor of direct impact
- They are expanding into new European markets and scaling their data infrastructure accordingly
 
EXAMPLE OUTPUT:
{{
  "OPENING_PARAGRAPH": {{
    "text": "I am a Lead AI Engineer with hands-on experience delivering production LLM and RAG pipelines for enterprise clients. I am applying for the Senior Data Engineer role because my background in productionizing ML workflows and managing compliant data pipelines maps directly to the team's core needs.",
    "reason": "Sentence 1 draws from bullet 1 (LLM/RAG, enterprise). Sentence 2 links bullet 3 (CI/CD, compliance) to the job's top need of production ML pipelines."
  }},
  "EXPERIENCE_PARAGRAPH": {{
    "text": "In my current role at Fabasoft, I deliver end-to-end RAG solutions and manage MLOps-compliant data pipelines serving hundreds of enterprise clients. Previously, I built backend APIs and worked within CI/CD pipelines adhering to ISO 27001, giving me a strong software engineering foundation. This combination of ML delivery and engineering discipline directly supports the role's requirement for robust, fault-tolerant production systems.",
    "reason": "Sentence 1 uses bullets 1 and 3 (RAG, MLOps). Sentence 2 uses bullet 4 (APIs, CI/CD). Sentence 3 bridges to the job's 'Systems Integrity' requirement."
  }},
  "COMPANY_PARAGRAPH": {{
    "text": "I am drawn to Digitec Galaxus because your team is building a clean behavioral data ecosystem to power ML and Generative AI features at scale across European markets. I believe my experience operationalizing LLM solutions and managing data pipelines under governance constraints would contribute directly to that infrastructure.",
    "reason": "Sentence 1 uses research facts 1 and 4 (behavioral data ecosystem, European expansion). Sentence 2 links bullet 1 (LLM delivery) and bullet 3 (governance) to the company's stated data platform focus."
  }},
  "CLOSING_PARAGRAPH": {{
    "text": "I am confident that my background in ML engineering and data pipeline delivery makes me a strong candidate for this role. I would welcome the opportunity to discuss how I can contribute to Digitec Galaxus and am available at your convenience.",
    "reason": "No new claims introduced. Company name taken from job offer. Skill summary derived from opening paragraph only."
  }}
}}
 
══════════════════════════════════════════════
END OF EXAMPLE — YOUR TASK STARTS HERE
══════════════════════════════════════════════
 
## Hard constraints — apply to ALL paragraphs
- No filler words: no "passionate", "excited", "proven track record", "dynamic", "robust",
  "thrilled", "seasoned", "eager", "delighted", "pleasure", "leverage", "synergy", "hard-working"
- Every factual claim must map to a provided bullet. If no bullet supports it, omit it.
- COMPANY_PARAGRAPH must only use facts from COMPANY RESEARCH. Do not invent company facts.
- COMPANY_PARAGRAPH must not mention: employee count, revenue, founding year, stock price,
  or generic praise. Only mission, product focus, or specific engineering challenges.
- First person. Present tense for current role, past tense for previous roles.
- Do not copy any sentence, name, company, or fact from the example above.
 
## Per-paragraph constraints
 
OPENING_PARAGRAPH:
- Exactly 2 sentences. Maximum 50 words.
- Sentence 1: who you are + strongest skill match to the job
- Sentence 2: why this role + specific overlap with the job's top need
 
EXPERIENCE_PARAGRAPH:
- Exactly 3 sentences. Maximum 80 words.
- Sentence 1: current role + concrete achievement with specific detail
- Sentence 2: relevant past experience that supports the job's needs
- Sentence 3: bridge between your skill cluster and a specific job requirement
 
COMPANY_PARAGRAPH:
- Exactly 2 sentences. Maximum 50 words.
- Sentence 1: one specific fact from COMPANY RESEARCH explaining why this company
- Sentence 2: your specific skill from bullets mapped to their specific need
 
CLOSING_PARAGRAPH:
- Exactly 2 sentences. Maximum 40 words.
- No new claims. End with a call to action that names the company.
 
## Inputs
 
SELECTED BULLETS (draw facts only from these):
{bullets_text}
 
JOB OFFER (extract: position title, company name, top needs):
{job_offer_text}
 
COMPANY NAME: {company_name}
 
COMPANY RESEARCH (use only these facts in COMPANY_PARAGRAPH):
{company_research}
 
Return ONLY valid JSON with no preamble and no markdown fences:
{{
  "OPENING_PARAGRAPH": {{
    "text": "...",
    "reason": "..."
  }},
  "EXPERIENCE_PARAGRAPH": {{
    "text": "...",
    "reason": "..."
  }},
  "COMPANY_PARAGRAPH": {{
    "text": "...",
    "reason": "..."
  }},
  "CLOSING_PARAGRAPH": {{
    "text": "...",
    "reason": "..."
  }}
}}"""
 
    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    raw_fields = json.loads(response.message.content)
 
    # Run hallucination validation before stripping reasons
    warnings = validate_paragraphs(raw_fields, bullets_text, model)
    if warnings:
        print("[CL] ⚠  Validation warnings (possible hallucinations):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("[CL] ✓ Validation passed — all claims traceable to bullets.")
 
    # Strip the "reason" field — only keep the final text
    return {key: value["text"] for key, value in raw_fields.items()}
 
 
# ── Step 3b: Validate paragraphs against source bullets ──────────────────────
 
def validate_paragraphs(paragraphs_with_reasons: dict, bullets_text: str, model: str) -> list[str]:
    """
    Cross-checks each generated paragraph against the source bullets.
    Returns a list of warning strings. Empty list means all claims are traceable.
    """
    prompt = f"""You are a fact-checker for a job application letter.
 
APPROVED FACTS (the only permitted source of claims):
{bullets_text}
 
PARAGRAPHS TO CHECK (each has a "text" and a "reason" justifying its claims):
{json.dumps(paragraphs_with_reasons, indent=2)}
 
For each paragraph, check whether every factual claim in "text" is supported
by a bullet in APPROVED FACTS. The "reason" field explains the intended mapping —
use it as a hint, but verify against the bullets directly.
 
Flag any claim that:
- References experience, sectors, or technologies not present in any bullet
- Invents or embellishes a detail beyond what the bullet states
- Cannot be traced to a specific bullet even loosely
 
Return ONLY a JSON array of warning strings. Return [] if everything checks out.
Example: ["EXPERIENCE_PARAGRAPH claims 'public sector work' but no bullet supports this."]
Return ONLY a JSON array, no preamble."""
 
    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    result = json.loads(response.message.content)
    # Normalise: model might return a dict with a "warnings" key
    if isinstance(result, dict):
        return result.get("warnings", [])
    return result if isinstance(result, list) else []


# ── Main function ─────────────────────────────────────────────────────────────
 
def generate_motivation_letter(
    relevant_blocks: list[str],
    selected_experience: dict,
    experience_data: dict,
    company_name: str,
    job_title: str,
    company_research: str,
    company_address: str,
    language: str,
    filename: str,
    cl_template: str,
    config_folder: str,
    output_folder: str,
    model: str = "qwen2.5:32b",
) -> dict:
    """
    Full motivation letter pipeline:
      1. Extract recipient info from job page
      2. Assess job fit and warn if score is low
      3. Generate the four letter body paragraphs (with validation)
      4. Fill the template and write the output .odt
 
    Fields handled automatically by generate_document (from translations JSON):
      FULL_NAME, CITY, DATE, PHONE, EMAIL, LINKEDIN, WEBSITE, CLOSING_PHRASE
 
    Fields handled here:
      RECIPIENT_NAME, RECIPIENT_TITLE, COMPANY_NAME, COMPANY_ADDRESS,
      POSITION_TITLE, SALUTATION,
      OPENING_PARAGRAPH, EXPERIENCE_PARAGRAPH, COMPANY_PARAGRAPH, CLOSING_PARAGRAPH
    """
 
    # Step 1: Flatten experience with language fallback
    filled_experience = apply_defaults(selected_experience, experience_data, language="en")
 
    # Step 2: Extract recipient from job page
    recipient_name, recipient_title = extract_recipient(relevant_blocks, model)
 
    # Step 3: Flatten bullets for fit check
    bullets = [
        text
        for block_data in filled_experience.values()
        for text in block_data.values()
    ]
    bullets_text = "\n".join(f"- {b}" for b in bullets)
    job_offer_text = "\n\n".join(relevant_blocks)
 
    # Step 4: Assess fit — warns if score is low, but does not block generation
    print("[CL] Assessing job fit...")
    assess_fit(bullets_text, job_offer_text, model)
 
    # Step 5: Generate letter body (includes validation internally)
    paragraphs = generate_paragraphs(
        filled_experience=filled_experience,
        relevant_blocks=relevant_blocks,
        company_name=company_name,
        job_title=job_title,
        company_research=company_research,
        model=model,
    )
 
    # Step 6: Build salutation — use recipient name if found, fall back to company team
    # Note: salutation string must NOT end with a comma if the template already has one.
    # Check your ODT template: if SALUTATION placeholder is followed by a comma, remove
    # the trailing comma here. Currently we include it so the template should have none.
    if recipient_name:
        salutation = f"Dear {recipient_name},"
    else:
        salutation = f"Dear {company_name} Team,"
 
    # Step 7: Assemble all dynamic placeholders
    dynamic_fields = {
        "RECIPIENT_NAME":    recipient_name,
        "RECIPIENT_TITLE":   recipient_title,
        "COMPANY_NAME":      company_name,
        "COMPANY_ADDRESS":   company_address,
        "POSITION_TITLE":    job_title,
        "SALUTATION":        salutation,
        "DATE":              datetime.today().strftime('%d-%m-%Y'),
        **paragraphs,
    }
 
    # Step 8: Fill template (generate_document injects translation fields on top)
    generate_document(filename, config_folder, cl_template, output_folder, language, dynamic_fields)
    
    return dynamic_fields

 
 
#%%
# ── Standalone entry point ────────────────────────────────────────────────────
 
if __name__ == "__main__":
    from extract_job_page import extract_blocks, filter_relevant_blocks, filter_title_company
    from research_agent import research_full
 
    # ── Config ────────────────────────────────────────────────────────────────
    job_link      = "https://www.galaxus.ch/de/joboffer/4176"
    filename      = "CL_Alp_Yuecesan"
    cl_template   = "./templates/motivation_letter_template.odt"
    config_folder = "./configs/"
    output_folder = "./outputs/"
    language      = "en"
    model         = "qwen2.5:32b"
 
    with open(config_folder + "experience.json", "r", encoding="utf-8") as f:
        experience_data = json.load(f)
 
    # ── Step 1: Extract job page ──────────────────────────────────────────────
    if "blocks" not in dir():
        print("[CL] Extracting job page blocks...")
        blocks = extract_blocks(job_link)
 
    if "relevant_blocks" not in dir():
        print("[CL] Filtering relevant blocks...")
        relevant_blocks = filter_relevant_blocks(blocks, model)
 
    if "job_title" not in dir():
        print("[CL] Extracting title & company...")
        job_title, company_name, _ = filter_title_company(relevant_blocks, model)
        print(f"[CL] Job: {job_title} @ {company_name} ({language})")
 
    # ── Step 2: Research (single pass for both brief and address) ─────────────
    if "company_research" not in dir() or "company_address" not in dir():
        print("[CL] Researching company...")
        company_research, company_address = research_full(company_name)
 
    # ── Step 3: Experience ────────────────────────────────────────────────────
    # NOTE: Replace the empty dict below with your actual selected_experience.
    # Passing {} here uses ALL experience bullets with no selection — which
    # floods the prompt and weakens relevance. Always select before this step.
    if "selected_experience" not in dir():
        selected_experience = apply_defaults({}, experience_data, language=language)
 
    # ── Step 4: Generate letter ───────────────────────────────────────────────
    print("[CL] Generating motivation letter...")
    dynamic_fields = generate_motivation_letter(
        relevant_blocks     = relevant_blocks,
        selected_experience = selected_experience,
        experience_data     = experience_data,
        company_name        = company_name,
        job_title           = job_title,
        company_research    = company_research,
        company_address     = company_address,
        language            = language,
        filename            = filename,
        cl_template         = cl_template,
        config_folder       = config_folder,
        output_folder       = output_folder,
        model               = model,
    )
    print(f"[CL] Done → {output_folder}{filename}_{language}.odt")