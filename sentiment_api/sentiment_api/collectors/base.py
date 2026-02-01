"""Base types for collectors."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawItem:
    """Raw discovered item from a source (AC-M1.2)."""

    source_id: str
    source_type: str  # gdelt, rss, api, scrape, dataset
    url: str
    published_at: datetime | None
    fetched_at: datetime
    title_raw: str
    content_raw: str = ""
    content_html: str = ""
    metadata: dict = field(default_factory=dict)
