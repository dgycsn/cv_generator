import json
import zipfile
import shutil
import os
import subprocess
from tempfile import mkdtemp
import tempfile

LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

def load_translations(language="en"):
    with open("translations.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    resolved = {}

    for key, translations in raw.items():
        if language in translations:
            resolved[key] = translations[language]
        else:
            # fallback (optional)
            resolved[key] = translations.get("en", "")

    return resolved


def replace_placeholders_in_odt(template_path, output_path, replacements):
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except OSError:
            pass
        
    temp_dir = mkdtemp()

    # Unzip ODT
    with zipfile.ZipFile(template_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    content_file = os.path.join(temp_dir, "content.xml")

    # Read XML
    with open(content_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace placeholders
    for key, value in replacements.items():
        placeholder = "{{" + key + "}}"
        content = content.replace(placeholder, str(value))

    # Write back
    with open(content_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Zip back to ODT
    shutil.make_archive(output_path.replace(".odt", ""), 'zip', temp_dir)
    os.rename(output_path.replace(".odt", "") + ".zip", output_path)

    shutil.rmtree(temp_dir)

def convert_to_pdf(input_odt, output):
    if os.path.exists(output):
        try:
            os.remove(output)
        except OSError:
            pass
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run([
            LIBREOFFICE_PATH,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", tmp_dir,
            input_odt
        ], check=True)


def generate_document(filename, language = "en", output_folder = ""):
    template_folder = "./templates/"
    template = template_folder + "template.odt"
    # output_folder = "./outputs/"
    filled_odt = f"{output_folder}/{filename}_{language}.odt"

    data = load_translations(language)

    replace_placeholders_in_odt(template, filled_odt, data)

    # convert_to_pdf(filled_odt, ".")

    # print(f"Generated: {filled_odt} and PDF")


if __name__ == "__main__":
    # generate_document("en")
    generate_document("de")