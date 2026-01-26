from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum
from urllib.parse import urlparse
import re


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
    
    def __post_init__(self):
        """Валидация данных после инициализации"""
        self._validate()
    
    def _validate(self):
        """Базовая валидация полей"""
        if not self.title or len(self.title.strip()) < 3:
            raise ValueError("Заголовок должен содержать минимум 3 символа")
        
        if not self.url or not self._is_valid_url(self.url):
            raise ValueError(f"Некорректный URL: {self.url}")
        
        if not self.source or len(self.source.strip()) < 2:
            raise ValueError("Источник должен содержать минимум 2 символа")
        
        if not 0 <= self.relevance_score <= 1:
            raise ValueError("Релевантность должна быть в диапазоне от 0 до 1")
    
    def _is_valid_url(self, url: str) -> bool:
        """Проверка валидности URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
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
        """Создание из словаря с валидацией"""
        try:
            return cls(
                id=data.get("id", ""),
                title=data.get("title", ""),
                url=data.get("url", ""),
                source=data.get("source", ""),
                published_at=datetime.fromisoformat(data.get("published_at", datetime.now().isoformat())),
                content=data.get("content"),
                summary=data.get("summary"),
                category=NewsCategory(data.get("category", "other")),
                region=data.get("region", "Тульская область"),
                relevance_score=float(data.get("relevance_score", 0.0))
            )
        except Exception as e:
            # В случае ошибки создания с валидацией, пробуем создать с базовыми значениями
            return cls(
                id=data.get("id", "unknown"),
                title=data.get("title", "Без заголовка"),
                url=data.get("url", "https://example.com"),
                source=data.get("source", "Unknown"),
                published_at=datetime.now(),
                relevance_score=0.0
            )