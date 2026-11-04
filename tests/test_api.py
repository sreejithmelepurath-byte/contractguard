import fitz
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, get_analyzer
from app.schemas import AnalysisResult, RedFlag
from app.services.analyzer import AnalysisError, parse_result
from app.services.extraction import ExtractionError, extract_text

CONTRACT = (
    "SERVICE AGREEMENT. The Contractor shall design a marketing website. "
    "Payment is due Net-90 after invoice. The Contractor will provide unlimited revisions "
    "until the Client is satisfied. All intellectual property created by the Contractor during "
    "the term, whether or not related to this project, transfers to the Client."
)


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 800), text, fontsize=11)
    return doc.tobytes()


class FakeAnalyzer:
    async def analyze(self, text: str) -> AnalysisResult:
        assert "Net-90" in text
        return AnalysisResult(
            summary="Website design for a fixed scope.",
            red_flags=[
                RedFlag(
                    category="payment_terms",
                    severity="high",
                    clause="Payment is due Net-90 after invoice.",
                    explanation="You wait three months to be paid.",
                )
            ],
        )


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: Settings(openai_api_key="test-key")
    app.dependency_overrides[get_analyzer] = lambda: FakeAnalyzer()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_extract_text_reads_text_pdf():
    result = extract_text(make_pdf(CONTRACT))
    assert "Net-90" in result.text
    assert result.pages == 1
    assert result.ocr_pages == 0


def test_extract_text_rejects_garbage():
    with pytest.raises(ExtractionError):
        extract_text(b"not a pdf")


def test_analyze_endpoint_returns_flags(client):
    response = client.post("/analyze", files={"file": ("contract.pdf", make_pdf(CONTRACT), "application/pdf")})
    assert response.status_code == 200
    body = response.json()
    assert body["red_flags"][0]["category"] == "payment_terms"
    assert body["pages"] == 1
    assert "legal advice" in body["disclaimer"]


def test_analyze_rejects_non_pdf(client):
    response = client.post("/analyze", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415


def test_parse_result_rejects_bad_schema():
    with pytest.raises(AnalysisError):
        parse_result('{"summary": "x", "red_flags": [{"severity": "extreme"}]}')
