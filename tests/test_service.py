import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.services.news_service import NewsService
from src.news.models import NewsArticle, NewsCategory


class TestNewsService:
    """Тесты новостного сервиса"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.service = NewsService(use_cache=False)  # Отключаем кэш для тестов
        
        # Создаем тестовые статьи
        self.test_articles = [
            NewsArticle(
                id="1",
                title="Высокорелевантная новость о Туле",
                url="https://example.com/1",
                source="Источник 1",
                published_at=datetime.now(),
                relevance_score=0.9,
                category=NewsCategory.POLITICS
            ),
            NewsArticle(
                id="2",
                title="Низкорелевантная новость",
                url="https://example.com/2",
                source="Источник 2",
                published_at=datetime.now(),
                relevance_score=0.2,
                category=NewsCategory.OTHER
            ),
            NewsArticle(
                id="3",
                title="Короткая",  # Слишком короткий заголовок
                url="https://example.com/3",
                source="Источник 3",
                published_at=datetime.now(),
                relevance_score=0.8
            )
        ]
    
    @patch('src.services.news_service.NewsCollector')
    def test_collect_news_success(self, mock_collector_class):
        """Тест успешного сбора новостей"""
        # Настраиваем мок коллектора
        mock_collector = MagicMock()
        mock_collector.collect.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        result = service.collect_news("Тула", 10)
        
        # Проверяем что коллектор был вызван
        mock_collector.collect.assert_called_once_with("Тула", 10, False)
        
        # Проверяем фильтрацию (короткая новость должна быть отфильтрована)
        assert len(result) == 2
        assert all(article.title != "Короткая" for article in result)
    
    @patch('src.services.news_service.NewsCollector')
    def test_collect_news_with_force_refresh(self, mock_collector_class):
        """Тест принудительного обновления"""
        mock_collector = MagicMock()
        mock_collector.collect.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        service.collect_news("Тула", 10, force_refresh=True)
        
        mock_collector.collect.assert_called_once_with("Тула", 10, True)
    
    @patch('src.services.news_service.NewsCollector')
    def test_get_latest_news(self, mock_collector_class):
        """Тест получения последних новостей"""
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        result = service.get_latest_news(10)
        
        mock_collector.load_latest.assert_called_once()
        
        # Проверяем что результаты отсортированы по релевантности
        assert len(result) == 2  # После фильтрации
        assert result[0].relevance_score >= result[1].relevance_score
    
    @patch('src.services.news_service.NewsCollector')
    def test_search_news(self, mock_collector_class):
        """Тест поиска новостей"""
        mock_collector = MagicMock()
        mock_collector.collect.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        result = service.search_news("Тула", 10, min_relevance=0.5)
        
        # Проверяем что отфильтрованы новости с низкой релевантностью
        assert len(result) == 1
        assert result[0].relevance_score >= 0.5
    
    @patch('src.services.news_service.NewsCollector')
    def test_get_news_by_category(self, mock_collector_class):
        """Тест получения новостей по категории"""
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        result = service.get_news_by_category("politics", 10)
        
        # Проверяем что отфильтрованы по категории
        assert len(result) == 1
        assert result[0].category == NewsCategory.POLITICS
    
    @patch('src.services.news_service.NewsCollector')
    def test_get_news_by_source(self, mock_collector_class):
        """Тест получения новостей по источнику"""
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        result = service.get_news_by_source("Источник 1", 10)
        
        # Проверяем что отфильтрованы по источнику
        assert len(result) == 1
        assert "Источник 1" in result[0].source
    
    @patch('src.services.news_service.NewsCollector')
    def test_get_statistics(self, mock_collector_class):
        """Тест получения статистики"""
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector.get_cache_stats.return_value = {
            "total_files": 1,
            "valid_files": 1,
            "total_size_mb": 0.5
        }
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        stats = service.get_statistics()
        
        assert "total_articles" in stats
        assert "sources" in stats
        assert "categories" in stats
        assert "relevance" in stats
        assert "cache" in stats
        
        assert stats["total_articles"] == 2  # После фильтрации
        assert stats["relevance"]["high"] == 1
        assert stats["relevance"]["low"] == 1
    
    @patch('src.services.news_service.NewsCollector')
    def test_get_statistics_empty(self, mock_collector_class):
        """Тест статистики при отсутствии данных"""
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = []
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        stats = service.get_statistics()
        
        assert "message" in stats
    
    @patch('src.services.news_service.NewsCollector')
    def test_clear_cache(self, mock_collector_class):
        """Тест очистки кэша"""
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=True)
        service.clear_cache()
        
        mock_collector.clear_cache.assert_called_once()
    
    @patch('src.services.news_service.NewsCollector')
    @patch('src.services.news_service.config')
    def test_export_news_json(self, mock_config, mock_collector_class):
        """Тест экспорта в JSON"""
        mock_config.storage_path = "/tmp/test"
        
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                result = service.export_news("json", 10)
                
                assert result.endswith('.json')
                mock_open.assert_called_once()
                mock_dump.assert_called_once()
    
    @patch('src.services.news_service.NewsCollector')
    @patch('src.services.news_service.config')
    def test_export_news_csv(self, mock_config, mock_collector_class):
        """Тест экспорта в CSV"""
        mock_config.storage_path = "/tmp/test"
        
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('csv.writer') as mock_writer:
                result = service.export_news("csv", 10)
                
                assert result.endswith('.csv')
                mock_open.assert_called_once()
                mock_writer.assert_called_once()
    
    @patch('src.services.news_service.NewsCollector')
    @patch('src.services.news_service.config')
    def test_export_news_txt(self, mock_config, mock_collector_class):
        """Тест экспорта в TXT"""
        mock_config.storage_path = "/tmp/test"
        
        mock_collector = MagicMock()
        mock_collector.load_latest.return_value = self.test_articles
        mock_collector_class.return_value = mock_collector
        
        service = NewsService(use_cache=False)
        
        with patch('builtins.open', create=True) as mock_open:
            result = service.export_news("txt", 10)
            
            assert result.endswith('.txt')
            mock_open.assert_called_once()
    
    def test_export_news_invalid_format(self):
        """Тест экспорта в неподдерживаемом формате"""
        service = NewsService(use_cache=False)
        
        with pytest.raises(ValueError, match="Неподдерживаемый формат: xml"):
            service.export_news("xml", 10)
    
    def test_filter_articles(self):
        """Тест фильтрации статей"""
        # Создаем статьи с разными характеристиками
        old_article = NewsArticle(
            id="old",
            title="Старая новость",
            url="https://example.com/old",
            source="Источник",
            published_at=datetime.now().replace(year=2020),  # Старая новость
            relevance_score=0.8
        )
        
        low_relevance_article = NewsArticle(
            id="low",
            title="Новость с низкой релевантностью",
            url="https://example.com/low",
            source="Источник",
            published_at=datetime.now(),
            relevance_score=0.05  # Очень низкая релевантность
        )
        
        all_articles = self.test_articles + [old_article, low_relevance_article]
        
        filtered = self.service._filter_articles(all_articles)
        
        # Проверяем что отфильтрованы неподходящие статьи
        assert len(filtered) == 2  # Только валидные статьи
        assert all(len(article.title) >= 5 for article in filtered)
        assert all(article.relevance_score >= 0.1 for article in filtered)
    
    def test_sort_articles(self):
        """Тест сортировки статей"""
        unsorted_articles = [
            NewsArticle("3", "CCC", "https://example.com/3", "source", datetime.now(), relevance_score=0.3),
            NewsArticle("1", "AAA", "https://example.com/1", "source", datetime.now(), relevance_score=0.9),
            NewsArticle("2", "BBB", "https://example.com/2", "source", datetime.now(), relevance_score=0.7)
        ]
        
        sorted_articles = self.service._sort_articles(unsorted_articles)
        
        # Проверяем сортировку по релевантности (убывание)
        assert sorted_articles[0].relevance_score == 0.9
        assert sorted_articles[1].relevance_score == 0.7
        assert sorted_articles[2].relevance_score == 0.3
