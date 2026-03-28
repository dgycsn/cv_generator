import zipfile
import shutil
import re

def fill_experience_placeholders(odt_path: str, output_path: str, experience_data: dict):
    with zipfile.ZipFile(odt_path, "r") as z:
        names = z.namelist()
        files = {name: z.read(name) for name in names}

    content = files["content.xml"].decode("utf-8")

    # Normalize split placeholders
    content = re.sub(r'\{\{[^}]*\}\}', lambda m: re.sub(r'<[^>]+>', '', m.group()), content)

    # Fill slots in order (1, 2, 3...) regardless of original numbers
    for section, entries in experience_data.items():
        for new_num, text in enumerate(entries.values(), start=1):
            content = content.replace(f"{{{{{section}_{new_num}}}}}", text)

    # Remove remaining unfilled bullet lines
    bullet = '\u25b8'
    content = re.sub(rf'<text:p text:style-name="[^"]*">{bullet} <text:span text:style-name="[^"]*">\{{\{{EXPERIENCE_\d+_\d+\}}\}}</text:span></text:p>', '', content)

    files["content.xml"] = content.encode("utf-8")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            zout.writestr(name, files[name])

    print(f"✓ Saved to {output_path}")


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
