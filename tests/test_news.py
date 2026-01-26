import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.news.models import NewsArticle, NewsCategory
from src.news.cache import NewsCache


class TestNewsArticle:
    """Тесты модели NewsArticle"""
    
    def test_valid_article_creation(self):
        """Тест создания валидной статьи"""
        article = NewsArticle(
            id="test_id",
            title="Тестовая новость",
            url="https://example.com/news/1",
            source="Тестовый источник",
            published_at=datetime.now(),
            relevance_score=0.8
        )
        
        assert article.id == "test_id"
        assert article.title == "Тестовая новость"
        assert article.relevance_score == 0.8
        assert article.category == NewsCategory.OTHER
    
    def test_invalid_title_raises_error(self):
        """Тест ошибки при коротком заголовке"""
        with pytest.raises(ValueError, match="Заголовок должен содержать минимум 3 символа"):
            NewsArticle(
                id="test_id",
                title="XY",  # Слишком короткий
                url="https://example.com/news/1",
                source="Тестовый источник",
                published_at=datetime.now()
            )
    
    def test_invalid_url_raises_error(self):
        """Тест ошибки при невалидном URL"""
        with pytest.raises(ValueError, match="Некорректный URL"):
            NewsArticle(
                id="test_id",
                title="Тестовая новость",
                url="invalid_url",
                source="Тестовый источник",
                published_at=datetime.now()
            )
    
    def test_invalid_relevance_score_raises_error(self):
        """Тест ошибки при невалидной релевантности"""
        with pytest.raises(ValueError, match="Релевантность должна быть в диапазоне от 0 до 1"):
            NewsArticle(
                id="test_id",
                title="Тестовая новость",
                url="https://example.com/news/1",
                source="Тестовый источник",
                published_at=datetime.now(),
                relevance_score=1.5  # Слишком высокое значение
            )
    
    def test_to_dict_conversion(self):
        """Тест конвертации в словарь"""
        article = NewsArticle(
            id="test_id",
            title="Тестовая новость",
            url="https://example.com/news/1",
            source="Тестовый источник",
            published_at=datetime(2023, 1, 1, 12, 0, 0),
            category=NewsCategory.POLITICS,
            relevance_score=0.8
        )
        
        data = article.to_dict()
        
        assert data["id"] == "test_id"
        assert data["title"] == "Тестовая новость"
        assert data["category"] == "politics"
        assert data["published_at"] == "2023-01-01T12:00:00"
    
    def test_from_dict_creation(self):
        """Тест создания из словаря"""
        data = {
            "id": "test_id",
            "title": "Тестовая новость",
            "url": "https://example.com/news/1",
            "source": "Тестовый источник",
            "published_at": "2023-01-01T12:00:00",
            "category": "politics",
            "relevance_score": 0.8
        }
        
        article = NewsArticle.from_dict(data)
        
        assert article.id == "test_id"
        assert article.title == "Тестовая новость"
        assert article.category == NewsCategory.POLITICS
        assert article.relevance_score == 0.8
    
    def test_from_dict_with_missing_fields(self):
        """Тест создания из неполного словаря"""
        data = {
            "id": "test_id",
            "title": "Тестовая новость",
            "url": "https://example.com/news/1",
            "source": "Тестовый источник",
            "published_at": "2023-01-01T12:00:00"
        }
        
        article = NewsArticle.from_dict(data)
        
        assert article.id == "test_id"
        assert article.category == NewsCategory.OTHER  # Значение по умолчанию
        assert article.relevance_score == 0.0  # Значение по умолчанию


class TestNewsCache:
    """Тесты кэша новостей"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = NewsCache(cache_dir=Path(self.temp_dir), ttl_hours=1)
        
        # Создаем тестовые статьи
        self.test_articles = [
            NewsArticle(
                id="1",
                title="Первая новость",
                url="https://example.com/1",
                source="Источник 1",
                published_at=datetime.now(),
                relevance_score=0.8
            ),
            NewsArticle(
                id="2",
                title="Вторая новость",
                url="https://example.com/2",
                source="Источник 2",
                published_at=datetime.now(),
                relevance_score=0.6
            )
        ]
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_miss(self):
        """Тест отсутствия данных в кэше"""
        result = self.cache.get("test_query", 10)
        assert result is None
    
    def test_cache_put_and_get(self):
        """Тест сохранения и получения из кэша"""
        self.cache.put("test_query", 10, self.test_articles)
        
        result = self.cache.get("test_query", 10)
        
        assert result is not None
        assert len(result) == 2
        assert result[0].title == "Первая новость"
        assert result[1].title == "Вторая новость"
    
    def test_cache_expiration(self):
        """Тест истечения срока действия кэша"""
        # Создаем кэш с TTL 0 часов (сразу истекает)
        expired_cache = NewsCache(cache_dir=Path(self.temp_dir), ttl_hours=0)
        
        expired_cache.put("test_query", 10, self.test_articles)
        result = expired_cache.get("test_query", 10)
        
        assert result is None  # Кэш должен быть недействителен
    
    def test_cache_key_generation(self):
        """Тест генерации ключей кэша"""
        key1 = self.cache._get_cache_key("query", 10)
        key2 = self.cache._get_cache_key("query", 10)
        key3 = self.cache._get_cache_key("query", 20)
        
        assert key1 == key2  # Одинаковые параметры - одинаковый ключ
        assert key1 != key3  # Разные параметры - разный ключ
    
    def test_cache_clear(self):
        """Тест очистки кэша"""
        self.cache.put("test_query1", 10, self.test_articles)
        self.cache.put("test_query2", 10, self.test_articles)
        
        # Проверяем что файлы созданы
        cache_files = list(self.cache.cache_dir.glob("news_*.json"))
        assert len(cache_files) > 0
        
        # Очищаем кэш
        self.cache.clear()
        
        # Проверяем что файлы удалены
        cache_files = list(self.cache.cache_dir.glob("news_*.json"))
        assert len(cache_files) == 0
    
    def test_cache_stats(self):
        """Тест получения статистики кэша"""
        self.cache.put("test_query", 10, self.test_articles)
        
        stats = self.cache.get_stats()
        
        assert "total_files" in stats
        assert "valid_files" in stats
        assert "total_size_mb" in stats
        assert "ttl_hours" in stats
        assert stats["total_files"] == 1
        assert stats["valid_files"] == 1
    
    def test_cleanup_expired(self):
        """Тест очистки устаревших файлов"""
        # Создаем кэш с нулевым TTL
        expired_cache = NewsCache(cache_dir=Path(self.temp_dir), ttl_hours=0)
        
        # Добавляем данные (они сразу становятся устаревшими)
        expired_cache.put("test_query", 10, self.test_articles)
        
        # Проверяем что файлы есть
        cache_files = list(expired_cache.cache_dir.glob("news_*.json"))
        assert len(cache_files) == 1
        
        # Очищаем устаревшие
        expired_cache.cleanup_expired()
        
        # Проверяем что файлы удалены
        cache_files = list(expired_cache.cache_dir.glob("news_*.json"))
        assert len(cache_files) == 0
    
    def test_empty_articles_not_cached(self):
        """Тест что пустой список не кэшируется"""
        self.cache.put("test_query", 10, [])
        
        # Проверяем что файлы не созданы
        cache_files = list(self.cache.cache_dir.glob("news_*.json"))
        assert len(cache_files) == 0
