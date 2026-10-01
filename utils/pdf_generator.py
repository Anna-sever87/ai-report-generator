import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, select_autoescape
from weasyprint import HTML

from config import BASE_DIR, REPORTS_DIR, TEMPLATES_DIR
from report_types import NOT_SPECIFIED, ReportType

logger = logging.getLogger("pdf_generator")


class PDFGenerationError(Exception):
    """Не удалось подготовить HTML или сохранить PDF."""


def make_environment() -> Environment:
    """Окружение Jinja2. Автоэкранирование включено: текст от ИИ не может «сломать» HTML-разметку."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,  # опечатка в имени поля в шаблоне даст ошибку, а не пустое место
    )


def render_html(report_type: ReportType, data: Dict[str, Any], source_name: str) -> str:
    """Подставляет данные в HTML-шаблон отчёта."""
    try:
        template = make_environment().get_template(report_type.template)
        return template.render(
            title=report_type.title,
            disclaimer=report_type.disclaimer,
            not_specified=NOT_SPECIFIED,
            data=data,
            meta={
                "report_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "source_name": source_name,
            },
        )
    except TemplateError as e:
        raise PDFGenerationError(f"Ошибка в HTML-шаблоне {report_type.template}: {e}") from e


def build_output_path(report_type: ReportType) -> Path:
    """Имя файла вида report_client_2026-10-05_15-30-12.pdf в папке reports."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return REPORTS_DIR / f"report_{report_type.key}_{stamp}.pdf"


def generate_pdf(html: str, output_path: Path) -> Path:
    """Превращает готовый HTML в PDF-файл с помощью WeasyPrint."""
    try:
        HTML(string=html, base_url=str(BASE_DIR)).write_pdf(str(output_path))
    except PermissionError as e:
        raise PDFGenerationError(
            f"Нет доступа к файлу {output_path.name}. Возможно, он открыт в другой программе."
        ) from e
    except Exception as e:
        raise PDFGenerationError(f"Не удалось создать PDF: {e}") from e
    logger.info("PDF сохранён: %s", output_path)
    return output_path