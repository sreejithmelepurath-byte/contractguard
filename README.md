# ContractGuard

**PDF in, plain-English red flags out.** An async FastAPI backend that reads a freelance contract (including messy scanned PDFs) and returns a short summary plus the clauses a freelancer should actually worry about.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)
![Tesseract](https://img.shields.io/badge/OCR-Tesseract-5A5A5A)

📄 **Case study:** [sreejithmelepurath-byte.github.io/MYPORTFOLIO](https://sreejithmelepurath-byte.github.io/MYPORTFOLIO/)

---

## The problem

A lawyer usually costs more than the contract is worth, so most freelancers just sign. That is how Net-90 payment terms, "unlimited revisions" and IP clauses broad enough to cover unrelated work slip through. ContractGuard is a first line of defence: it reads the contract before you sign and tells you, in plain English, what is worth a second look.

It catches things like:

- Payment terms of **Net-60/90** or longer
- **Unlimited revisions** with no scope boundary
- **IP transfer** that reaches beyond the delivered work
- **One-sided termination**, uncapped liability, broad non-competes

## How it works

```
PDF upload ──► PyMuPDF text extraction ──► (scanned page?) ──► Tesseract OCR
                                                   │
                                                   ▼
                     gpt-4o-mini, constrained system prompt, JSON mode
                                                   │
                                                   ▼
                     Pydantic validation ──► { summary, red_flags[] }
```

| Decision | Why | Implementation |
|---|---|---|
| Async pipeline | OCR + LLM calls take 10–30 s; a sync server would freeze | FastAPI async routes; blocking OCR runs via `asyncio.to_thread` |
| OCR fallback per page | Real contracts are scanned, rotated and messy | PyMuPDF rasterizes low-text pages, Tesseract reads them (`--psm 1` for orientation) |
| Structured output | The frontend needs predictable data, not a chat reply | JSON mode + strict Pydantic schema (`summary`, `red_flags[]` with category/severity) |
| Secrets & config | Keys never live in the codebase | `.env` + `pydantic-settings`; the app fails at startup if the key is missing |

## Quick start

```bash
# Tesseract is needed for scanned PDFs
#   macOS: brew install tesseract    Ubuntu: sudo apt install tesseract-ocr

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add your OPENAI_API_KEY
uvicorn app.main:app --reload
```

Open the interactive docs at <http://localhost:8000/docs>, or:

```bash
curl -F "file=@contract.pdf" http://localhost:8000/analyze
```

Or with Docker:

```bash
docker build -t contractguard .
docker run -p 8000:8000 --env-file .env contractguard
```

### Example response

```json
{
  "summary": "Design of a marketing website for a fixed fee, paid after delivery...",
  "red_flags": [
    {
      "category": "payment_terms",
      "severity": "high",
      "clause": "Payment is due Net-90 after invoice.",
      "explanation": "You would wait roughly three months to be paid for finished work."
    }
  ],
  "filename": "contract.pdf",
  "pages": 4,
  "ocr_pages": 1,
  "processing_seconds": 14.2,
  "disclaimer": "Informational analysis only - not a substitute for legal advice."
}
```

## Project structure

```
app/
├── main.py              # FastAPI app, /analyze and /health
├── config.py            # typed settings from .env
├── schemas.py           # request/response models
└── services/
    ├── extraction.py    # PyMuPDF + Tesseract OCR fallback
    └── analyzer.py      # OpenAI call, prompt, schema validation
tests/test_api.py        # endpoint + extraction tests (LLM mocked)
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The OpenAI call is mocked, so tests run offline and cost nothing. They also run on every push via GitHub Actions.

## Status

A working solo-built MVP, benchmarked locally rather than in production: about **10–30 s** per multi-page contract and an estimated **< $0.01** per scan with gpt-4o-mini. Next step: put it in front of real freelancers and learn which red flags they care about most.

> ⚠️ ContractGuard provides informational analysis only and is not a substitute for legal advice.

---

Built by **Sreejith Sreenivasan (Sree)** · [Portfolio](https://sreejithmelepurath-byte.github.io/MYPORTFOLIO/)
