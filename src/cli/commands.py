from typing import Optional, List
from datetime import datetime
import json
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from ..news.models import NewsArticle
from ..services.news_service import NewsService
from ..core.config import config

# Создаем Typer приложение
app = typer.Typer(
    name="tula-news",
    help="Агент для сбора новостей по Тульской области",
    add_completion=False
)

console = Console()

# Инициализируем сервис
news_service = NewsService()


def _display_news_table(articles: List[NewsArticle], title: str = "Новости"):
    """Отображение новостей в красивой таблице"""
    
    # Создаем таблицу
    table = Table(
        title=f"[bold cyan]{title}[/bold cyan]",
        title_justify="left",
        show_header=True,
        header_style="bold magenta",
        border_style="blue"
    )
    
    # Добавляем колонки
    table.add_column("№", style="dim", width=4)
    table.add_column("Заголовок", style="bold", width=60)
    table.add_column("Источник", style="green", width=20)
    table.add_column("Дата", style="yellow", width=15)
    table.add_column("Релевантность", style="red", width=12)
    
    # Добавляем строки
    for i, article in enumerate(articles, 1):
        # Форматируем дату
        date_str = article.published_at.strftime("%d.%m.%Y")
        
        # Форматируем релевантность
        relevance = "🔴 Низкая"
        if article.relevance_score > 0.7:
            relevance = "🟢 Высокая"
        elif article.relevance_score > 0.4:
            relevance = "🟡 Средняя"
        
        # Обрезаем длинный заголовок
        title = article.title
        if len(title) > 80:
            title = title[:77] + "..."
        
        table.add_row(
            str(i),
            title,
            article.source,
            date_str,
            relevance
        )
    
    # Выводим таблицу
    console.print(table)
    
    # Выводим статистику
    console.print()
    stats_panel = Panel(
        f"[bold]Статистика:[/bold] {len(articles)} новостей | "
        f"Высокая релевантность: {sum(1 for a in articles if a.relevance_score > 0.7)} | "
        f"Последняя новость: {articles[0].published_at.strftime('%d.%m.%Y %H:%M') if articles else 'нет'}",
        title="[bold]📊 Статистика[/bold]",
        border_style="green"
    )
    console.print(stats_panel)


@app.command()
def collect(
    query: Optional[str] = typer.Option(
        None,
        "--query", "-q",
        help="Поисковый запрос (по умолчанию: Тульская область)"
    ),
    limit: int = typer.Option(
        10,
        "--limit", "-l",
        help="Количество новостей для сбора"
    ),
    show: bool = typer.Option(
        True,
        "--show/--no-show",
        help="Показать результат после сбора"
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Принудительно обновить без использования кэша"
    )
):
    """Собрать свежие новости"""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(
            description=f"[cyan]Ищу новости по запросу: {query or config.news.default_region}[/cyan]",
            total=None
        )
        
        # Собираем новости через сервис
        articles = news_service.collect_news(query, limit, force_refresh)
        
        progress.update(task, completed=True)
    
    if show and articles:
        _display_news_table(articles, "Собранные новости")
        
        # Ссылки на новости
        console.print("\n[bold]🔗 Ссылки на новости:[/bold]")
        for i, article in enumerate(articles[:5], 1):  # Показываем первые 5
            console.print(f"{i}. [link={article.url}]{article.title[:50]}...[/link]")
    
    return articles


@app.command()
def show(
    limit: int = typer.Option(
        10,
        "--limit", "-l",
        help="Количество новостей для показа"
    ),
    sort_by: str = typer.Option(
        "date",
        "--sort",
        help="Сортировка: date (дата), relevance (релевантность), source (источник)"
    )
):
    """Показать последние сохраненные новости"""
    
    # Загружаем новости через сервис
    articles = news_service.get_latest_news(limit)
    
    if not articles:
        console.print("[red]Нет сохраненных новостей. Сначала выполните collect.[/red]")
        return
    
    # Дополнительная сортировка если нужно
    if sort_by == "source":
        articles.sort(key=lambda x: x.source)
    # Сервис уже сортирует по релевантности и дате
    
    # Показываем
    _display_news_table(articles, "Сохраненные новости")


