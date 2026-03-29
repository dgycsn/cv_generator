import json
import zipfile
import shutil
import os
import subprocess
from tempfile import mkdtemp
from urllib.parse import quote


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
    try:
        with zipfile.ZipFile(template_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if not filename.endswith(('.xml', '.rdf')):
                    continue
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                for key, value in replacements.items():
                    clean_key = key.strip('{}')
                    placeholder = '{{' + clean_key + '}}'
                    
                    # Replace plain placeholder (in text content)
                    text = text.replace(placeholder, str(value))
                    
                    # Replace URL-encoded placeholder (in href attributes like mailto:)
                    encoded_placeholder = quote(placeholder, safe='')  # → %7B%7BEMAIL%7D%7D
                    encoded_value = quote(str(value), safe='@.')       # keep @ and . unencoded in emails
                    text = text.replace(encoded_placeholder, encoded_value)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            mimetype_path = os.path.join(temp_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zout.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            for root, dirs, files in os.walk(temp_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, temp_dir)
                    if arcname == 'mimetype':
                        continue
                    zout.write(filepath, arcname)
    finally:
        shutil.rmtree(temp_dir)
        
def prepare_fill_input(selected: dict, lang_data: dict, lang: str = "en") -> dict:
    return {
        section: {str(num): lang_data[section][str(num)][lang] for num in data["numbers"]}
        for section, data in selected.items()
        if "numbers" in data and section in lang_data
    }

def convert_to_pdf(input_odt, output):
    if os.path.exists(output):
        try:
            os.remove(output)
        except OSError:
            pass
    
    output_dir = os.path.dirname(os.path.abspath(input_odt))
    
    subprocess.run([
        LIBREOFFICE_PATH,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        input_odt
    ], check=True)


def generate_document(filename, language = "en", output_folder = ""):
    template_folder = "./templates/"
    template = template_folder + "template_new.odt"
    
    # output_folder = "./outputs/"
    filled_odt = f"{output_folder}/{filename}_{language}.odt"

    data = load_translations(language)

    replace_placeholders_in_odt(template, filled_odt, data)

    # convert_to_pdf(filled_odt, ".")

    # print(f"Generated: {filled_odt} and PDF")


if __name__ == "__main__":
    # generate_document("en")
    generate_document("de")