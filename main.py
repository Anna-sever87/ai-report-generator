import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

from config import LOG_FILE, load_settings
from report_types import DEFAULT_TYPE, REPORT_TYPES, get_report_type
from utils.ai_processor import AIProcessingError, process_dialog_with_ai
from utils.pdf_generator import PDFGenerationError, build_output_path, generate_pdf, render_html

logger = logging.getLogger("main")


def setup_logging(level_name: str) -> None:
    """Журнал пишется и в консоль, и в файл report_generator.log."""
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )
    # Убираем лишние технические сообщения библиотек
    for noisy in ("httpx", "openai", "fontTools", "weasyprint"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def decode_bytes(raw: bytes) -> str:
    """Читает текст в самых частых кодировках Windows: UTF-8, UTF-16 и cp1251 (ANSI)."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1251")


def read_input(source: str) -> str:
    """Читает текст диалога из файла (или из стандартного ввода, если указан «-»)."""
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {source}")
    return decode_bytes(path.read_bytes())


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Client Report Generator: превращает текст диалога в PDF-отчёт."
    )
    parser.add_argument("input", nargs="?", help="путь к текстовому файлу с диалогом (или «-» для ввода с клавиатуры)")
    parser.add_argument(
        "--type", "-t", choices=sorted(REPORT_TYPES), default=DEFAULT_TYPE,
        help=f"тип отчёта (по умолчанию {DEFAULT_TYPE})",
    )
    parser.add_argument("--list-types", action="store_true", help="показать доступные типы отчётов и выйти")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    started = time.time()
    try:
        settings = load_settings()
    except RuntimeError as e:
        print(f"Ошибка настроек: {e}")
        return 1
    setup_logging(settings.log_level)
    report_type = get_report_type(args.type)
    source_name = "ввод с клавиатуры" if args.input == "-" else Path(args.input).name

    try:
        logger.info("Этап 1/4: чтение текста диалога (%s)", source_name)
        text = read_input(args.input).strip()
        if not text:
            raise ValueError("Файл с диалогом пустой.")
        if len(text) > settings.max_input_chars:
            raise ValueError(
                f"Текст слишком длинный ({len(text)} символов, максимум {settings.max_input_chars}). "
                "Сократите диалог или увеличьте MAX_INPUT_CHARS в .env."
            )
        logger.info("Прочитано символов: %s", len(text))

        logger.info("Этап 2/4: обработка диалога с помощью ИИ (тип отчёта: %s)", report_type.key)
        data = process_dialog_with_ai(text, report_type, settings)

        logger.info("Этап 3/4: подстановка данных в HTML-шаблон %s", report_type.template)
        html = render_html(report_type, data, source_name)

        logger.info("Этап 4/4: создание PDF")
        output_path = generate_pdf(html, build_output_path(report_type))
    except (FileNotFoundError, ValueError) as e:
        logger.error("%s", e)
        print(f"Ошибка: {e}")
        return 1
    except (AIProcessingError, PDFGenerationError) as e:
        logger.error("%s", e)
        print(f"Ошибка: {e}\nПодробности записаны в файл {LOG_FILE.name}")
        return 1
    except Exception as e:
        logger.exception("Непредвиденная ошибка")
        print(f"Непредвиденная ошибка: {e}\nПодробности записаны в файл {LOG_FILE.name}")
        return 1

    logger.info("Готово за %.1f с", time.time() - started)
    try:
        shown = output_path.relative_to(Path.cwd())
    except ValueError:
        shown = output_path
    print(f"Отчёт успешно создан: {shown}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.list_types:
        for report_type in REPORT_TYPES.values():
            print(f"{report_type.key}: {report_type.title}")
        return 0
    if not args.input:
        print("Укажите файл с диалогом, например: python main.py examples/example_dialog.txt")
        return 2
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
        return 130


if __name__ == "__main__":
    sys.exit(main())