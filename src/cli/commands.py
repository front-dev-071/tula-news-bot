from typing import Optional, List
from datetime import datetime
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from ..news.collector import NewsCollector
from ..news.models import NewsArticle
from ..core.config import config

# Создаем Typer приложение
app = typer.Typer(
    name="tula-news",
    help="Агент для сбора новостей по Тульской области",
    add_completion=False
)

console = Console()

# Инициализируем коллектор
collector = NewsCollector()


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
        
        # Собираем новости
        articles = collector.collect(query, limit)
        
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
    
    # Загружаем новости
    articles = collector.load_latest()
    
    if not articles:
        console.print("[red]Нет сохраненных новостей. Сначала выполните collect.[/red]")
        return
    
    # Сортируем
    if sort_by == "relevance":
        articles.sort(key=lambda x: x.relevance_score, reverse=True)
    elif sort_by == "source":
        articles.sort(key=lambda x: x.source)
    else:  # date
        articles.sort(key=lambda x: x.published_at, reverse=True)
    
    # Ограничиваем количество
    articles = articles[:limit]
    
    # Показываем
    _display_news_table(articles, "Сохраненные новости")


@app.command()
def stats():
    """Показать статистику"""
    
    json_files = list(config.storage_path.glob("news_*.json"))
    
    if not json_files:
        console.print("[yellow]Еще нет собранных новостей[/yellow]")
        return
    
    # Загружаем последний файл для детальной статистики
    articles = collector.load_latest()
    
    # Общая статистика
    table = Table(title="[bold cyan]📈 Общая статистика[/bold cyan]")
    table.add_column("Показатель", style="bold")
    table.add_column("Значение", style="green")
    
    table.add_row("Всего сборов", str(len(json_files)))
    table.add_row("Последний сбор", json_files[-1].stem.replace("news_", ""))
    table.add_row("Всего новостей", str(sum(len(json.load(open(f))["articles"]) for f in json_files)))
    table.add_row("Последних новостей", str(len(articles)))
    
    if articles:
        table.add_row("Источников", str(len(set(a.source for a in articles))))
        table.add_row("Первая новость", articles[-1].published_at.strftime("%d.%m.%Y"))
        table.add_row("Последняя новость", articles[0].published_at.strftime("%d.%m.%Y"))
    
    console.print(table)
    
    # Статистика по источникам
    if articles:
        from collections import Counter
        source_counts = Counter(article.source for article in articles)
        
        table = Table(title="[bold cyan]📊 По источникам[/bold cyan]")
        table.add_column("Источник", style="bold")
        table.add_column("Количество", style="green")
        
        for source, count in source_counts.most_common():
            table.add_row(source, str(count))
        
        console.print(table)


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