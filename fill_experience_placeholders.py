import zipfile
import re
import html

def fill_experience_placeholders(odt_path: str, output_path: str, experience_data: dict):
    with zipfile.ZipFile(odt_path, "r") as z:
        names = z.namelist()
        files = {name: z.read(name) for name in names}
    content = files["content.xml"].decode("utf-8")

    # 1. Normalize split placeholders (LibreOffice may inject spans inside {{ }})
    content = re.sub(
        r'\{\{(<[^>]+>)*([A-Z_0-9]+)(<[^>]+>)*\}\}',
        r'{{\2}}',
        content
    )

    if "SUMMARY" in experience_data:
        safe_summary = html.escape(experience_data["SUMMARY"]["text"])
        content = content.replace("{{PROFILE_SUMMARY}}", safe_summary)
        experience_data = {k: v for k, v in experience_data.items() if k != "SUMMARY"}

    # 2. Fill slots
    for section, entries in experience_data.items():
        for new_num, text in enumerate(entries.values(), start=1):
            safe_text = html.escape(text)
            bullet = "\u25b8"  # ▸
            content = content.replace(f"{{{{{section}_{new_num}}}}}", f"{bullet} {safe_text}")

    # 3. Clear all remaining unfilled placeholders
    content = re.sub(r'\{\{[A-Z_0-9]+\}\}', '', content)

    # 4. Remove now-empty paragraph lines
    def is_empty_paragraph(tag_text):
        inner = tag_text[tag_text.index('>') + 1:]
        inner = re.sub(r'<[^>]+/>', '', inner)
        if re.search(r'<[a-zA-Z]', inner):
            return False
        text_only = re.sub(r'<[^>]+>', '', inner).strip()
        return text_only == ''

    content = re.sub(
        r'<text:p [^>]*>.*?</text:p>',
        lambda m: '' if is_empty_paragraph(m.group()) else m.group(),
        content,
        flags=re.DOTALL
    )

    # 5. Save
    files["content.xml"] = content.encode("utf-8")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            data = files[name]
            if isinstance(data, str):
                data = data.encode("utf-8")
            zout.writestr(name, data)
            
            
if __name__ == "__main__":
    experience_data = {
        "EXPERIENCE_1": {
            "1": "Led end-to-end AI use case development from ideation to deployment.",
            "3": "Reduced inference latency by 40% through model optimization."
            # "2" not included = that bullet line will be removed
        },
        "EXPERIENCE_2": {
            "1": "Managed a cross-functional team of 8 engineers.",
            "2": "Delivered product roadmap on time and under budget."
        }
    }
    
    fill_experience_placeholders("templates/template.odt", "output.odt", experience_data)
