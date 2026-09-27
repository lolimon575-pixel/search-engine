# NOVA Search

Экспериментальный поисковик с технической проверкой сайтов и отдельным слоем подтверждения официальности.

## Локальный запуск
```
python -m venv .venv
pip install -r requirements.txt
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Открыть: http://127.0.0.1:8000/

## Render
Build: `pip install -r requirements.txt`
Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
Health: `/health`

NOVA сообщает результаты технических проверок и уровень подтверждения официальности на момент проверки. Это не гарантия безопасности, законности или добросовестности сайта.

Текущий MVP использует DuckDuckGo HTML и небольшой реестр официальных доменов.
