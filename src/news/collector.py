from typing import List, Dict, Any
from datetime import datetime
import json
from pathlib import Path
from loguru import logger

from .models import NewsArticle
from .sources import NewsSourceFactory
from ..core.config import config


class NewsCollector:
    """Основной класс для сбора новостей"""
    
    def __init__(self, source_type: str = "google"):
        """Инициализация коллектора"""
        self.source = NewsSourceFactory.create_source(source_type)
        self.storage_path = config.storage_path
        logger.info(f"NewsCollector инициализирован с источником: {source_type}")
    
    def collect(self, query: str = None, limit: int = None) -> List[NewsArticle]:
        """Сбор новостей"""
        if query is None:
            query = config.news.default_region
        
        if limit is None:
            limit = config.news.news_limit
        
        logger.info(f"Начинаем сбор новостей. Запрос: '{query}', лимит: {limit}")
        
        # Получаем новости
        articles = self.source.fetch_news(query, limit)
        
        if articles:
            # Сохраняем в файл
            self._save_to_file(articles)
            logger.success(f"Собрано и сохранено {len(articles)} новостей")
        else:
            logger.warning("Новости не найдены")
        
        return articles
    
    def _save_to_file(self, articles: List[NewsArticle]):
        """Сохранение новостей в JSON файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.storage_path / f"news_{timestamp}.json"
        
        data = {
            "collected_at": datetime.now().isoformat(),
            "query": config.news.default_region,
            "total_count": len(articles),
            "articles": [article.to_dict() for article in articles]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Новости сохранены в {filename}")
    
    def load_latest(self) -> List[NewsArticle]:
        """Загрузка последних сохраненных новостей"""
        json_files = sorted(self.storage_path.glob("news_*.json"))
        
        if not json_files:
            logger.warning("Нет сохраненных новостей")
            return []
        
        latest_file = json_files[-1]
        logger.info(f"Загружаем новости из {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [NewsArticle.from_dict(article) for article in data["articles"]]