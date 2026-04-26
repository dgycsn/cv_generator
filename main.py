from dialogs import run_dialog
from helpers import dict2str, apply_defaults, enforce_maximums
from extract_job_page import extract_blocks, filter_relevant_blocks, filter_title_company
from generate_placeholders import prepare_experiences, prepare_skills, prepare_summary
from fill_translation_placeholders import generate_document, convert_to_pdf, prepare_fill_input
from fill_experience_placeholders import fill_experience_placeholders
from generate_motivation_letter import generate_motivation_letter
from research_agent import research_full
import json
import os
import time

model = "qwen2.5:32b"

import torch

# ─── CPU THREAD LIMITS ───────────────────────────────────────────
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ─── PYTORCH THREAD LIMITS ───────────────────────────────────────
torch.set_num_threads(4)
torch.set_num_interop_threads(2)

# ─── GPU / CUDA LIMITS ───────────────────────────────────────────
if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(0.75)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"

# ─── PROCESS PRIORITY (cross-platform) ───────────────────────────
import psutil, os as _os
try:
    p = psutil.Process(_os.getpid())
    # p.nice(10)                    # Linux/Mac
    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)  # Windows
except Exception:
    pass

# ─── OLLAMA-SPECIFIC ENV VARS ─────────────────────────────────────
os.environ["OLLAMA_NUM_PARALLEL"] = "1"
os.environ["OLLAMA_MAX_LOADED_MODELS"] = "1"
os.environ["OLLAMA_FLASH_ATTENTION"] = "1"

# ─── GARBAGE COLLECTION ──────────────────────────────────────────
import gc
gc.enable()
gc.collect()


#%%
# ── Pipeline (runs in background thread) ──────────────────────────────────────

def pipeline(dialog_data, progress_callback, stop_event):
    """
    Runs the LLM-heavy steps in a background thread.
    Calls progress_callback(step_index) BEFORE each step.
    Steps are numbered sequentially; their count depends on which documents
    are being generated (gen_cv, gen_cl).
    Raises InterruptedError if the window is closed.
    """
    def check():
        if stop_event.is_set():
            raise InterruptedError("Window closed — pipeline cancelled.")

    job_link      = dialog_data["job_link"]
    config_folder = dialog_data["config_folder"]
    gen_cv        = dialog_data.get("gen_cv", True)
    gen_cl        = dialog_data.get("gen_cl", False)

    with open(config_folder + "experience.json", "r", encoding="utf-8") as f:
        experience_data = json.load(f)

    # Skills only needed for CV
    skills_data = {}
    if gen_cv:
        with open(config_folder + "skills.json", "r", encoding="utf-8") as f:
            skills_data = json.load(f)

    # Step counter — incremented before each step so the progress bar advances
    step = 0

    # ── Step: extract job page (always runs) ──────────────────────────────────
    progress_callback(step); step += 1
    blocks          = extract_blocks(job_link)
    relevant_blocks = filter_relevant_blocks(blocks, model)
    job_title, company_name, language = filter_title_company(relevant_blocks, model)
    check()

    # ── CV-only steps ─────────────────────────────────────────────────────────
    selected_experience = {}
    selected_skill      = {}
    summary             = {}

    if gen_cv:
        # Select experience
        progress_callback(step); step += 1
        experience          = dict2str(experience_data, language)
        experience_numbers  = prepare_experiences(relevant_blocks, experience, model)
        selected_experience = prepare_fill_input(experience_numbers, experience_data)
        check()

        # Select skills
        progress_callback(step); step += 1
        skills         = dict2str(skills_data, language)
        skill_numbers  = prepare_skills(relevant_blocks, skills, model)
        selected_skill = prepare_fill_input(skill_numbers, skills_data)
        check()

        # Generate summary
        progress_callback(step); step += 1
        filled_experience    = apply_defaults(selected_experience, experience_data, language="en")
        selected_bullets     = [t for block in filled_experience.values() for t in block.values()]
        selected_bullets_text = "\n".join(f"- {b}" for b in selected_bullets)
        summary = prepare_summary(relevant_blocks, selected_bullets_text, model)
        check()

    # ── CL-only steps ─────────────────────────────────────────────────────────
    company_research = ""
    company_address  = ""

    if gen_cl:
        # Research company (single pass — returns brief and address together)
        progress_callback(step); step += 1
        company_research, company_address = research_full(company_name)
        check()

    result = {
        "job_title":           job_title,
        "company_name":        company_name,
        "language":            language,
        "relevant_blocks":     relevant_blocks,
        "selected_experience": selected_experience,
        "selected_skill":      selected_skill,
        "experience_data":     experience_data,
        "summary":             summary,
        "company_research":    company_research,
        "company_address":     company_address,
        **dialog_data,
    }
    globals().update(result)
    return result


#%%
# ── Finish (runs on main thread after pipeline, before page 3) ────────────────

def finish(result):
    """
    Generates the requested documents (.odt and .pdf).
    Called on the main thread once the pipeline completes.
    """
    globals().update(result)

    job_title           = result["job_title"]
    company_name        = result["company_name"]
    language            = result["language"]
    relevant_blocks     = result["relevant_blocks"]
    selected_experience = result["selected_experience"]
    selected_skill      = result["selected_skill"]
    experience_data     = result["experience_data"]
    summary             = result["summary"]
    company_research    = result["company_research"]
    company_address     = result["company_address"]
    filename            = result["filename"]
    template            = result.get("template", "")
    cl_template         = result.get("cl_template", "")
    config_folder       = result["config_folder"]
    output_folder       = result["output_folder"]
    gen_cv              = result.get("gen_cv", True)
    gen_cl              = result.get("gen_cl", False)

    # Shared output folder per company
    cv_folder = os.path.join(output_folder, company_name.split(" ")[0])
    os.makedirs(cv_folder, exist_ok=True)

    # ── Generate CV ───────────────────────────────────────────────────────────
    if gen_cv:
        filled_experience = apply_defaults(selected_experience, experience_data, language="en")
        filled_experience = enforce_maximums(filled_experience)

        generate_document(filename, config_folder, template, cv_folder, language)

        output_path = os.path.join(cv_folder, filename)
        fill_experience_placeholders(
            output_path + ".odt",
            output_path + "_" + language + ".odt",
            filled_experience | selected_skill | {"SUMMARY": summary["SUMMARY"]}
        )

        # Retry once — LibreOffice sometimes has a stale headless process
        for attempt in range(2):
            try:
                convert_to_pdf(output_path + "_" + language + ".odt", "")
                break
            except Exception:
                if attempt == 0:
                    time.sleep(2)
                else:
                    raise

    # ── Generate motivation letter ────────────────────────────────────────────
    if gen_cl:
        cl_paragraphs = generate_motivation_letter(
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
            output_folder       = cv_folder,
            model               = model,
        )
        # Bubble up paragraphs so page 3 can display them
        result.update(cl_paragraphs)


#%%
# ── Launch ────────────────────────────────────────────────────────────────────

run_dialog(pipeline_fn=pipeline, finish_fn=finish)