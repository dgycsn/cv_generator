from extract_job import (extract_blocks, 
                         filter_relevant_blocks, 
                         filter_title_company,
                         extract_lang,
                         prepare_cv_fields)

from template_filler import generate_document, convert_to_pdf
from bulletpoint_select import fill_experience_placeholders
from pathlib import Path
import json


#%%

# export job, select relevant html blocks, select relevant bulletpoints from experience json

with open("experience.json", "r", encoding="utf-8") as f:
    data = json.load(f)

experience = extract_lang(data, "en")

job_link = "https://www.galaxus.ch/de/joboffer/4140"
blocks = extract_blocks(job_link)

relevant_blocks = filter_relevant_blocks(blocks)

job_title, company_name, language = filter_title_company(relevant_blocks)


selected_fields = prepare_cv_fields(relevant_blocks, experience)

#%%

# fill hardcoded fields (e.g. name, sections) and generate .odt
output_folder = Path.home() / "Downloads" / "CV" / company_name.lower()

filename = "CV_" + job_title.lower()
generate_document(filename, language, output_folder)

#%%

# fill out selected bulletpoints and save to pdf

output_path = str(output_folder / filename ) + "_" + language

def prepare_fill_input(selected: dict, lang_data: dict, lang: str = "en") -> dict:
    return {
        section: {str(num): lang_data[section][str(num)][lang] for num in data["numbers"]}
        for section, data in selected.items()
        if "numbers" in data and section in lang_data
    }

experience_data = prepare_fill_input(selected_fields, data)

fill_experience_placeholders(output_path + ".odt", output_path + "_final.odt", experience_data)

convert_to_pdf(output_path + "_final.odt", "" )