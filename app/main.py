"""ContractGuard API - upload a contract PDF, get plain-English red flags back."""
import asyncio
import time

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.schemas import AnalysisResponse
from app.services.analyzer import AnalysisError, ContractAnalyzer
from app.services.extraction import ExtractionError, extract_text

app = FastAPI(
    title="ContractGuard",
    description="Reads a freelance contract PDF and flags the clauses worth worrying about.",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET"], allow_headers=["*"])


def get_analyzer(settings: Settings = Depends(get_settings)) -> ContractAnalyzer:
    return ContractAnalyzer(settings.openai_api_key, settings.openai_model, settings.max_contract_chars)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_contract(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    analyzer: ContractAnalyzer = Depends(get_analyzer),
) -> AnalysisResponse:
    started = time.perf_counter()

    if file.content_type not in ("application/pdf", "application/octet-stream") and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        # OCR is blocking and CPU-bound: run it off the event loop so the
        # server keeps answering other requests while a scan is processed.
        extracted = await asyncio.to_thread(
            extract_text, data, settings.ocr_dpi, settings.ocr_min_chars_per_page
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = await analyzer.analyze(extracted.text)
    except AnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalysisResponse(
        **result.model_dump(),
        filename=file.filename or "contract.pdf",
        pages=extracted.pages,
        ocr_pages=extracted.ocr_pages,
        processing_seconds=round(time.perf_counter() - started, 2),
    )
