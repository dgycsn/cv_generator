# cv_generator

I got tired of sending the same generic CV to every job and getting ignored. So I built a pipeline that reads a job posting, understands what the role actually needs, and assembles a tailored CV automatically — in the right language, with the right bullets, every time.

This is not a template filler. It uses local LLMs (via Ollama) to reason about role fit, select relevant experience, and write a targeted summary. The output is a clean, ATS-optimized PDF ready to send.

---

## How it works

```
Job URL
   │
   ▼
[1] Scrape & filter HTML
      Extract relevant blocks (title, requirements, responsibilities)
      Discard: nav menus, cookie banners, ads
   │
   ▼
[2] Classify the role
      Identify role type (e.g. Data Engineer, AI/ML Engineer)
      Extract top technical & process requirements
   │
   ▼
[3] Select experience bullets
      Match candidate's experience JSON against role requirements
      Respect priority hierarchy: current role > previous > internship > education
      Apply minimum bullet defaults to prevent empty sections
   │
   ▼
[4] Select skills
      Pick 5–8 skills from candidate's skills JSON
      Prefer hard technical skills that mirror job description terminology
   │
   ▼
[5] Write profile summary
      Ground summary strictly in selected bullets, no fabrication
      Detect direct vs. partial fit and bridge accordingly
      First person, 2–3 sentences, no filler phrases
   │
   ▼
[6] Fill ODT template
      Replace {{placeholders}} with selected content
      Remove empty bullet lines automatically
      Export to PDF
```

---

## Example output

Total runtime: ~300 seconds on a local GPU.

WATCH DEMO BY CLICKING ON CAR!!!

 \>>> [![Watch the video](car.png)](https://www.youtube.com/watch?v=yNdxS3wlHVA) <<<
---

## Installation

**Requirements:**
- Python 3.10+
- [Ollama](https://ollama.ai) running locally
- LibreOffice (for ODT → PDF conversion)
- `qwen2.5:32b` model pulled in Ollama

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Pull the model:**

```bash
ollama pull qwen2.5:32b
```

**Configure your profile:**
Edit `translations.json` for hardcoded translations, e.g. sections, name, titles.
Edit `experience.json`,  and `skills.json` with your own experience and skills. These are the source pools the LLM selects from, the quality of your inputs directly affects output quality.

---

## Design decisions

**Why local LLMs?** Privacy. Your CV and job applications contain sensitive personal and professional information. Nothing leaves your machine.

**Why ODT and not DOCX or LaTeX?** ODT is open, editable in LibreOffice, and converts cleanly to PDF. LaTeX produces beautiful output but is overkill for this use case and harder to maintain visually.

**Why select from a bullet pool instead of generating new bullets?** Generated bullets hallucinate: they invent tools, timeframes, and outcomes that aren't true. Selection from a pre-written, verified pool guarantees honesty and keeps human in the loop. The LLM's job is to choose and order, not to invent.

---

## Limitations

- Pipeline tested primarily against Swiss and German job postings
- Very long or poorly structured job pages may confuse the HTML block filter
- Model quality affects selection accuracy — `qwen2.5:32b` works well; smaller models may make weaker choices (skill issue)

---

