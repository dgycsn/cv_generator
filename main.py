from helpers import dict2str, apply_defaults

from extract_job_page import extract_blocks, filter_relevant_blocks, filter_title_company
from generate_placeholders import prepare_experiences, prepare_skills, prepare_summary

from fill_translation_placeholders import generate_document, convert_to_pdf, prepare_fill_input
from fill_experience_placeholders import fill_experience_placeholders

from pathlib import Path
import json

model = "qwen2.5:32b"

#%%

# export job, select relevant html blocks, select relevant bulletpoints from experience json

with open("./configs/experience.json", "r", encoding="utf-8") as f:
    experience_data = json.load(f)
    
with open("./configs/skills.json", "r", encoding="utf-8") as f:
    skills_data = json.load(f)

#%%
job_link = "https://www.galaxus.ch/de/joboffer/4140"
blocks = extract_blocks(job_link)

relevant_blocks = filter_relevant_blocks(blocks, model)

job_title, company_name, language = filter_title_company(relevant_blocks, model)

experience = dict2str(experience_data, language)
skills = dict2str(skills_data, language)

experience_numbers = prepare_experiences(relevant_blocks, experience, model)
skill_numbers = prepare_skills(relevant_blocks, skills, model)

selected_experience = prepare_fill_input(experience_numbers, experience_data, model)
selected_skill = prepare_fill_input(skill_numbers, skills_data, model)

#%%

selected_bullets = []
for block, data in selected_experience.items():
    for num, text in data.items():
        selected_bullets.append(text)

selected_bullets_text = "\n".join(f"- {b}" for b in selected_bullets)

summary = prepare_summary(relevant_blocks, selected_bullets_text)

#%%

filled_experience = apply_defaults(selected_experience, experience_data, language="en")

#%%

# fill hardcoded fields (e.g. name, sections) and generate .odt
output_folder = Path.home() / "Destop" / "git" / "cv_generator" / "outputs"

filename = "CV_" + job_title.lower()
generate_document(filename, language, output_folder)

#%%

# fill out selected bulletpoints and save to pdf

output_path = str(output_folder / filename ) + "_" + language



fill_experience_placeholders(output_path + ".odt", 
                             output_path + "_final.odt", 
                             filled_experience | selected_skill | {"SUMMARY": summary["SUMMARY"]})

convert_to_pdf(output_path + "_final.odt", "" )

