import json
import sys
from pathlib import Path

# Ensure workspace root (parent of 'src') is on sys.path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.rag_pipeline import RAGPipeline


def test_pipeline_offline_basic(tmp_path: Path):
    # Create a small temp corpus
    d = tmp_path / "data"
    d.mkdir()
    (d / "a.txt").write_text("RAG retrieves documents. It reduces hallucinations.")
    (d / "b.txt").write_text("TF-IDF is a classic retrieval method using term weights.")

    pipe = RAGPipeline(d, use_openai=False)
    pipe.build()

    res = pipe.query("What does RAG do?", k=3)
    assert "answer" in res and "sources" in res
    assert any("a.txt" == s["doc"] for s in res["sources"])  # should hit the relevant file
    assert "RAG" in res["answer"] or "retriev" in res["answer"].lower()


def test_cli_import():
    # Ensure CLI imports without side effects
    import importlib

    m = importlib.import_module("src.app.cli")
    assert hasattr(m, "main")
