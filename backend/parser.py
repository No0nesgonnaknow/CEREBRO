import os
import json
import hashlib
from datetime import datetime
from multiprocessing import Pool, cpu_count
from langdetect import detect, DetectorFactory
from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
from PIL import Image
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract
import docx
import re

# === CONFIG ===
BOOKS_PATH = r"D:\BOOK\BOOKS"
DATA_PATH = r"D:\.COUNCIL\Cerebro\data"
POPPLER_PATH = r"D:\.COUNCIL\Cerebro\tools\poppler\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_LANGS = "eng+spa+tgl"
LOG_PATH = os.path.join(DATA_PATH, "parsed_files.log")
MIN_WORD_THRESHOLD = 20

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
DetectorFactory.seed = 0

os.makedirs(DATA_PATH, exist_ok=True)
parsed_hashes = set()
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r", encoding="utf-8") as log:
        parsed_hashes = set(line.strip() for line in log if line.strip())

# === HELPERS ===
def normalize_filename(name):
    return ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in name)

def clean_text(text):
    return ' '.join(line.strip() for line in text.splitlines() if line.strip())

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

def hash_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def inferred_tags(text):
    tokens = set(tokenize(text))
    tags = []
    if {"islam", "quran", "sharia", "ummah"} & tokens:
        tags.append("Islamic Studies")
    if {"indigenous", "ancestral", "customary", "tribal"} & tokens:
        tags.append("Decolonial")
    if {"sovereignty", "nationhood", "self-determination"} & tokens:
        tags.append("Political Theory")
    if {"philosophy", "epistemology", "metaphysics"} & tokens:
        tags.append("Philosophy")
    if {"eurasia", "china", "russia", "usa", "geopolitics"} & tokens:
        tags.append("Geopolitics")
    return tags[:5]

# === PARSERS ===
def ocr_image(img_path):
    try:
        image = Image.open(img_path)
        return pytesseract.image_to_string(image, lang=OCR_LANGS)
    except Exception as e:
        print(f"[✘] OCR failed on image: {img_path} — {e}")
        return ""

def ocr_pdf(pdf_path):
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        return "\n".join(pytesseract.image_to_string(img, lang=OCR_LANGS) for img in images)
    except Exception as e:
        print(f"[✘] OCR failed on PDF: {pdf_path} — {e}")
        return ""

def parse_epub(path):
    try:
        book = epub.read_epub(path)
        text = ""
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text += soup.get_text()
        return text, "epub"
    except Exception as e:
        print(f"[✘] EPUB parse failed: {path} — {e}")
        return None, None

def parse_docx(path):
    try:
        doc = docx.Document(path)
        return '\n'.join(p.text for p in doc.paragraphs), "docx"
    except Exception as e:
        print(f"[✘] DOCX parse failed: {path} — {e}")
        return None, None

def parse_file(path):
    ext = os.path.splitext(path.lower())[1]
    try:
        if ext == ".pdf":
            text = extract_text(path).strip()
            if len(text.split()) < MIN_WORD_THRESHOLD:
                text = ocr_pdf(path)
            return text, "pdf"
        elif ext in (".jpg", ".jpeg", ".png", ".tiff"):
            return ocr_image(path), "image"
        elif ext == ".epub":
            return parse_epub(path)
        elif ext == ".docx":
            return parse_docx(path)
        elif ext in (".txt", ".md"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), "text"
        else:
            print(f"[!] Unsupported file: {path}")
    except Exception as e:
        print(f"[✘] Parse failed: {path} — {e}")
    return None, None

# === PARSE AND SAVE ===
def parse_and_save(file_path, domain):
    if not os.path.isfile(file_path):
        return
    file_hash = hash_file(file_path)
    if file_hash in parsed_hashes:
        return

    text, filetype = parse_file(file_path)
    if not text or len(text.split()) < MIN_WORD_THRESHOLD:
        print(f"[!] Skipped (too short/unreadable): {file_path}")
        return

    text = clean_text(text)
    try:
        lang = detect(text)
    except:
        lang = "unknown"

    base = normalize_filename(os.path.splitext(os.path.basename(file_path))[0])
    basename = f"{domain}__{base}__{lang}"
    out_path = os.path.join(DATA_PATH, f"{basename}.txt")
    meta_path = os.path.join(DATA_PATH, f"{basename}.json")

    try:
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(text)

        metadata = {
            "domain": domain,
            "filename": base,
            "language": lang,
            "tags": inferred_tags(text),
            "length": len(text),
            "words": len(text.split()),
            "filetype": filetype,
            "path": file_path,
            "hash": file_hash,
            "parsed_at": datetime.now().isoformat()
        }

        with open(meta_path, "w", encoding="utf-8") as m:
            json.dump(metadata, m, indent=2, ensure_ascii=False)

        with open(LOG_PATH, "a", encoding="utf-8") as log:
            log.write(f"{file_hash}\n")

        parsed_hashes.add(file_hash)
        print(f"[✔] Parsed: {file_path}")
    except Exception as e:
        print(f"[✘] Failed to save: {file_path} — {e}")

# === SCAN ALL ===
def scan_all():
    print(f"[🔍] Scanning {BOOKS_PATH}...")
    file_list = []
    for domain in os.listdir(BOOKS_PATH):
        domain_path = os.path.join(BOOKS_PATH, domain)
        if os.path.isdir(domain_path):
            for file in os.listdir(domain_path):
                file_path = os.path.join(domain_path, file)
                file_list.append((file_path, domain))
    print(f"[⚙] Files found: {len(file_list)}")
    with Pool(cpu_count() // 2 or 1) as pool:
        pool.starmap(parse_and_save, file_list)
    print(f"[✔] Scan complete.")

# === MAIN ENTRY ===
if __name__ == "__main__":
    scan_all()
