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
 
    prompt = f"""You are filling in a motivation letter template. Your ONLY task is to replace
each [SLOT] with the correct value extracted from the provided inputs.
Do NOT rewrite sentences. Do NOT add words outside the slots. Do NOT invent facts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SLOT DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[CURRENT_TITLE]
  Source: SELECTED BULLETS (infer from current role context)
  Rule: exact job title, e.g. "Lead AI Engineer" — do not invent or soften

[PRIMARY_SKILL]
  Source: SELECTED BULLETS
  Rule: the single technical skill that best matches the job's PRIMARY requirement
        — must be a concrete skill name, not a category (e.g. "vector database indexing pipelines",
        not "machine learning")

[PRIMARY_JOB_REQUIREMENT]
  Source: JOB OFFER
  Rule: copy or closely paraphrase the job's single most important technical requirement

[CURRENT_ROLE_ACHIEVEMENT]
  Source: SELECTED BULLETS — must come from the MOST RECENT role only
  Rule: one concrete achievement — include a specific tool, system, or scale detail from the bullet
        (e.g. "RAG pipelines serving hundreds of enterprise clients", not "AI solutions")

[SUPPORTING_SKILL]
  Source: SELECTED BULLETS — must come from a DIFFERENT bullet than [CURRENT_ROLE_ACHIEVEMENT]
  Rule: a distinct capability the job also requires — name it concretely

[JOB_REQUIREMENT_BRIDGE]
  Source: JOB OFFER
  Rule: quote or closely paraphrase a specific requirement from the job offer that
        [CURRENT_ROLE_ACHIEVEMENT] + [SUPPORTING_SKILL] together address

[COMPANY_SPECIFIC_FACT]
  Source: COMPANY RESEARCH only — never invent
  Rule: one concrete fact: a specific technical challenge, product area, or engineering
        decision — NOT generic praise, NOT revenue/size/founding year
        If no concrete fact exists in the research, use: "your focus on data-driven product features"

[CANDIDATE_CONTRIBUTION]
  Source: SELECTED BULLETS
  Rule: the specific skill from bullets most relevant to [COMPANY_SPECIFIC_FACT]
        — must be named concretely, not summarised generically

[FIT_SUMMARY]
  Source: derive only from [CURRENT_TITLE] + [PRIMARY_SKILL] — no new claims
  Rule: one short phrase, e.g. "my background in [PRIMARY_SKILL] as [CURRENT_TITLE]"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEMPLATE — fill every [SLOT], change nothing else
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPENING:
"I am a [CURRENT_TITLE] with hands-on experience in [PRIMARY_SKILL].
I am applying for the {job_title} role because [PRIMARY_JOB_REQUIREMENT] maps directly to my work."

EXPERIENCE:
"In my current role, I [CURRENT_ROLE_ACHIEVEMENT].
I also bring [SUPPORTING_SKILL], developed through [X].
Together, these directly address the role's requirement to [JOB_REQUIREMENT_BRIDGE]."

COMPANY:
"I am drawn to {company_name} because [COMPANY_SPECIFIC_FACT].
My experience in [CANDIDATE_CONTRIBUTION] would contribute directly to that goal."

CLOSING:
"[FIT_SUMMARY] makes me a strong candidate for this position.
I look forward to discussing how I can contribute to {company_name} and am available at your convenience."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SELECTED BULLETS (only source for candidate facts):
{bullets_text}

JOB OFFER:
{job_offer_text}

COMPANY RESEARCH (only source for [COMPANY_SPECIFIC_FACT]):
{company_research}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON, no preamble, no markdown fences.
Each "text" value must be the fully filled paragraph — no remaining [SLOT] tokens.
Each "reason" must name which bullet or research fact filled each slot.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "OPENING_PARAGRAPH":    {{"text": "...", "reason": "..."}},
  "EXPERIENCE_PARAGRAPH": {{"text": "...", "reason": "..."}},
  "COMPANY_PARAGRAPH":    {{"text": "...", "reason": "..."}},
  "CLOSING_PARAGRAPH":    {{"text": "...", "reason": "..."}}
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
        if language == "de":
            salutation = f"Guten Tag {recipient_name}"
        else:
            salutation = f"Dear {recipient_name}"
    else:
        if language == "de":
            salutation = f"Guten Tag {company_name} Team"
        else:
            salutation = f"Dear {company_name} Team"
 
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