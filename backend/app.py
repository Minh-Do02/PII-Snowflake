import os
import re
import uuid
from datetime import date
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from faker import Faker
from cryptography.fernet import Fernet
import pandas as pd
from docx import Document
from dotenv import load_dotenv

import torch
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Request


# =====================================================
# CONFIGURATION
# =====================================================

# Charger .env depuis la racine du projet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

FERNET_KEY = os.environ.get("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY environment variable is required")

fernet = Fernet(FERNET_KEY)
fake = Faker("fr_FR")

app = FastAPI(title="RGPD Fiscal Anonymizer – CamemBERT")

# =====================================================
# CAMEMBERT NER
# =====================================================


NER_MODEL = "Jean-Baptiste/camembert-ner-with-dates"

tokenizer = AutoTokenizer.from_pretrained(
    NER_MODEL,
    use_fast=True   # force le fast tokenizer
)
model = AutoModelForTokenClassification.from_pretrained(NER_MODEL)

ner = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple"
)

CAMEMBERT_MAP = {
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "LOC": "ADDRESS",
    "DATE": "DATE"
}

# =====================================================
# REGEX PII (FISCAL FR)
# =====================================================
PII_REGEX = {
    "EMAIL": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "PHONE_NUMBER": r"\b(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}\b",
    "ZIP_CODE": r"\b\d{5}\b",
    "CITY": r"\b(?:Paris|Lyon|Marseille|Toulouse|Nice|Nantes|Bordeaux|Lille)\b",
    "SIREN": r"\b\d{9}\b",
    "SIRET": r"\b\d{14}\b",
    "VAT_NUMBER": r"\bFR\s?\d{11}\b",
    "IBAN": r"\bFR\d{2}(?:\s?\d{4}){5}\b",
    "REVENUE": r"\b\d{1,3}(?:[ .]\d{3})*(?:€|EUR)\b",
    "TAX_AMOUNT": r"(imp[oô]t|taxe)[^\d]*(\d{1,3}(?:[ .]\d{3})*(?:€|EUR))",
}

# =====================================================
# FAKE VALUE (GARDE LA STRUCTURE )
# =====================================================
def fake_value(entity, original):
    if entity == "PERSON":
        val = fake.first_name() + " " + fake.last_name()

    elif entity == "FIRST_NAME":
        val = fake.first_name()

    elif entity == "LAST_NAME":
        val = fake.last_name()

    elif entity == "DATE":
        dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
        val = dob.strftime("%d/%m/%Y")

    elif entity == "AGE":
        dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
        val = str(date.today().year - dob.year)

    elif entity == "ORGANIZATION":
        val = fake.company()

    elif entity == "SIREN":
        val = fake.siren()

    elif entity == "SIRET":
        val = fake.siret()

    elif entity == "VAT_NUMBER":
        val = "FR" + str(fake.random_number(digits=11))

    elif entity == "ADDRESS":
        val = fake.address().replace("\n", ", ")

    elif entity == "ZIP_CODE":
        val = fake.postcode()

    elif entity == "CITY":
        val = fake.city()

    elif entity == "EMAIL":
        val = fake.email()

    elif entity == "PHONE_NUMBER":
        val = fake.phone_number()

    elif entity == "IBAN":
        val = fake.iban()

    elif entity in ["REVENUE", "TAX_AMOUNT", "OTHER_INCOME"]:
        val = f"{fake.random_int(1000, 150000):,} €".replace(",", " ")

    else:
        val = f"<{entity}_{uuid.uuid4().hex[:6]}>"

    return val

# =====================================================
# DETECTION CAMEMBERT
# =====================================================
def detect_pii_camembert(text: str) -> List[Dict]:
    results = []
    entities = ner(text)

    for e in entities:
        mapped = CAMEMBERT_MAP.get(e["entity_group"])
        if not mapped:
            continue

        results.append({
            "entity_type": mapped,
            "start": e["start"],
            "end": e["end"],
            "text": e["word"]
        })

    return results

# =====================================================
# DETECTION REGEX
# =====================================================
def detect_pii_regex(text: str) -> List[Dict]:
    hits = []
    for entity, pattern in PII_REGEX.items():
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append({
                "entity_type": entity,
                "start": m.start(),
                "end": m.end(),
                "text": m.group()
            })
    return hits

# =====================================================
# MERGE DES SPANS
# =====================================================
def merge_spans(text: str) -> List[Dict]:
    spans = detect_pii_camembert(text) + detect_pii_regex(text)
    spans = sorted(spans, key=lambda x: x["start"], reverse=True)

    merged = []
    last_start = len(text)

    for s in spans:
        if s["end"] <= last_start:
            merged.append(s)
            last_start = s["start"]

    return merged

# =====================================================
# ENDPOINT PRINCIPAL
# =====================================================

FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.post("/anonymize")
async def anonymize(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only DOCX supported")

    doc = Document(file.file)
    mapping = {}

    for p in doc.paragraphs:
        if not p.text.strip():
            continue

        text = p.text
        spans = merge_spans(text)

        new_text = text
        for s in spans:
            original = s["text"]
            fake_val = fake_value(s["entity_type"], original)

            cipher = fernet.encrypt(original.encode()).decode()
            mapping[fake_val] = {
                "cipher": cipher,
                "entity": s["entity_type"]
            }

            new_text = new_text[:s["start"]] + fake_val + new_text[s["end"]:]

        p.text = new_text

    uid = uuid.uuid4().hex
    anon_file = f"note_fiscale_anonymisee_{uid}.docx"
    map_file = f"mapping_rgpd_{uid}.csv"

    anon_path = os.path.join(OUTPUT_DIR, anon_file)
    map_path = os.path.join(OUTPUT_DIR, map_file)

    doc.save(anon_path)

    pd.DataFrame(
        [{"fake": k, "cipher": v["cipher"], "entity": v["entity"]} for k, v in mapping.items()]
    ).to_csv(map_path, index=False)

    return {
        "anonymized_file": anon_file,
        "mapping_file": map_file
    }

# =====================================================
# DOWNLOAD
# =====================================================
@app.get("/download/{filename}")
def download(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, filename=filename)