@app.command()
def stats():
    """Показать статистику"""
    
    # Получаем статистику через сервис
    stats_data = news_service.get_statistics()
    
    if "message" in stats_data:
        console.print(f"[yellow]{stats_data['message']}[/yellow]")
        return
    
    # Общая статистика
    table = Table(title="[bold cyan]📈 Общая статистика[/bold cyan]")
    table.add_column("Показатель", style="bold")
    table.add_column("Значение", style="green")
    
    table.add_row("Всего новостей", str(stats_data["total_articles"]))
    
    if "date_range" in stats_data:
        table.add_row("Период", f"{stats_data['date_range']['earliest'][:10]} - {stats_data['date_range']['latest'][:10]}")
    
    if "relevance" in stats_data:
        rel = stats_data["relevance"]
        table.add_row("Высокая релевантность", str(rel["high"]))
        table.add_row("Средняя релевантность", str(rel["medium"]))
        table.add_row("Низкая релевантность", str(rel["low"]))
    
    console.print(table)
    
    # Статистика по источникам
    if "sources" in stats_data and stats_data["sources"]:
        table = Table(title="[bold cyan]📊 По источникам[/bold cyan]")
        table.add_column("Источник", style="bold")
        table.add_column("Количество", style="green")
        
        for source, count in sorted(stats_data["sources"].items(), key=lambda x: x[1], reverse=True):
            table.add_row(source, str(count))
        
        console.print(table)
    
    # Статистика кэша
    if "cache" in stats_data:
        cache = stats_data["cache"]
        table = Table(title="[bold cyan]💾 Кэш[/bold cyan]")
        table.add_column("Параметр", style="bold")
        table.add_column("Значение", style="green")
        
        table.add_row("Файлов в кэше", str(cache.get("total_files", 0)))
        table.add_row("Актуальных файлов", str(cache.get("valid_files", 0)))
        table.add_row("Размер кэша", f"{cache.get('total_size_mb', 0)} MB")
        table.add_row("TTL", f"{cache.get('ttl_hours', 0)} ч")
        
        console.print(table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Поисковый запрос"),
    limit: int = typer.Option(10, "--limit", "-l", help="Лимит результатов"),
    min_relevance: float = typer.Option(0.0, "--min-relevance", help="Минимальная релевантность (0-1)")
):
    """Поиск новостей по запросу"""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(
            description=f"[cyan]Ищем новости: {query}[/cyan]",
            total=None
        )
        
        articles = news_service.search_news(query, limit, min_relevance)
        progress.update(task, completed=True)
    
    if articles:
        _display_news_table(articles, f"Результаты поиска: {query}")
    else:
        console.print(f"[yellow]Новостей по запросу '{query}' не найдено[/yellow]")


@app.command()
def export(
    format_type: str = typer.Option("json", "--format", "-f", help="Формат экспорта (json, csv, txt)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Количество новостей")
):
    """Экспорт новостей в файл"""
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task(
                description=f"[cyan]Экспортируем новости в {format_type}[/cyan]",
                total=None
            )
            
            filename = news_service.export_news(format_type, limit)
            progress.update(task, completed=True)
        
        console.print(f"[green]✅ Новости экспортированы в: {filename}[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка экспорта: {e}[/red]")


@app.command()
def clear_cache():
    """Очистить кэш новостей"""
    
    news_service.clear_cache()
    console.print("[green]✅ Кэш очищен[/green]")


@app.command()
def config_show():
    """Показать текущую конфигурацию"""
    
    panel = Panel.fit(
        f"[bold]Приложение:[/bold] {config.app_name}\n"
        f"[bold]Регион:[/bold] {config.news.default_region}\n"
        f"[bold]Лимит новостей:[/bold] {config.news.news_limit}\n"
        f"[bold]Язык:[/bold] {config.news.language}\n"
        f"[bold]Хранилище:[/bold] {config.storage_path}\n"
        f"[bold]Уровень логов:[/bold] {config.log_level}",
        title="[bold]⚙️ Конфигурация[/bold]",
        border_style="cyan"
    )
    
    console.print(panel)


if __name__ == "__main__":
    app()