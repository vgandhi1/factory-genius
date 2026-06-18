from pathlib import Path

from backend.app.rag_engine import ManualRAG

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bm25_retrieves_bearing_content():
    rag = ManualRAG(_REPO_ROOT / "data" / "knowledge")
    n = rag.load()
    assert n > 0
    ranked = rag.retrieve("bearing thermal pillow block shaft", top_k=3)
    assert ranked
    titles = " ".join(c.title.lower() for c, _ in ranked)
    assert "bearing" in titles or "shaft" in titles or "thermal" in titles
