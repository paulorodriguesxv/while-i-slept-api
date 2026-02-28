"""Feed registry: language -> topic -> list of RSS feeds."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from while_i_slept_api.content.models import FeedDefinition
from while_i_slept_api.content.topics import validate_topic


class FeedRegistryError(ValueError):
    """Base error for feed registry resolution."""


class UnsupportedLanguageError(FeedRegistryError):
    """Raised when the registry has no feeds for the requested language."""


class FeedRegistry:
    """In-memory registry of allowed feeds per language/topic."""

    def __init__(
        self,
        registry: Mapping[str, Mapping[str, Sequence[FeedDefinition]]] | None = None,
    ) -> None:
        source = registry or DEFAULT_FEED_REGISTRY
        self._registry: dict[str, dict[str, tuple[FeedDefinition, ...]]] = {
            lang: {topic: tuple(feeds) for topic, feeds in topics.items()}
            for lang, topics in source.items()
        }

    def languages(self) -> tuple[str, ...]:
        """Return supported languages in stable sorted order."""

        return tuple(sorted(self._registry))

    def resolve(self, language: str, topic: str) -> tuple[FeedDefinition, ...]:
        """Resolve feeds for a language/topic pair."""

        validate_topic(topic)
        language_bucket = self._registry.get(language)
        if language_bucket is None:
            raise UnsupportedLanguageError(f"Unsupported language: {language}")
        return tuple(language_bucket.get(topic, ()))


DEFAULT_FEED_REGISTRY: dict[str, dict[str, tuple[FeedDefinition, ...]]] = {
    "en": {
        "world": (
            FeedDefinition(url="https://feeds.bbci.co.uk/news/world/rss.xml", source_name="BBC World"),
        ),
        "technology": (
            FeedDefinition(url="https://feeds.arstechnica.com/arstechnica/technology-lab", source_name="Ars Technica"),
        ),
        "business": (
            FeedDefinition(url="https://feeds.reuters.com/reuters/businessNews", source_name="Reuters Business"),
        ),
        "science": (
            FeedDefinition(url="https://www.sciencedaily.com/rss/top/science.xml", source_name="ScienceDaily"),
        ),
        "sports": (
            FeedDefinition(url="https://feeds.bbci.co.uk/sport/rss.xml?edition=uk", source_name="BBC Sport"),
        ),
        "finance": (
            FeedDefinition(
                url="https://www.infomoney.com.br/feed/",
                source_name="InfoMoney"
            ),
        )
    },
    "pt": {
        "world": (
            FeedDefinition(
                url="https://g1.globo.com/dynamo/mundo/rss2.xml",
                source_name="G1 Mundo"
            ),
        ),
        "technology": (
            FeedDefinition(
                url="https://g1.globo.com/dynamo/tecnologia/rss2.xml",
                source_name="G1 Tecnologia"
            ),
        ),
        "finance": (
            FeedDefinition(
                url="https://www.infomoney.com.br/feed/",
                source_name="InfoMoney"
            ),
        ),
        "science": (
            FeedDefinition(
                url="https://g1.globo.com/dynamo/ciencia-e-saude/rss2.xml",
                source_name="G1 Ciência"
            ),
        ),
        "sports": (
            FeedDefinition(
                url="https://g1.globo.com/dynamo/esportes/rss2.xml",
                source_name="G1 Esportes"
            ),
        ),
    },
}
