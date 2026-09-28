"""Retired/redirect articles must never re-enter the automated audio queue."""
from scripts import ensure_explainers


def test_only_published_articles_are_audio_candidates(tmp_path, monkeypatch):
    blog = tmp_path / 'blog'
    blog.mkdir()
    pages = {
        'index.html': '<main>Library</main>',
        'published.html': '<main>Published research</main>',
        'retired.html': '<meta name="robots" content="noindex, follow"><main>Old article</main>',
        'moved.html': '<meta http-equiv="refresh" content="0; url=/new.html">',
    }
    for name, html in pages.items():
        (blog / name).write_text(html)
    monkeypatch.setattr(ensure_explainers, 'ROOT', tmp_path)
    assert [p.name for p in ensure_explainers.blogs()] == ['published.html']
