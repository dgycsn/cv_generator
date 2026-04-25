import zipfile
import shutil
import os
import subprocess
from tempfile import mkdtemp
from urllib.parse import quote
from xml.sax.saxutils import escape
import re

from helpers import find_soffice, load_translations


LIBREOFFICE_PATH = find_soffice()


def convert_markdown_links_to_odf(value):
    """
    Convert markdown links [text](url) in a string to ODF XML hyperlink fragments.
    Non-link parts are XML-escaped. Returns a string ready to splice into XML.
    """
    LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    
    parts = []
    last = 0
    for m in LINK_RE.finditer(value):
        # Escape plain text before this link
        if m.start() > last:
            parts.append(escape(value[last:m.start()]))
        
        link_text = escape(m.group(1))
        link_url  = escape(m.group(2))          # escapes & etc. in the URL
        parts.append(
            f'<text:a xlink:type="simple" xlink:href="{link_url}">'
            f'{link_text}'
            f'</text:a>'
        )
        last = m.end()
    
    # Escape any trailing plain text
    if last < len(value):
        parts.append(escape(value[last:]))
    
    return ''.join(parts)


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
                    value_str = str(value)

                    # Check whether this value contains any markdown links
                    if re.search(r'\[([^\]]+)\]\(([^)]+)\)', value_str):
                        # Produce ODF XML — must NOT be additionally escaped
                        safe_value = convert_markdown_links_to_odf(value_str)
                    else:
                        # Plain text — escape XML special chars as before
                        safe_value = escape(value_str)

                    text = text.replace(placeholder, safe_value)

                    # URL-encoded placeholder replacement (e.g. inside href attributes)
                    # Links inside href don't make sense here, so keep existing behaviour
                    encoded_placeholder = quote(placeholder, safe='')
                    encoded_value = quote(value_str, safe='@.')
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


def generate_document(filename, 
                      config="./configs/",
                      template="./templates/template_new.odt", 
                      output_folder="./outputs/",
                      language="en",
                      extra_translations = {}):
    
    os.makedirs(output_folder, exist_ok=True)
    filled_odt = os.path.join(output_folder, f"{filename}.odt")
    
    data = load_translations(config + "translations.json", language)
    replace_placeholders_in_odt(template, filled_odt, data | extra_translations)



if __name__ == "__main__":
    print("hi")
    # generate_document("test", template = "./templates/motivation_letter_template.odt")
    