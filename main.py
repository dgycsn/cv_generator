from dialogs import run_dialog
from helpers import dict2str, apply_defaults
from extract_job_page import extract_blocks, filter_relevant_blocks, filter_title_company
from generate_placeholders import prepare_experiences, prepare_skills, prepare_summary
from fill_translation_placeholders import generate_document, convert_to_pdf, prepare_fill_input
from fill_experience_placeholders import fill_experience_placeholders
import json
import os
import time
import sys

model = "qwen2.5:32b"


#%%
# ── Pipeline (runs in background thread) ──────────────────────────────────────

def pipeline(dialog_data, progress_callback, stop_event):
    """
    Runs the LLM-heavy steps in a background thread.
    Calls progress_callback(step_index) BEFORE each step.
    Raises InterruptedError via check() if the window is closed.
    """
    def check():
        if stop_event.is_set():
            raise InterruptedError("Window closed — pipeline cancelled.")

    job_link      = dialog_data["job_link"]
    config_folder = dialog_data["config_folder"]

    with open(config_folder + "experience.json", "r", encoding="utf-8") as f:
        experience_data = json.load(f)
    with open(config_folder + "skills.json", "r", encoding="utf-8") as f:
        skills_data = json.load(f)

    # ── Step 1: extract job page ──────────────────────────────────────────────
    progress_callback(0)
    blocks = extract_blocks(job_link)
    relevant_blocks = filter_relevant_blocks(blocks, model)
    job_title, company_name, language = filter_title_company(relevant_blocks, model)
    check()

    # ── Step 2: select experience ─────────────────────────────────────────────
    progress_callback(1)
    experience      = dict2str(experience_data, language)
    experience_numbers  = prepare_experiences(relevant_blocks, experience, model)
    selected_experience = prepare_fill_input(experience_numbers, experience_data)
    check()

    # ── Step 3: select skills ─────────────────────────────────────────────────
    progress_callback(2)
    skills         = dict2str(skills_data, language)
    skill_numbers  = prepare_skills(relevant_blocks, skills, model)
    selected_skill = prepare_fill_input(skill_numbers, skills_data)
    check()

    # ── Step 4: generate summary ──────────────────────────────────────────────
    progress_callback(3)
    # selected_bullets = [
    #     text
    #     for block_data in selected_experience.values()
    #     for text in block_data.values()
    # ]
    # selected_bullets_text = "\n".join(f"- {b}" for b in selected_bullets)
    
    filled_experience = apply_defaults(selected_experience, experience_data, language="en")
    selected_bullets = [
        text
        for block_data in filled_experience.values()
        for text in block_data.values()
    ]
    selected_bullets_text = "\n".join(f"- {b}" for b in selected_bullets)
    summary = prepare_summary(relevant_blocks, selected_bullets_text, model)
    check()

    return {
        "job_title":           job_title,
        "company_name":        company_name,
        "language":            language,
        "selected_experience": selected_experience,
        "selected_skill":      selected_skill,
        "experience_data":     experience_data,
        "summary":             summary,
        **dialog_data,
    }


#%%
# ── Finish (runs on main thread after pipeline, before page 3) ────────────────

def finish(result):
    """
    Generates the final .odt and .pdf CV files.
    Called on the main thread once the pipeline completes.
    Retries convert_to_pdf once on failure to handle stale LibreOffice processes.
    """
    job_title           = result["job_title"]
    company_name        = result["company_name"]
    language            = result["language"]
    selected_experience = result["selected_experience"]
    selected_skill      = result["selected_skill"]
    experience_data     = result["experience_data"]
    summary             = result["summary"]
    filename      = result["filename"]
    template      = result["template"]
    config_folder = result["config_folder"]
    output_folder = result["output_folder"]

    filled_experience = apply_defaults(selected_experience, experience_data, language="en")

    cv_folder = output_folder + "/" + company_name.split(" ")[0]
    os.makedirs(cv_folder, exist_ok=True)   # ensure output folder exists

    generate_document(filename, config_folder, template, cv_folder, language)

    output_path = cv_folder + "/" + filename
    fill_experience_placeholders(
        output_path + ".odt",
        output_path + "_" + language + ".odt",
        filled_experience | selected_skill | {"SUMMARY": summary["SUMMARY"]}
    )

    # Retry once on failure — LibreOffice sometimes has a stale headless process
    for attempt in range(2):
        try:
            convert_to_pdf(output_path + "_" + language + ".odt", "")
            break
        except:
            if attempt == 0:
                time.sleep(2)   # wait for any lingering soffice.exe to exit
            else:
                raise

#%%
# ── Launch ────────────────────────────────────────────────────────────────────

run_dialog(pipeline_fn=pipeline, finish_fn=finish)