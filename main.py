from extract_job import (extract_blocks, 
                         filter_relevant_blocks, 
                         filter_title_company,
                         extract_lang,
                         prepare_cv_fields,
                         prepare_skills,
                         prepare_summary)

from template_filler import generate_document, convert_to_pdf, prepare_fill_input
from bulletpoint_select import fill_experience_placeholders
from pathlib import Path
import json


#%%

# export job, select relevant html blocks, select relevant bulletpoints from experience json

with open("experience.json", "r", encoding="utf-8") as f:
    experience_data = json.load(f)
    
with open("skills.json", "r", encoding="utf-8") as f:
    skills_data = json.load(f)

#%%
job_link = "https://www.galaxus.ch/de/joboffer/4140"
blocks = extract_blocks(job_link)

relevant_blocks = filter_relevant_blocks(blocks)

job_title, company_name, language = filter_title_company(relevant_blocks)

experience = extract_lang(experience_data, language)
skills = extract_lang(skills_data, language)

experience_numbers = prepare_cv_fields(relevant_blocks, experience)
skill_numbers = prepare_skills(relevant_blocks, skills)

selected_experience = prepare_fill_input(experience_numbers, experience_data)
selected_skill = prepare_fill_input(skill_numbers, skills_data)

#%%

selected_bullets = []
for block, data in selected_experience.items():
    for num, text in data.items():
        selected_bullets.append(text)

selected_bullets_text = "\n".join(f"- {b}" for b in selected_bullets)

summary = prepare_summary(relevant_blocks, selected_bullets_text)

#%%

# select some default experiences so they are there even if llm does not choose
DEFAULTS = {
    "EXPERIENCE_1": ["1", "7", "10", "12", "6"],  # LLM+RAG, sole engineer, agents, prompt eng, feasibility
    "EXPERIENCE_2": ["1", "2", "7"],               # dev+team, CI/CD, REST APIs
    "EXPERIENCE_3": ["1", "2"],                    # research, simulation pipeline
    "EDUCATION_1":  ["1", "2", "3"],               # thesis, coursework, teaching assistant
}

MIN_BULLETS = {
    "EXPERIENCE_1": 4,
    "EXPERIENCE_2": 2,
    "EXPERIENCE_3": 2,
    "EDUCATION_1":  2,
}

def apply_defaults(selected_experience: dict, experience: dict, language: str = "en") -> dict:
    result = {}
    for block, min_count in MIN_BULLETS.items():
        current_nums = list(selected_experience.get(block, {}).get("numbers", []))
        current_nums_str = [str(n) for n in current_nums]
        
        # Add defaults if below minimum, avoiding duplicates
        if len(current_nums_str) < min_count:
            for default_num in DEFAULTS.get(block, []):
                if len(current_nums_str) >= min_count:
                    break
                if default_num not in current_nums_str:
                    current_nums_str.append(default_num)
        
        # Build the resolved text dict in order
        resolved = {}
        for num in current_nums_str:
            if num in experience.get(block, {}):
                resolved[num] = experience[block][num][language]
        
        result[block] = resolved
    
    return result

filled_experience = apply_defaults(selected_experience, experience_data, language="en")

#%%

# fill hardcoded fields (e.g. name, sections) and generate .odt
output_folder = Path.home() / "Downloads" / "CV" / company_name.lower()

filename = "CV_" + job_title.lower()
generate_document(filename, language, output_folder)

#%%

# fill out selected bulletpoints and save to pdf

output_path = str(output_folder / filename ) + "_" + language



fill_experience_placeholders(output_path + ".odt", 
                             output_path + "_final.odt", 
                             filled_experience | selected_skill | {"SUMMARY": summary["SUMMARY"]})

convert_to_pdf(output_path + "_final.odt", "" )

