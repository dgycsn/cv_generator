from ollama import chat
import json


def prepare_experiences(blocks: list[str], experience: str, model: str) -> list[str]:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))
    
    prompt = f"""
    You are a professional CV writer specializing in ATS optimization.

    ## Step 1 — Classify the role
    Read the job offer and identify:
    - Primary role type (e.g. Data Engineer, AI/ML Engineer, Backend Developer, Researcher etc.)
    - Top 5 technical requirements
    - Top 3 soft/process requirements
    
    ## Step 2 — Select bullets
    Given the candidate's experience and the role classification above, select the most relevant bullet points per experience block.
    
    Rules:
    - Prioritize EXPERIENCE_1 (most recent role) — select up to 5 bullets
    - EXPERIENCE_2 — select up to 4 bullets, only if directly relevant
    - EXPERIENCE_3 — select at most 2 bullets, only if directly relevant; otherwise return empty list
    - EDUCATION_1 — select at most 3 bullets, only if they add something not covered by work experience
    - Quality over quantity. Do NOT pad to hit a number. An empty list is better than a weak bullet.
    - Select bullets that mirror the language and priorities of the job offer
    
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

def prepare_skills(blocks: list[str], skills: str, model: str) -> list[str]:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))
    
    prompt = f"""
    You are a professional CV writer specializing in ATS optimization.
    
    ## Step 1 — Classify the role
    Read the job offer and identify:
    - Primary role type (e.g. Data Engineer, AI/ML Engineer, Backend Developer)
    - Top 5 technical requirements
    
    ## Step 2 — Select skills
    Given the candidate's skill list and the role classification above, select the most relevant skills.
    
    Rules:
    - Select between 6 and 9 skills maximum
    - Prioritize exact or near-exact matches to the job offer's required technical stack
    - Prefer hard technical skills over process skills
    - Mirror the terminology used in the job offer where possible
    
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

def prepare_summary(blocks: list[str], selected_bullets: str, model: str) -> list[str]:
    job_blocks = "\n\n".join(f" {b}" for i, b in enumerate(blocks))
    
    prompt = f"""
    You are a professional CV writer specializing in ATS optimization.
    
    ## Step 1 — Classify the role
    Read the job offer and identify:
    - Primary role type (e.g. Data Engineer, AI/ML Engineer, Backend Developer)
    - Top 5 technical requirements
    
    ## Step 2 — Assess fit
    Determine whether the candidate's work experience directly matches the role type.
    - DIRECT FIT: candidate's experience closely matches the role
    - PARTIAL FIT: candidate has relevant transferable skills but comes from a different domain
    
    ## Step 3 — Write summary
    Write a 2-3 sentence professional summary based STRICTLY on the selected experience 
    bullets below.
    
    Rules:
    - Write in first person, Never use third person.
    - Do NOT invent, infer, or add any experience, tools, or claims not present in the bullets
    - When bridging your experience to the role, use the job offer's terminology 
  but rephrase in your own words, do not copy sentence structures
    - Every claim in the summary must be traceable to a specific 
  selected bullet. If you cannot point to the bullet, remove the claim
    - Mirror the terminology used in the job offer where possible
    - Start with the candidate's current role and strongest relevant qualification
    - Always open with the candidate's actual current job title, 
  never the target role title
    - End with what value they bring to this specific role
    - Do NOT use filler phrases like "passionate about", "proven track record", "dynamic"
    - If PARTIAL FIT: explicitly bridge the candidate's background to the target role in 
      1-2 sentences — make the connection clear rather than leaving it to the reader
    - If DIRECT FIT: focus purely on relevant experience and impact, write 3 sentences.
    
    --- SELECTED EXPERIENCE BULLETS ---
    {selected_bullets}
    
    --- JOB OFFER ---
    {job_blocks}
    
    Return ONLY valid JSON in this exact format:
    {{
      "role_classification": {{
        "role_type": "...",
        "top_technical_requirements": ["..."]
      }},
      "fit_assessment": "DIRECT FIT" or "PARTIAL FIT",
      "SUMMARY": {{"text": "...", "reason": "..."}}
    }}
    """
    
    response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
    fields = json.loads(response.message.content)
    

    return fields