from abc import ABC, abstractmethod
from typing import List, Optional
from loguru import logger

from .models import NewsArticle
from ..core.config import config


class NewsSource(ABC):
    """Абстрактный класс источника новостей"""
    
    @abstractmethod
    def fetch_news(self, query: Optional[str] = None, limit: int = 10) -> List[NewsArticle]:
        """Получение новостей из источника"""
        pass
    
    def _generate_id(self, title: str, source: str) -> str:
        """Генерация уникального ID для новости"""
        import hashlib
        text = f"{title}_{source}".encode('utf-8')
        return hashlib.md5(text).hexdigest()


class GoogleNewsSource(NewsSource):
    """Источник новостей из Google News"""
    
    def __init__(self):
        try:
            from pygooglenews import GoogleNews
            self.gn = GoogleNews(lang=config.news.language, country='RU')
            logger.info("Google News источник инициализирован")
        except ImportError:
            logger.error("PyGoogleNews не установлен. Установите: pip install pygooglenews")
            raise
    
    def fetch_news(self, query: Optional[str] = None, limit: int = 10) -> List[NewsArticle]:
        """Получение новостей из Google News"""
        if query is None:
            query = config.news.default_region
        
        logger.info(f"Ищем новости по запросу: {query}")
        
        try:
            stories = self.gn.search(query)
            articles = []
            
            for i, entry in enumerate(stories['entries'][:limit]):
                try:
                    article = NewsArticle(
                        id=self._generate_id(entry['title'], entry.get('source', {}).get('title', 'unknown')),
                        title=entry.get('title', ''),
                        url=entry.get('link', ''),
                        source=entry.get('source', {}).get('title', 'Unknown'),
                        published_at=self._parse_date(entry.get('published', '')),
                        summary=entry.get('summary', ''),
                        region=config.news.default_region,
                        relevance_score=self._calculate_relevance(entry, query)
                    )
                    articles.append(article)
                    logger.debug(f"Найдена новость: {article.title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Ошибка обработки новости: {e}")
                    continue
            
            logger.info(f"Найдено {len(articles)} новостей")
            return articles
            
        except Exception as e:
            logger.error(f"Ошибка при поиске новостей: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> datetime:
        """Парсинг даты из строки"""
        from dateutil import parser
        from datetime import datetime
        try:
            return parser.parse(date_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка парсинга даты '{date_str}': {e}")
            return datetime.now()
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге даты '{date_str}': {e}")
            return datetime.now()
    
    def _calculate_relevance(self, entry: dict, query: str) -> float:
        """Вычисление релевантности новости"""
        title: str = entry.get('title', '').lower()
        summary: str = entry.get('summary', '').lower()
        query_lower: str = query.lower()
        
        score: float = 0.0
        
        # Проверяем наличие ключевых слов
        keywords = ['тула', 'тульск', 'област']
        for keyword in keywords:
            if keyword in title or keyword in summary:
                score += 0.3
        
        # Проверяем точное совпадение региона
        if any(region in title or region in summary 
                for region in query_lower.split(',')):
            score += 0.4
        
        # Ограничиваем от 0 до 1
        return min(1.0, max(0.0, score))


class NewsSourceFactory:
    """Фабрика источников новостей"""
    
    @staticmethod
    def create_source(source_type: str = "google") -> NewsSource:
        """Создание источника новостей"""
        sources = {
            "google": GoogleNewsSource,
            # "ria": RIANewsSource,  # Можно добавить позже
            # "tula_specific": TulaNewsSource,  # Специфичный для Тулы
        }
        
        if source_type not in sources:
            raise ValueError(f"Неизвестный источник: {source_type}")
        
        return sources[source_type]()