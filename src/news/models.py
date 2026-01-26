from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class NewsCategory(str, Enum):
    """Категории новостей"""
    POLITICS = "politics"
    ECONOMY = "economy"
    SOCIETY = "society"
    INCIDENT = "incident"
    SPORT = "sport"
    CULTURE = "culture"
    OTHER = "other"


@dataclass
class NewsArticle:
    """Модель новостной статьи"""
    id: str
    title: str
    url: str
    source: str
    published_at: datetime
    content: Optional[str] = None
    summary: Optional[str] = None
    category: NewsCategory = NewsCategory.OTHER
    region: str = "Тульская область"
    relevance_score: float = 0.0  # 0-1, оценка релевантности
    
    def to_dict(self) -> dict:
        """Преобразование в словарь для сериализации"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "content": self.content,
            "summary": self.summary,
            "category": self.category.value,
            "region": self.region,
            "relevance_score": self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NewsArticle":
        """Создание из словаря"""
        return cls(
            id=data["id"],
            title=data["title"],
            url=data["url"],
            source=data["source"],
            published_at=datetime.fromisoformat(data["published_at"]),
            content=data.get("content"),
            summary=data.get("summary"),
            category=NewsCategory(data.get("category", "other")),
            region=data.get("region", "Тульская область"),
            relevance_score=data.get("relevance_score", 0.0)
        )