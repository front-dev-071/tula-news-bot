import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import time

from src.news.sources import (
    retry_on_failure, 
    NetworkError, 
    TimeoutError, 
    ConnectionError,
    GoogleNewsSource,
    NewsSourceFactory
)
from src.news.models import NewsArticle


class TestRetryMechanism:
    """Тесты механизма повторных попыток"""
    
    def test_retry_on_success(self):
        """Тест успешного выполнения с первой попытки"""
        @retry_on_failure(max_attempts=3, delay=0.1)
        def success_function():
            return "success"
        
        result = success_function()
        assert result == "success"
    
    def test_retry_on_failure_then_success(self):
        """Тест повторных попыток с eventual success"""
        call_count = 0
        
        @retry_on_failure(max_attempts=3, delay=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 2
    
    def test_retry_max_attempts_reached(self):
        """Тест достижения максимального количества попыток"""
        @retry_on_failure(max_attempts=2, delay=0.1)
        def always_failing_function():
            raise NetworkError("Permanent failure")
        
        with pytest.raises(NetworkError, match="Permanent failure"):
            always_failing_function()
    
    def test_retry_specific_exceptions(self):
        """Тест повторных попыток только для определенных исключений"""
        @retry_on_failure(max_attempts=2, delay=0.1, exceptions=(TimeoutError,))
        def function_with_different_errors():
            raise ValueError("Different error type")
        
        # Должно вызвать ValueError без повторных попыток
        with pytest.raises(ValueError, match="Different error type"):
            function_with_different_errors()
    
    def test_retry_backoff_delay(self):
        """Тест экспоненциальной задержки"""
        call_times = []
        
        @retry_on_failure(max_attempts=3, delay=0.1, backoff=2.0)
        def delayed_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Retry needed")
            return "success"
        
        delayed_function()
        
        # Проверяем что задержки увеличиваются
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        # Вторая задержка должна быть примерно в 2 раза больше первой
        assert delay2 > delay1 * 1.5  # Небольшой допуск на погрешность


class TestNetworkErrors:
    """Тесты классов сетевых ошибок"""
    
    def test_network_error_inheritance(self):
        """Тест наследования NetworkError"""
        error = NetworkError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    def test_timeout_error_inheritance(self):
        """Тест наследования TimeoutError"""
        error = TimeoutError("Timeout occurred")
        assert isinstance(error, NetworkError)
        assert isinstance(error, Exception)
        assert str(error) == "Timeout occurred"
    
    def test_connection_error_inheritance(self):
        """Тест наследования ConnectionError"""
        error = ConnectionError("Connection failed")
        assert isinstance(error, NetworkError)
        assert isinstance(error, Exception)
        assert str(error) == "Connection failed"


class TestGoogleNewsSource:
    """Тесты GoogleNewsSource"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        # Мокируем конфигурацию
        self.mock_config = MagicMock()
        self.mock_config.news.language = "ru"
        
    @patch('src.news.sources.config')
    @patch('src.news.sources.GoogleNews')
    def test_source_initialization(self, mock_gn, mock_config):
        """Тест инициализации источника"""
        mock_config.news.language = "ru"
        
        source = GoogleNewsSource()
        
        mock_gn.assert_called_once_with(lang="ru", country='RU')
    
    @patch('src.news.sources.GoogleNews')
    def test_source_import_error(self, mock_gn):
        """Тест ошибки импорта GoogleNews"""
        mock_gn.side_effect = ImportError("Module not found")
        
        with pytest.raises(ImportError):
            GoogleNewsSource()
    
    @patch('src.news.sources.config')
    @patch('src.news.sources.GoogleNews')
    def test_fetch_news_success(self, mock_gn, mock_config):
        """Тест успешного получения новостей"""
        # Настраиваем моки
        mock_config.news.language = "ru"
        mock_config.news.default_region = "Тула"
        
        mock_gn_instance = MagicMock()
        mock_gn.return_value = mock_gn_instance
        
        # Мокируем ответ от Google News
        mock_stories = {
            'entries': [
                {
                    'title': 'Тестовая новость',
                    'link': 'https://example.com/news/1',
                    'source': {'title': 'Тестовый источник'},
                    'published': 'Mon, 01 Jan 2023 12:00:00 GMT',
                    'summary': 'Тестовое описание'
                }
            ]
        }
        mock_gn_instance.search.return_value = mock_stories
        
        # Тестируем
        source = GoogleNewsSource()
        articles = source.fetch_news("Тула", 10)
        
        # Проверяем
        assert len(articles) == 1
        assert articles[0].title == "Тестовая новость"
        assert articles[0].url == "https://example.com/news/1"
        assert articles[0].source == "Тестовый источник"
    
    @patch('src.news.sources.config')
    @patch('src.news.sources.GoogleNews')
    def test_fetch_news_timeout_error(self, mock_gn, mock_config):
        """Тест обработки таймаута"""
        mock_config.news.language = "ru"
        
        mock_gn_instance = MagicMock()
        mock_gn.return_value = mock_gn_instance
        mock_gn_instance.search.side_effect = Exception("timeout occurred")
        
        source = GoogleNewsSource()
        
        with pytest.raises(TimeoutError, match="Таймаут при поиске новостей"):
            source.fetch_news("Тула", 10)
    
    @patch('src.news.sources.config')
    @patch('src.news.sources.GoogleNews')
    def test_fetch_news_connection_error(self, mock_gn, mock_config):
        """Тест обработки ошибки подключения"""
        mock_config.news.language = "ru"
        
        mock_gn_instance = MagicMock()
        mock_gn.return_value = mock_gn_instance
        mock_gn_instance.search.side_effect = Exception("connection failed")
        
        source = GoogleNewsSource()
        
        with pytest.raises(ConnectionError, match="Ошибка подключения"):
            source.fetch_news("Тула", 10)
    
    def test_generate_id(self):
        """Тест генерации ID"""
        source = GoogleNewsSource.__new__(GoogleNewsSource)  # Создаем без инициализации
        
        id1 = source._generate_id("Title", "Source")
        id2 = source._generate_id("Title", "Source")
        id3 = source._generate_id("Different Title", "Source")
        
        assert id1 == id2  # Одинаковые данные - одинаковый ID
        assert id1 != id3  # Разные данные - разный ID
        assert len(id1) == 32  # MD5 хеш
    
    def test_parse_date_valid(self):
        """Тест парсинга валидной даты"""
        source = GoogleNewsSource.__new__(GoogleNewsSource)
        
        date_str = "Mon, 01 Jan 2023 12:00:00 GMT"
        parsed_date = source._parse_date(date_str)
        
        assert isinstance(parsed_date, datetime)
        assert parsed_date.year == 2023
        assert parsed_date.month == 1
        assert parsed_date.day == 1
    
    def test_parse_date_invalid(self):
        """Тест парсинга невалидной даты"""
        source = GoogleNewsSource.__new__(GoogleNewsSource)
        
        invalid_date = "invalid date string"
        parsed_date = source._parse_date(invalid_date)
        
        # Должна вернуться текущая дата
        assert isinstance(parsed_date, datetime)
    
    def test_calculate_relevance(self):
        """Тест вычисления релевантности"""
        source = GoogleNewsSource.__new__(GoogleNewsSource)
        
        # Тест с релевантными ключевыми словами
        entry = {
            'title': 'Новости Тульской области',
            'summary': 'События в Туле'
        }
        query = 'Тула, Тульская область'
        
        relevance = source._calculate_relevance(entry, query)
        
        assert relevance > 0  # Должна быть положительная релевантность
        assert relevance <= 1  # Не должна превышать 1


class TestNewsSourceFactory:
    """Тесты фабрики источников"""
    
    def test_create_google_source(self):
        """Тест создания Google источника"""
        with patch('src.news.sources.GoogleNewsSource'):
            source = NewsSourceFactory.create_source("google")
            assert source is not None
    
    def test_create_unknown_source(self):
        """Тест создания неизвестного источника"""
        with pytest.raises(ValueError, match="Неизвестный источник: unknown"):
            NewsSourceFactory.create_source("unknown")
