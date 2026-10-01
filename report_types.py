from dataclasses import dataclass
from typing import Any, Dict, Tuple

TEXT = "text"   # поле со строкой
LIST = "list"   # поле со списком строк
NOT_SPECIFIED = "Не указано"


@dataclass(frozen=True)
class Field:
    """Поле структурированных данных: единое имя, тип и описание для ИИ."""
    key: str
    description: str
    kind: str = TEXT


@dataclass(frozen=True)
class ReportType:
    key: str          # короткое имя типа (для командной строки)
    title: str        # заголовок отчёта в PDF
    template: str     # имя HTML-шаблона из папки templates
    role: str         # кем выступает ИИ при разборе текста
    disclaimer: str   # примечание в конце отчёта
    fields: Tuple[Field, ...]


COMMON_DISCLAIMER = (
    "Отчёт сформирован автоматически с помощью ИИ по тексту диалога. "
    "Данные могут содержать неточности, поэтому перед использованием их стоит проверить."
)

REPORT_TYPES: Dict[str, ReportType] = {
    "client": ReportType(
        key="client",
        title="Отчёт по диалогу с клиентом",
        template="report_client.html",
        role="аналитик, который готовит отчёты по разговорам с клиентами",
        disclaimer=COMMON_DISCLAIMER,
        fields=(
            Field("client_name", "имя клиента или название компании"),
            Field("topic", "тема разговора, одной короткой фразой"),
            Field("summary", "краткое резюме разговора в 2-3 предложениях"),
            Field("main_request", "основной запрос клиента"),
            Field("mood", "настроение клиента: одно-два слова и короткое пояснение"),
            Field("desired_deadline", "желаемые сроки"),
            Field("budget", "бюджет или желаемая стоимость"),
            Field("key_requirements", "основные пожелания: что точно должно быть в финальном продукте", LIST),
            Field("next_steps", "рекомендуемые следующие шаги", LIST),
        ),
    ),
    "interview": ReportType(
        key="interview",
        title="Отчёт по собеседованию с кандидатом",
        template="report_interview.html",
        role="HR-аналитик, который готовит отчёты по собеседованиям",
        disclaimer=(
            COMMON_DISCLAIMER
            + " Предварительная оценка не заменяет решение специалиста по подбору персонала."
        ),
        fields=(
            Field("candidate_name", "имя кандидата"),
            Field("position", "должность, на которую проходит собеседование"),
            Field("summary", "краткое резюме собеседования в 2-3 предложениях"),
            Field("experience", "релевантный опыт работы кандидата"),
            Field("key_skills", "ключевые навыки кандидата, названные в разговоре", LIST),
            Field("strengths", "сильные стороны кандидата", LIST),
            Field("concerns", "возможные риски и вопросы, которые стоит уточнить", LIST),
            Field("salary_expectations", "зарплатные ожидания кандидата"),
            Field("availability", "когда кандидат может приступить к работе"),
            Field("recommendation", "предварительная рекомендация (продолжить процесс, отказать или уточнить) с кратким обоснованием"),
            Field("next_steps", "рекомендуемые следующие шаги", LIST),
        ),
    ),
}

DEFAULT_TYPE = "client"


def get_report_type(key: str) -> ReportType:
    try:
        return REPORT_TYPES[key]
    except KeyError:
        raise ValueError(f"Неизвестный тип отчёта «{key}». Доступные типы: {', '.join(REPORT_TYPES)}.")


def _to_text(value: Any) -> str:
    if value is None:
        return NOT_SPECIFIED
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(item).strip() for item in value if item is not None and str(item).strip())
    text = str(value).strip()
    return text or NOT_SPECIFIED


def _to_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    text = str(value).strip()
    return [text] if text and text != NOT_SPECIFIED else []


def normalize(report_type: ReportType, data: Dict[str, Any]) -> Dict[str, Any]:
    """Приводит ответ ИИ к предсказуемой структуре: все поля на месте, типы верные, лишнее отброшено."""
    result: Dict[str, Any] = {}
    for field in report_type.fields:
        value = data.get(field.key)
        result[field.key] = _to_list(value) if field.kind == LIST else _to_text(value)
    return result