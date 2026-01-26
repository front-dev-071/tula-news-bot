import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config import load_config, NewsConfig, AppConfig


class TestConfig:
    """Тесты конфигурации"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_default_values(self):
        """Тест загрузки конфигурации с значениями по умолчанию"""
        with patch('src.core.config.Path') as mock_path:
            # Мокируем отсутствие .env файла
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.__str__ = lambda: ".env"
            
            config = load_config()
            
            assert isinstance(config, AppConfig)
            assert config.app_name == "TulaNewsAgent"
            assert config.log_level == "INFO"
            assert config.news.default_region == "Тула, Тульская область"
            assert config.news.news_limit == 10
            assert config.news.language == "ru"
            assert config.news.request_timeout == 30
    
    def test_load_config_with_env_file(self):
        """Тест загрузки конфигурации с .env файлом"""
        env_content = """
APP_NAME=CustomApp
LOG_LEVEL=DEBUG
DEFAULT_REGION=Москва
NEWS_LIMIT=20
LANGUAGE=en
REQUEST_TIMEOUT=60
STORAGE_PATH=/custom/path
"""
        
        env_file = Path(self.temp_dir) / ".env"
        env_file.write_text(env_content)
        
        with patch('src.core.config.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__str__ = lambda: str(env_file)
            
            with patch('src.core.config.load_dotenv') as mock_load:
                config = load_config()
                
                # Проверяем что load_dotenv был вызван
                mock_load.assert_called_once()
    
    def test_news_config_dataclass(self):
        """Тест NewsConfig dataclass"""
        news_config = NewsConfig(
            default_region="Тестовый регион",
            news_limit=15,
            language="en",
            request_timeout=45
        )
        
        assert news_config.default_region == "Тестовый регион"
        assert news_config.news_limit == 15
        assert news_config.language == "en"
        assert news_config.request_timeout == 45
    
    def test_app_config_dataclass(self):
        """Тест AppConfig dataclass"""
        app_config = AppConfig(
            app_name="TestApp",
            log_level="DEBUG",
            storage_path=Path("/test/path"),
            news=NewsConfig(default_region="Test")
        )
        
        assert app_config.app_name == "TestApp"
        assert app_config.log_level == "DEBUG"
        assert str(app_config.storage_path) == "/test/path"
        assert app_config.news.default_region == "Test"
    
    def test_app_config_post_init_creates_directory(self):
        """Тест что __post_init__ создает директорию"""
        test_path = Path(self.temp_dir) / "test_storage"
        
        # Убеждаемся что директория не существует
        assert not test_path.exists()
        
        # Создаем конфигурацию
        app_config = AppConfig(storage_path=test_path)
        
        # Проверяем что директория создана
        assert test_path.exists()
        assert test_path.is_dir()
    
    def test_config_storage_path_creation(self):
        """Тест создания директории хранения"""
        with patch('src.core.config.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.__str__ = lambda: ".env"
            
            # Мокируем mkdir
            mock_mkdir = MagicMock()
            mock_path.return_value.mkdir = mock_mkdir
            
            config = load_config()
            
            # Проверяем что mkdir был вызван
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
