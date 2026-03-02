"""Unit tests for SmartBrevitySummarizer."""

from __future__ import annotations

from types import SimpleNamespace

from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.summarizers.smart_brevity import SmartBrevitySummarizer


def _job(*, language: str = "en") -> SummaryJob:
    return SummaryJob.from_payload(
        {
            "version": 1,
            "job_id": "job_1",
            "article_id": "art_1",
            "content_hash": "a" * 64,
            "language": language,
            "topic": "world",
            "summary_version": 1,
            "priority": "normal",
            "reprocess": False,
            "model_override": None,
            "created_at": "2026-02-27T12:00:00Z",
        }
    )


def _parse(summary: str, *, why_label: str = "Why it matters", bottom_label: str = "Bottom line") -> tuple[str, str, list[str], str]:
    lines = summary.splitlines()
    assert lines[0].startswith("📰 ")
    assert f"{why_label}: " in summary
    assert f"{bottom_label}: " in summary

    headline = lines[0].removeprefix("📰 ")
    why_line = next(line for line in lines if line.startswith(f"{why_label}: "))
    bottom_line = next(line for line in lines if line.startswith(f"{bottom_label}: "))
    bullets = [line.removeprefix("• ") for line in lines if line.startswith("• ")]
    return headline, why_line.removeprefix(f"{why_label}: "), bullets, bottom_line.removeprefix(f"{bottom_label}: ")


def test_smart_brevity_structure_and_selection_rules() -> None:
    summarizer = SmartBrevitySummarizer()
    article = RawArticle(
        content_hash="h1",
        article_id="a1",
        language="en",
        topic="world",
        source="Example",
        source_url="https://example.com/story",
        title="Regulators approve sweeping rule changes for global market oversight in 2026",
        content=(
            "<p>Officials approved a new regulation in 2026 to tighten oversight across the economy.</p> "
            "Audits will run every 30 days for listed firms through the first phase. "
            "Analysts said compliance costs could decrease by 12 percent in year one. "
            "Several industry groups requested phased deadlines for smaller companies. "
            "The agency will publish a final timeline after public consultation ends."
        ),
        published_at="2026-02-27T10:00:00Z",
        ingested_at="2026-02-27T10:05:00Z",
    )

    output = summarizer.summarize(article, _job())
    headline, why, bullets, bottom = _parse(output.summary)

    assert output.model_used == "smart_brevity_v1"
    assert len(headline) <= 140
    assert len(why) <= 160
    assert 1 <= len(bullets) <= 3
    assert all(len(bullet) <= 200 for bullet in bullets)
    assert len(bottom) <= 160
    assert "approved a new regulation in 2026" in why.lower()
    assert any(char.isdigit() for char in bullets[0])
    assert len(set(bullets)) == len(bullets)


def test_smart_brevity_truncates_headline_to_140_chars() -> None:
    summarizer = SmartBrevitySummarizer()
    article = RawArticle(
        content_hash="h2",
        article_id="a2",
        language="en",
        topic="technology",
        source="Example",
        source_url="https://example.com/story2",
        title="X" * 220,
        content="This is a sufficiently long sentence with 2026 data to trigger the main selection rule.",
        published_at="2026-02-27T10:00:00Z",
        ingested_at="2026-02-27T10:05:00Z",
    )

    output = summarizer.summarize(article, _job())
    headline, _, _, _ = _parse(output.summary)

    assert len(headline) <= 140
    assert headline.endswith("...")


def test_smart_brevity_never_raises_on_malformed_content() -> None:
    summarizer = SmartBrevitySummarizer()
    article = RawArticle(  # type: ignore[arg-type]
        content_hash="h3",
        article_id=None,
        language="en",
        topic="science",
        source="Example",
        source_url="https://example.com/story3",
        title=None,
        content=None,
        published_at="2026-02-27T10:00:00Z",
        ingested_at="2026-02-27T10:05:00Z",
    )

    output = summarizer.summarize(article, _job())
    headline, why, bullets, bottom = _parse(output.summary)

    assert headline
    assert why
    assert bullets
    assert bottom


def test_smart_brevity_supports_portuguese_labels_and_keywords() -> None:
    summarizer = SmartBrevitySummarizer()
    article = RawArticle(
        content_hash="h4",
        article_id="a4",
        language="pt",
        topic="economia",
        source="Exemplo",
        source_url="https://example.com/pt",
        title="Mercado reage após regulação aprovada no Brasil",
        content=(
            "O governo aprovou nova regulação para o mercado financeiro em 2026. "
            "As empresas terão 30 dias para cumprir a primeira fase das regras. "
            "Analistas dizem que o impacto inicial pode reduzir custos em 10 por cento. "
            "A implementação completa depende de nova decisão do tribunal."
        ),
        published_at="2026-02-27T10:00:00Z",
        ingested_at="2026-02-27T10:05:00Z",
    )

    output = summarizer.summarize(article, _job(language="pt"))
    headline, why, bullets, bottom = _parse(output.summary, why_label="Por que importa", bottom_label="Em resumo")

    assert headline
    assert why
    assert bullets
    assert bottom
    assert "regulação" in why.lower() or any(char.isdigit() for char in why)


def test_smart_brevity_defaults_to_english_for_unknown_language() -> None:
    summarizer = SmartBrevitySummarizer()
    article = RawArticle(
        content_hash="h5",
        article_id="a5",
        language="en",
        topic="world",
        source="Example",
        source_url="https://example.com/es",
        title="Court updates market guidance",
        content="The court issued new guidance to the market in 2026. Agencies will apply changes immediately.",
        published_at="2026-02-27T10:00:00Z",
        ingested_at="2026-02-27T10:05:00Z",
    )
    unknown_language_request = SimpleNamespace(language="es")

    output = summarizer.summarize(article, unknown_language_request)  # type: ignore[arg-type]

    assert "Why it matters: " in output.summary
    assert "Bottom line: " in output.summary
