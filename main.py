from extract_job import (extract_blocks, 
                         filter_relevant_blocks, 
                         filter_title_company,
                         extract_lang,
                         prepare_cv_fields,
                         prepare_skills)

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

#%%

# if llm doesnt select enough bulletpoints, chose first two by default
DEFAULT_NUMBERS = [1, 2]
LIMIT = 3

for key, value in experience_numbers.items():
    if 'numbers' in value:
        if len(value['numbers']) < LIMIT:
            # Add defaults that aren't already in the list
            missing = [n for n in DEFAULT_NUMBERS if n not in value['numbers']]
            value['numbers'] = value['numbers'] + missing

#%%

# fill hardcoded fields (e.g. name, sections) and generate .odt
output_folder = Path.home() / "Downloads" / "CV" / company_name.lower()

filename = "CV_" + job_title.lower()
generate_document(filename, language, output_folder)

#%%

# fill out selected bulletpoints and save to pdf

output_path = str(output_folder / filename ) + "_" + language

experience_selected = prepare_fill_input(experience_numbers, experience_data)
skill_selected = prepare_fill_input(skill_numbers, skills_data)

fill_experience_placeholders(output_path + ".odt", output_path + "_final.odt", experience_selected | skill_selected)

convert_to_pdf(output_path + "_final.odt", "" )

