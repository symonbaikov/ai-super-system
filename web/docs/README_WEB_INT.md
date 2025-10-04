# WEB Interface Parser (build 2025-09-28)
Это автономный пакет, собранный из документов:
- 'Веб Инт.Парсер 18.09 последний(обновленный).docx'
- 'инструкция.docx'

## Структура
- configs/ui_config.json — страницы, кнопки, фильтры (извлечено из .docx, при отсутствии — дефолт).
- configs/parser_rules.json — источники, лимиты, дедуп, алерты.
- docs/raw_sources/ — исходные документы .docx без изменений.
- web/index.html — минимальный прототип интерфейса.
- src/main.py — заглушка API (FastAPI), совместимая с api_spec.md.
- scripts/validate_config.py — базовая проверка конфигов.

## Быстрый старт
python -m pip install fastapi uvicorn pydantic
python src/main.py
Открой 'web/index.html' (локально) или подними любой статический сервер.

## Импорт в основную систему
Скопируйте 'configs/*.json' и 'docs/ui_spec.md' в соответствующие каталоги v6.
