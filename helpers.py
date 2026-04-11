import json
import shutil
import os
import sys
import glob

def dict2str(data: dict, lang = "en") -> str:
    """
    create string from dictionary to be used in llm prompts
    """
    cleaned = {
        section: {num: items[lang] for num, items in entries.items() if lang in items}
        for section, entries in data.items()
    }
    return json.dumps(cleaned, indent=2, ensure_ascii=False)

def load_translations(dict_name, language="en"):
    """
    load correct elements from dictionary
    """
    with open(dict_name, "r", encoding="utf-8") as f:
        raw = json.load(f)

    resolved = {}

    for key, translations in raw.items():
        if language in translations:
            resolved[key] = translations[language]
        else:
            # fallback (optional)
            resolved[key] = translations.get("en", "")

    return resolved

def find_soffice():
    """
    find libre office for conversions
    """
    # 1. Check if it's on PATH (works cross-platform)
    path = shutil.which("soffice")
    if path:
        return path

    # 2. Windows fallback locations
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

    # 3. macOS fallback
    elif sys.platform == "darwin":
        mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.isfile(mac_path):
            return mac_path

    # Linux fallbacks
    elif sys.platform.startswith("linux"):
        candidates = [
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/snap/bin/soffice",                          # Snap package
            "/opt/libreoffice/program/soffice",           # Manual installs
            "/opt/libreoffice7/program/soffice",          # Versioned manual installs
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        # Last resort: search /opt for versioned installs
        for match in glob.glob("/opt/libreoffice*/program/soffice"):
            if os.path.isfile(match):
                return match
            
    raise FileNotFoundError("LibreOffice not found. Install it or add it to PATH.")
    
    
#%%
    
# select some default experiences so they are there even if llm does not choose
DEFAULTS = {
    "EXPERIENCE_1": ["1", "7", "10", "12", "6"],  # LLM+RAG, sole engineer, agents, prompt eng, feasibility
    "EXPERIENCE_2": ["1", "2", "7"],               # dev+team, CI/CD, REST APIs
    "EXPERIENCE_3": ["1", "2"],                    # research, simulation pipeline
    "EDUCATION_1":  ["1", "2", "3"],               # thesis, coursework, teaching assistant
}

MIN_BULLETS = {
    "EXPERIENCE_1": 4,
    "EXPERIENCE_2": 2,
    "EXPERIENCE_3": 2,
    "EDUCATION_1":  2,
}

def apply_defaults(selected_experience: dict, experience: dict, language: str = "en") -> dict:
    result = {}
    for block, min_count in MIN_BULLETS.items():
        current_nums = list(selected_experience.get(block, {}).get("numbers", []))
        current_nums_str = [str(n) for n in current_nums]
        
        # Add defaults if below minimum, avoiding duplicates
        if len(current_nums_str) < min_count:
            for default_num in DEFAULTS.get(block, []):
                if len(current_nums_str) >= min_count:
                    break
                if default_num not in current_nums_str:
                    current_nums_str.append(default_num)
        
        # Build the resolved text dict in order
        resolved = {}
        for num in current_nums_str:
            if num in experience.get(block, {}):
                resolved[num] = experience[block][num][language]
        
        result[block] = resolved
    
    return result