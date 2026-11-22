\# Digital Dean API — Практична робота №1



Навчальна реалізація базового API інформаційної системи «Цифровий деканат» на FastAPI.



\*\*Індивідуальний варіант:\*\* №3 (`academic\_status`).



\## Технології



\- Python 3.12+

\- FastAPI

\- Pydantic 2

\- Uvicorn

\- pytest

\- Postman Collection 2.1



\## Запуск проєкту



Створення віртуального середовища:



```powershell

python -m venv .venv

```



Активація у Windows PowerShell:



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



Встановлення залежностей:



```powershell

python -m pip install -e ".\[dev]"

```



Запуск тестів:



```powershell

python -m pytest -q

```



Запуск сервера:



```powershell

python -m uvicorn app.main:app --reload

```



\## Документація API



\- Swagger UI: http://127.0.0.1:8000/docs

\- OpenAPI: http://127.0.0.1:8000/openapi.json

\- Перевірка стану: http://127.0.0.1:8000/health



\## Реалізовані маршрути



| Метод | Шлях | Призначення |

|---|---|---|

| GET | `/health` | Перевірка готовності API |

| POST | `/api/v1/students` | Створення студента |

| GET | `/api/v1/students` | Отримання списку студентів |

| GET | `/api/v1/students/{student\_id}` | Отримання студента за UUID |

| PATCH | `/api/v1/students/{student\_id}` | Часткове оновлення студента |



Для списку студентів передбачений необов'язковий фільтр `academic\_status`.



\## Індивідуальний варіант №3 — academic\_status



Поле `academic\_status` визначає навчальний статус студента.



Допустимі значення:



\- `active` — навчається;

\- `academic\_leave` — академічна відпустка;

\- `expelled` — відрахований;

\- `graduated` — завершив навчання.



Приклад фільтрації:



```text

GET /api/v1/students?academic\_status=active

```



\## Обробка помилок



\- `404` — запис не знайдено;

\- `409` — електронна адреса вже використовується;

\- `422` — некоректні вхідні дані.



\## Структура зберігання даних



У цій навчальній реалізації використовується сховище в оперативній пам'яті. Дані зникають після перезапуску сервера.



Використовуються синтетичні дані. Проєкт не призначений для обробки реальних персональних даних.



\## Git



Робоча гілка: `practice-01`.



Базовий репозиторій: https://github.com/serhii-ch-eu/digital-dean-api-starter



Для здачі роботи необхідно опублікувати власний Fork, гілку `practice-01` і тег `practice-01`.

