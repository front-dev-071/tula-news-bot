#!/usr/bin/env python3
"""Точка входа для новостного агента"""

import sys
from pathlib import Path

# Добавляем src в путь Python
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger
from src.cli.commands import app


def setup_logging():
    """Настройка логирования"""
    logger.remove()  # Удаляем стандартный обработчик
    
    # Добавляем красивый вывод в консоль
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Добавляем запись в файл
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    logger.add(
        log_path / "tula_news_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )


def main():
    """Основная функция"""
    setup_logging()
    logger.info("Запуск Tula News Agent")
    
    try:
        app()
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе приложения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()