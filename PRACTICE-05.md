# Практична робота №5 — SQLite, користувачі та захист паролів

## Локальне налаштування (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Ініціалізація, повторна ініціалізація та тести

```powershell
python -m app.db.initialize
python -m app.db.initialize
python -m pytest -q tests/test_practice05_accounts.py
python -m pytest -q
```

## Запуск API

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

## Облікові маршрути

- `POST /api/v1/users` — реєстрація; без `status_id` створюється inactive-користувач.
- `DELETE /api/v1/users/{user_id}` — фізичне видалення; наявність grade дає 409.
- `PATCH /api/v1/users/{user_id}/block` — блокування статусом 2.
- `POST /api/v1/auth/login` — JSON boolean; true лише для правильного пароля active-користувача.

Для локального тесту active-користувача передавай `status_id: 1`. Пароль реєстрації має 15–128 Unicode-символів, максимум 512 байтів UTF-8. Усі дані — вигадані.

## Postman

Імпортуй `postman/digital-dean-practice-05.postman_collection.json`. Змінна `base_url` за замовчуванням — `http://127.0.0.1:8000`. Запускай collection з початку, щоб скрипти могли зберігати ID створених у цій послідовності записів.

## Безпека

Це навчальний API тільки для `127.0.0.1`. Delete і block не мають адміністративної авторизації. Не відкривай сервер у локальну мережу або інтернет. Не коміть `var/*.sqlite3`, sidecar-файли, `.env`, дампи паролів або справжні секрети.
