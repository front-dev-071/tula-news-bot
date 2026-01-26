from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from ..news.collector import NewsCollector
from ..news.models import NewsArticle
from ..core.config import config


class NewsService:
    """Сервисный слой для работы с новостями"""
    
    def __init__(self, use_cache: bool = True):
        """Инициализация сервиса"""
        self.collector = NewsCollector(use_cache=use_cache)
        logger.info("NewsService инициализирован")
    
    def collect_news(
        self, 
        query: Optional[str] = None, 
        limit: Optional[int] = None,
        force_refresh: bool = False
    ) -> List[NewsArticle]:
        """
        Сбор новостей с бизнес-логикой
        
        Args:
            query: Поисковый запрос
            limit: Лимит новостей
            force_refresh: Принудительное обновление
            
        Returns:
            Отфильтрованный список новостей
        """
        # Получаем новости из коллектора
        articles = self.collector.collect(query, limit, force_refresh)
        
        # Применяем бизнес-логику
        filtered_articles = self._filter_articles(articles)
        sorted_articles = self._sort_articles(filtered_articles)
        
        logger.info(f"Обработано {len(sorted_articles)} новостей")
        return sorted_articles
    
    def get_latest_news(self, limit: int = 10) -> List[NewsArticle]:
        """Получение последних новостей"""
        articles = self.collector.load_latest()
        return self._sort_articles(articles[:limit])
    
    def search_news(
        self, 
        query: str, 
        limit: int = 10,
        min_relevance: float = 0.0
    ) -> List[NewsArticle]:
        """
        Поиск новостей по критериям
        
        Args:
            query: Поисковый запрос
            limit: Лимит результатов
            min_relevance: Минимальная релевантность
            
        Returns:
            Найденные новости
        """
        # Собираем новости
        articles = self.collect_news(query, limit * 2)  # Берем больше для фильтрации
        
        # Фильтруем по релевантности
        filtered = [
            article for article in articles 
            if article.relevance_score >= min_relevance
        ]
        
        return filtered[:limit]
    
    def get_news_by_category(self, category: str, limit: int = 10) -> List[NewsArticle]:
        """Получение новостей по категории"""
        articles = self.get_latest_news(limit * 3)  # Берем больше для фильтрации
        
        filtered = [
            article for article in articles
            if article.category.value == category.lower()
        ]
        
        return filtered[:limit]
    
    def get_news_by_source(self, source: str, limit: int = 10) -> List[NewsArticle]:
        """Получение новостей по источнику"""
        articles = self.get_latest_news(limit * 3)
        
        filtered = [
            article for article in articles
            if source.lower() in article.source.lower()
        ]
        
        return filtered[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики по новостям"""
        articles = self.get_latest_news(100)  # Берем больше для статистики
        
        if not articles:
            return {"message": "Нет данных для статистики"}
        
        # Базовая статистика
        stats = {
            "total_articles": len(articles),
            "date_range": {
                "earliest": min(article.published_at for article in articles).isoformat(),
                "latest": max(article.published_at for article in articles).isoformat()
            },
            "sources": {},
            "categories": {},
            "relevance": {
                "high": sum(1 for a in articles if a.relevance_score > 0.7),
                "medium": sum(1 for a in articles if 0.4 < a.relevance_score <= 0.7),
                "low": sum(1 for a in articles if a.relevance_score <= 0.4)
            }
        }
        
        # Статистика по источникам
        for article in articles:
            source = article.source
            stats["sources"][source] = stats["sources"].get(source, 0) + 1
        
        # Статистика по категориям
        for article in articles:
            category = article.category.value
            stats["categories"][category] = stats["categories"].get(category, 0) + 1
        
        # Добавляем статистику кэша
        cache_stats = self.collector.get_cache_stats()
        if cache_stats:
            stats["cache"] = cache_stats
        
        return stats
    
    def _filter_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Фильтрация новостей по бизнес-правилам"""
        filtered = []
        
        for article in articles:
            # Исключаем статьи без заголовка
            if not article.title or len(article.title.strip()) < 5:
                continue
            
            # Исключаем слишком старые новости (больше 7 дней)
            days_old = (datetime.now() - article.published_at).days
            if days_old > 7:
                continue
            
            # Исключаем статьи с очень низкой релевантностью
            if article.relevance_score < 0.1:
                continue
            
            filtered.append(article)
        
        return filtered
    
    def _sort_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Сортировка новостей по релевантности и дате"""
        # Сортируем по релевантности (убывание), затем по дате (убывание)
        return sorted(
            articles, 
            key=lambda x: (x.relevance_score, x.published_at), 
            reverse=True
        )
    
    def clear_cache(self) -> None:
        """Очистка кэша"""
        self.collector.clear_cache()
    
    def export_news(
        self, 
        format_type: str = "json", 
        limit: int = 50
    ) -> str:
        """
        Экспорт новостей в различных форматах
        
        Args:
            format_type: Формат экспорта (json, csv, txt)
            limit: Лимит новостей
            
        Returns:
            Путь к экспортированному файлу
        """
        articles = self.get_latest_news(limit)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type.lower() == "json":
            return self._export_json(articles, timestamp)
        elif format_type.lower() == "csv":
            return self._export_csv(articles, timestamp)
        elif format_type.lower() == "txt":
            return self._export_txt(articles, timestamp)
        else:
            raise ValueError(f"Неподдерживаемый формат: {format_type}")
    
    def _export_json(self, articles: List[NewsArticle], timestamp: str) -> str:
        """Экспорт в JSON"""
        import json
        from pathlib import Path
        
        filename = config.storage_path / f"export_{timestamp}.json"
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_count": len(articles),
            "articles": [article.to_dict() for article in articles]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filename)
    
    def _export_csv(self, articles: List[NewsArticle], timestamp: str) -> str:
        """Экспорт в CSV"""
        import csv
        from pathlib import Path
        
        filename = config.storage_path / f"export_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Заголовок', 'URL', 'Источник', 'Дата', 'Категория', 
                'Релевантность', 'Регион'
            ])
            
            for article in articles:
                writer.writerow([
                    article.title,
                    article.url,
                    article.source,
                    article.published_at.strftime('%Y-%m-%d %H:%M:%S'),
                    article.category.value,
                    article.relevance_score,
                    article.region
                ])
        
        return str(filename)
    
    def _export_txt(self, articles: List[NewsArticle], timestamp: str) -> str:
        """Экспорт в текстовый формат"""
        from pathlib import Path
        
        filename = config.storage_path / f"export_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Экспорт новостей от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего новостей: {len(articles)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, article in enumerate(articles, 1):
                f.write(f"{i}. {article.title}\n")
                f.write(f"   Источник: {article.source}\n")
                f.write(f"   Дата: {article.published_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"   Релевантность: {article.relevance_score:.2f}\n")
                f.write(f"   URL: {article.url}\n")
                if article.summary:
                    f.write(f"   Краткое содержание: {article.summary}\n")
                f.write("-" * 80 + "\n\n")
        
        return str(filename)
