from datetime import datetime
from fill_translation_placeholders import generate_document

from helpers import apply_defaults

from ollama import chat
import json

model = "qwen2.5:32b"

DATE = datetime.today().strftime('%d-%m-%Y')
datedict = {"DATE": DATE}

filename = "CL_Alp_Yuecesan"
cl_template = "./templates/motivation_letter_template.odt"
output_folder = "./outputs/"
config_folder = "./configs"
language = "en"



#%%

filled_experience = apply_defaults(selected_experience, experience_data, language="en")

company_research = ""

job_offer = ""

prompt = f"""
You are writing a motivation letter. You must follow all constraints exactly.

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
- No filler: no "passionate", "excited", "proven track record", "dynamic", "robust", "thrilled", "seasoned"
- Every factual claim must map to a provided bullet. If no bullet supports it, omit it.
- COMPANY_PARAGRAPH must only use facts from COMPANY RESEARCH. Do not invent company facts.
- First person. Present tense for current role, past tense for previous roles.
- Do not copy any sentence, name, company, or fact from the example above.

## Per-paragraph constraints

OPENING_PARAGRAPH:
- Exactly 2 sentences. Maximum 50 words.
- Sentence 1: who you are + strongest skill match to job
- Sentence 2: why this role + specific overlap with job's top need

EXPERIENCE_PARAGRAPH:
- Exactly 3 sentences. Maximum 80 words.
- Sentence 1: current role + concrete achievement with specific detail
- Sentence 2: relevant past experience supporting the job's needs
- Sentence 3: bridge between your skill cluster and a specific job requirement

COMPANY_PARAGRAPH:
- Exactly 2 sentences. Maximum 50 words.
- Sentence 1: specific fact from COMPANY RESEARCH — why this company
- Sentence 2: your specific skill from bullets → their specific need

CLOSING_PARAGRAPH:
- Exactly 2 sentences. Maximum 40 words.
- No new claims. End with a call to action naming the company.

## Inputs

SELECTED BULLETS (only draw from these — no other facts allowed):
{filled_experience}

JOB OFFER (extract: position title, company name, top needs):
{job_offer}

COMPANY NAME: {company_name}

COMPANY RESEARCH (only draw from these for COMPANY_PARAGRAPH):
{company_research}

Return ONLY valid JSON, no preamble, no markdown fences:
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
}}
"""

response = chat(model=model, messages=[{"role": "user", "content": prompt}], format="json")
fields = json.loads(response.message.content)


#%%

fields_final = {key: value["text"] for key, value in fields.items()}
fields_dict = {
    "COMPANY_NAME": company_name,
    "POSITION_TITLE":job_title
    "SALUTATION": "Dear " + company_name + " Team,"
    }

generate_document(filename, config_folder, cl_template, output_folder, language, datedict | fields_final)






