import json
import zipfile
import shutil
import os
import re
from tempfile import mkdtemp

def flatten_bullets(all_bullets, language="en"):
    flattened = {}
    for category, bullets in all_bullets.items():
        flattened[category] = {num: text[language] for num, text in bullets.items()}
    return flattened

def insert_bulletpoints_in_odt(template_odt_path, output_odt_path, llm_output, bullets):
    temp_dir = mkdtemp()

    # Extract ODT
    with zipfile.ZipFile(template_odt_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    content_file = os.path.join(temp_dir, "content.xml")

    # Read content.xml
    with open(content_file, "r", encoding="utf-8") as f:
        content = f.read()

    # For each category in LLM output
    for category, data in llm_output.items():
        selected = data.get("selected", [])
        reasoning = data.get("reasoning", [])

        for i, num in enumerate(selected, start=1):
            num_str = str(num)
            if category in bullets and num_str in bullets[category]:
                text = bullets[category][num_str]
                if i <= len(reasoning) and reasoning[i-1]:
                    text += f" ({reasoning[i-1]})"

                # Regex to match placeholder with optional whitespace inside XML
                pattern = re.compile(r"\{\{\s*" + re.escape(f"{category}_{i}") + r"\s*\}\}")
                content = pattern.sub(text, content)

        # Remove leftover placeholders
        i = len(selected) + 1
        while True:
            pattern = re.compile(r"\{\{\s*" + re.escape(f"{category}_{i}") + r"\s*\}\}")
            if pattern.search(content):
                content = pattern.sub("", content)
                i += 1
            else:
                break

        # Also handle single placeholder without numbering
        if len(selected) == 1:
            pattern = re.compile(r"\{\{\s*" + re.escape(category) + r"\s*\}\}")
            content = pattern.sub(bullets[category][str(selected[0])], content)

    # Write back
    with open(content_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Repack ODT
    shutil.make_archive(output_odt_path.replace(".odt", ""), 'zip', temp_dir)
    os.rename(output_odt_path.replace(".odt", "") + ".zip", output_odt_path)
    shutil.rmtree(temp_dir)
    
example_selected_bullets = """{
  "EXPERIENCE_1": {
    "selected": [1,2],
    "reasoning": [
      "Managed a team relevant to leadership required by job",
      "Python skills match requirements"
    ]
  },
  "EDUCATION": {
    "selected": [1],
    "reasoning": ["Degree relevant to required computer science background"]
  },
  "certifications": {
    "selected": [],
    "reasoning": []
  }
}"""

llm_output = json.loads(example_selected_bullets)

def load_experience(language="en"):
    with open("experience.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    resolved = {}

    for category, bullets in raw.items():
        resolved[category] = {}
        for num, translations in bullets.items():
            if language in translations:
                resolved[category][num] = translations[language]
            else:
                # fallback to English if language missing
                resolved[category][num] = translations.get("en", "")

    return resolved

bullets = load_experience()

insert_bulletpoints_in_odt(
    template_odt_path="output_de.odt",
    output_odt_path="final_document.odt",
    llm_output=llm_output,
    bullets=bullets
)