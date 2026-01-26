import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict
from loguru import logger

from .models import NewsArticle


class NewsCache:
    """Кэш для хранения результатов поиска новостей"""
    
    def __init__(self, cache_dir: Path = Path("storage/cache"), ttl_hours: int = 1):
        """
        Инициализация кэша
        
        Args:
            cache_dir: Директория для хранения кэша
            ttl_hours: Время жизни кэша в часах
        """
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Кэш инициализирован: {self.cache_dir}, TTL: {ttl_hours}ч")
    
    def _get_cache_key(self, query: str, limit: int) -> str:
        """Генерация ключа кэша"""
        key_data = f"{query}_{limit}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Путь к файлу кэша"""
        return self.cache_dir / f"news_{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Проверка актуальности кэша"""
        if not cache_path.exists():
            return False
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cached_at = datetime.fromisoformat(data.get('cached_at', ''))
            return datetime.now() - cached_at < self.ttl
            
        except Exception as e:
            logger.warning(f"Ошибка проверки кэша {cache_path}: {e}")
            return False
    
    def get(self, query: str, limit: int) -> Optional[List[NewsArticle]]:
        """
        Получение новостей из кэша
        
        Args:
            query: Поисковый запрос
            limit: Лимит новостей
            
        Returns:
            Список новостей или None если кэш отсутствует/устарел
        """
        cache_key = self._get_cache_key(query, limit)
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path):
            logger.debug(f"Кэш не найден или устарел: {query}")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = [NewsArticle.from_dict(article_data) for article_data in data['articles']]
            logger.info(f"Загружено {len(articles)} новостей из кэша: {query}")
            return articles
            
        except Exception as e:
            logger.error(f"Ошибка загрузки из кэша {cache_path}: {e}")
            return None
    
    def put(self, query: str, limit: int, articles: List[NewsArticle]) -> None:
        """
        Сохранение новостей в кэш
        
        Args:
            query: Поисковый запрос
            limit: Лимит новостей
            articles: Список новостей
        """
        if not articles:
            logger.debug("Нет новостей для кэширования")
            return
        
        cache_key = self._get_cache_key(query, limit)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cache_data = {
                'query': query,
                'limit': limit,
                'cached_at': datetime.now().isoformat(),
                'articles_count': len(articles),
                'articles': [article.to_dict() for article in articles]
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Сохранено {len(articles)} новостей в кэш: {query}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в кэш {cache_path}: {e}")
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        try:
            for cache_file in self.cache_dir.glob("news_*.json"):
                cache_file.unlink()
            logger.info("Кэш очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
    
    def cleanup_expired(self) -> None:
        """Очистка устаревших файлов кэша"""
        removed_count = 0
        try:
            for cache_file in self.cache_dir.glob("news_*.json"):
                if not self._is_cache_valid(cache_file):
                    cache_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Удалено {removed_count} устаревших файлов кэша")
                
        except Exception as e:
            logger.error(f"Ошибка очистки устаревшего кэша: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        try:
            cache_files = list(self.cache_dir.glob("news_*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            valid_files = sum(1 for f in cache_files if self._is_cache_valid(f))
            
            return {
                'total_files': len(cache_files),
                'valid_files': valid_files,
                'expired_files': len(cache_files) - valid_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': str(self.cache_dir),
                'ttl_hours': self.ttl.total_seconds() / 3600
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {e}")
            return {}
