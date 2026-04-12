import os
import subprocess
from tkinter import Tk, filedialog
from PyPDF2 import PdfReader, PdfWriter

"""
if selected pdf: crop its first page only
if selected odt: crop and convert to pdf
"""

def select_file():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)  # Force window to front
    root.update()  # Ensure it takes effect

    file_path = filedialog.askopenfilename(parent=root)

    root.destroy()
    return file_path

def convert_odt_to_pdf(odt_path):
    output_dir = os.path.dirname(odt_path)
    subprocess.run([
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        odt_path
    ], check=True)

    pdf_path = os.path.splitext(odt_path)[0] + ".pdf"
    return pdf_path

def crop_first_page(pdf_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    first_page = reader.pages[0]

    # Example crop: remove margins (adjust as needed)
    media_box = first_page.mediabox
    width = float(media_box.width)
    height = float(media_box.height)

    # Crop 10% from each side
    first_page.mediabox.lower_left = (width, height)
    first_page.mediabox.upper_right = (width, height)

    writer.add_page(first_page)

    output_path = os.path.splitext(pdf_path)[0] + "_processed.pdf"
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path

def main():
    file_path = select_file()

    if not file_path:
        print("No file selected.")
        return

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".odt":
        print("Converting ODT to PDF...")
        pdf_path = convert_odt_to_pdf(file_path)
        print(f"Converted to: {pdf_path}")

        print("Processing first page...")
        output = crop_first_page(pdf_path)
        print(f"Saved: {output}")

    elif ext == ".pdf":
        print("Processing PDF...")
        output = crop_first_page(file_path)
        print(f"Saved: {output}")

    else:
        print("Unsupported file type.")

if __name__ == "__main__":
    main()