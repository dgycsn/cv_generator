import zipfile
import shutil

def fill_experience_placeholders(odt_path: str, output_path: str, experience_data: dict):
    """
    experience_data format:
    {
        "EXPERIENCE_1": {"1": "Led AI projects...", "2": "Built ML pipelines..."},
        "EXPERIENCE_2": {"1": "Managed team...", "3": "Delivered product..."}
    }
    Entries not selected by LLM are replaced with empty string and the whole line removed.
    """
    # Build replacement map: {{EXPERIENCE_1_1}} -> "text" or ""
    replacements = {}
    for section, entries in experience_data.items():
        # Find max entry number from the template (we'll handle missing ones)
        for num, text in entries.items():
            replacements[f"{{{{{section}_{num}}}}}"] = text

    # Copy original to output
    shutil.copy2(odt_path, output_path)

    # Read ODT (it's a ZIP), edit content.xml, write back
    with zipfile.ZipFile(output_path, "r") as z:
        content = z.read("content.xml").decode("utf-8")

    # Replace matched placeholders with their text
    for placeholder, text in replacements.items():
        content = content.replace(placeholder, text)

    # Remove entire lines with unfilled {{EXPERIENCE_*}} placeholders (including the ▸ bullet)
    import re
    content = re.sub(r'[^\n]*\{\{EXPERIENCE_\d+_\d+\}\}[^\n]*\n?', '', content)

    # Write back
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        with zipfile.ZipFile(odt_path, "r") as zin:
            for item in zin.infolist():
                if item.filename == "content.xml":
                    zout.writestr(item, content.encode("utf-8"))
                else:
                    zout.writestr(item, zin.read(item.filename))

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
