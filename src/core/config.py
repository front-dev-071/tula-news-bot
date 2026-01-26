import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class NewsConfig:
    """Конфигурация для сбора новостей"""
    default_region: str = "Тула, Тульская область"
    news_limit: int = 10
    language: str = "ru"
    request_timeout: int = 30


@dataclass
class AppConfig:
    """Основная конфигурация приложения"""
    app_name: str = "TulaNewsAgent"
    log_level: str = "INFO"
    storage_path: Path = Path("storage/news_data")
    news: NewsConfig = field(default_factory=NewsConfig)  # Используем default_factory!


class Config:
    """Загрузчик конфигурации"""
    
    _instance: Optional["Config"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Загрузка конфигурации из .env файла"""
        # Загружаем .env файл
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Создаем пример .env файла, если его нет
            self._create_env_example()
        
        # Создаем конфигурацию
        self.app = AppConfig(
            app_name=os.getenv("APP_NAME", "TulaNewsAgent"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            storage_path=Path(os.getenv("STORAGE_PATH", "storage/news_data")),
            news=NewsConfig(
                default_region=os.getenv("DEFAULT_REGION", "Тула, Тульская область"),
                news_limit=int(os.getenv("NEWS_LIMIT", "10")),
                language=os.getenv("LANGUAGE", "ru"),
                request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30"))
            )
        )
        
        # Создаем необходимые директории
        self.app.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _create_env_example(self):
        """Создание примера .env файла"""
        example_content = """# Настройки приложения
APP_NAME=TulaNewsAgent
LOG_LEVEL=INFO

# Настройки новостей
DEFAULT_REGION=Тула, Тульская область
NEWS_LIMIT=10
LANGUAGE=ru
REQUEST_TIMEOUT=30

# Хранилище
STORAGE_PATH=storage/news_data
"""
        with open(".env.example", "w", encoding="utf-8") as f:
            f.write(example_content)
        print("Создан файл .env.example. Скопируйте его в .env для настройки.")
    
    @property
    def settings(self) -> AppConfig:
        """Получение настроек"""
        return self.app


# Глобальный объект конфигурации
config = Config().settings