from ollama import chat
import json


def prepare_experiences(blocks: list[str], experience: str, model: str) -> dict:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))

    prompt = f"""
    You are a professional CV writer specializing in ATS optimization.

    ## Step 1 — Classify the role
    Read the job offer and identify:
    - Primary role type (e.g. Data Engineer, AI/ML Engineer, Backend Developer, Researcher etc.)
    - Top 5 technical requirements
    - Top 3 soft/process requirements

    ## Step 2 — Select bullets
    Each bullet in the candidate's experience has a "description" field. This field tells you:
    - What skill or domain the bullet represents
    - When you SHOULD select it (role types and keywords that make it relevant)
    - When you SHOULD NOT select it (anti-patterns and cases where it wastes a slot)

    Use the "description" field as your PRIMARY selection signal. Do not rely only on the
    surface text of the bullet — the description captures context the text alone does not.

    Rules:
    - Prioritize EXPERIENCE_1 (most recent role) — select up to 5 bullets
    - EXPERIENCE_2 — select up to 4 bullets, only if directly relevant
    - EXPERIENCE_3 — select at most 2 bullets, only if directly relevant; otherwise return empty list
    - EDUCATION_1 — select at most 3 bullets, only if they add something not covered by work experience
    - Quality over quantity. Do NOT pad to hit a number. An empty list is better than a weak bullet.
    - Select bullets that mirror the language and priorities of the job offer
    - After selecting, check: does the set cover each of the top 5 technical requirements?
      If a requirement is uncovered and a bullet exists whose description matches it, replace
      the weakest selected bullet with that one.

    ## Step 3 — Identify gaps
    List what relevant experience or skills the candidate is missing for this role.

    --- CANDIDATE EXPERIENCE ---
    {experience}

    --- JOB OFFER ---
    {job_blocks}

    Return ONLY valid JSON in this exact format:
    {{
      "role_classification": {{
        "role_type": "...",
        "top_technical_requirements": ["..."],
        "top_process_requirements": ["..."]
      }},
      "EXPERIENCE_1": {{"numbers": [], "reason": "..."}},
      "EXPERIENCE_2": {{"numbers": [], "reason": "..."}},
      "EXPERIENCE_3": {{"numbers": [], "reason": "..."}},
      "EDUCATION_1": {{"numbers": [], "reason": "..."}},
      "EXPERIENCE_MISSING": {{"description": "..."}}
    }}
    """

    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    fields = json.loads(response.message.content)

    return fields


def prepare_skills(blocks: list[str], skills: str, model: str) -> dict:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))

    prompt = f"""
    You are a professional CV writer specializing in ATS optimization.

    ## Step 1 — Classify the role
    Read the job offer and identify:
    - Primary role type (e.g. Data Engineer, AI/ML Engineer, Backend Developer)
    - Top 5 technical requirements

    ## Step 2 — Select skills
    Each skill in the candidate's list has a "description" field. This field tells you:
    - What the skill represents and when it is appropriate to select it
    - When to SKIP it (weak signal, not transferable, or redundant with another skill)
    - When two skills OVERLAP — in those cases, select only the one that better matches
      the job offer's terminology; do not select both unless both are explicitly required

    Use the "description" field as your PRIMARY selection signal.

    Rules:
    - Select between 6 and 9 skills maximum
    - Prioritize exact or near-exact matches to the job offer's required technical stack
    - Prefer hard technical skills over process or soft skills
    - Mirror the terminology used in the job offer where possible
    - Avoid redundant skill pairs (e.g. skill 5 vs 19+20, skill 7 vs 32, skill 6 vs 16)
      — the description field flags these; pick the one that fits best, not both

    ## Step 3 — Verify coverage
    After selecting, check: does the set cover each of the top 5 technical requirements?
    If a requirement is uncovered and a skill exists whose description matches it,
    replace the weakest selected skill with that one.

    --- CANDIDATE SKILLS ---
    {skills}

    --- JOB OFFER ---
    {job_blocks}

    Return ONLY valid JSON in this exact format:
    {{
      "role_classification": {{
        "role_type": "...",
        "top_technical_requirements": ["..."]
      }},
      "SKILL": {{"numbers": [], "reason": "..."}}
    }}
    """

    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    fields = json.loads(response.message.content)

    return fields


def prepare_summary(blocks: list[str], selected_bullets: str, model: str) -> dict:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))

    prompt = f"""
    You are writing a CV summary. You must follow the structure exactly.

    ## Hard constraints
    - Exactly 2 sentences. No more.
    - Maximum 45 words total.
    - Every claim must map to one of the provided bullets. If no bullet supports it, omit it.
    - No filler: no "passionate", "proven track record", "seasoned", "robust", "dynamic".
    - First person. Present tense for current role.

    ## Sentence structure (follow this exactly)
    - Built entirely from SELECTED BULLETS.
    - Explains candidate's experience (source of truth)
    Includes:
        - The single strongest technical capability (must appear explicitly in a bullet)
        - One concrete achievement or tool (must appear explicitly in a bullet)
    Sentence 1 — CURRENT ROLE + STRONGEST MATCH:
      "Engineer with experience in [skill from bullets most
      relevant to job offer]."

    Sentence 2 — VALUE TO THIS ROLE:
    - Connect to Sentence 1, but only use Sentence 1 material on the candidate's side.
    - Explains why the candidate is a good fit for this role.
      "At this position, I would bring [specific capability from bullets] to
      [specific need from job offer]."

    ## Inputs

    SELECTED BULLETS (only draw from these):
    {selected_bullets}

    JOB OFFER (extract role name, company, top needs):
    {job_blocks}

    Return ONLY valid JSON:
    {{
      "SUMMARY": {{
        "text": "...",
        "reason": "explain your reasoning behind writing the summary text"
      }}
    }}
    """

    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    fields = json.loads(response.message.content)

    return fields