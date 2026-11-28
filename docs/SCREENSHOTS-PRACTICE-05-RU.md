# Практическая работа №5 — инструкция по настоящим скриншотам (русский язык)

Скриншоты нужно сделать **на своём компьютере после запуска проекта**. Картинки-примеры из интернета не подходят как доказательства выполнения. Не редактируйте ответы сервера и не показывайте реальные пароли.

Создайте папку `docs/screenshots/practice-05/` (можно хранить снимки отдельно и вставить их в отчёт). Делайте снимки через `Win + Shift + S` в Windows или `Cmd + Shift + 4` на macOS. Сохраняйте PNG с именами ниже.

## 0. Подготовка

1. Откройте папку проекта в VS Code: **File → Open Folder**.
2. Откройте терминал: **Terminal → New Terminal**.
3. Создайте и активируйте окружение (Windows PowerShell):

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```

4. Если PowerShell запрещает активацию, используйте терминал CMD и команду `\.venv\Scripts\activate.bat`.
5. Установите зависимости именно из `pyproject.toml`. Не пытайтесь исправлять ошибки тестов удалением тестов или снижением PBKDF2.

## 1. `01-project-tree.png` — структура проекта

В VS Code разверните слева `app`, `app/db`, `app/security`, `app/repositories`, `app/schemas`, `app/api`, `tests`, `postman`, `docs`. На снимке должны быть видны новые файлы `schema.py`, `connection.py`, `initialize.py`, `passwords.py`, `user_repository.py`, `user_account.py`, `accounts.py` и `test_practice05_accounts.py`.

## 2. `02-database-schema.png` — шесть таблиц

1. В терминале выполните `python -m app.db.initialize` два раза.
2. Откройте SQLite-файл `var/digital-dean.sqlite3` в DB Browser for SQLite (или используйте SQLite Viewer).
3. Перейдите на вкладку **Database Structure**.
4. Покажите таблицы `status`, `user`, `role`, `user_role`, `course`, `grade`.
5. Не открывайте и не фотографируйте таблицу пользователей с колонками `password` и `salt`.

Альтернатива без DB Browser — выполните в SQLite:

```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
```

## 3. `03-password-hashing.png` — PBKDF2

В VS Code откройте `app/security/passwords.py`. На снимке должны быть видны `ITERATIONS = 600_000`, `SALT_BYTES = 16`, `hashlib.pbkdf2_hmac`, `hmac.compare_digest`, проверки формата и UTF-8. Не показывайте парольные записи из реальной базы.

## 4. `04-practice05-tests.png` — тесты новой практической

В терминале выполните:

```powershell
python -m pytest -q tests/test_practice05_accounts.py
```

Сделайте снимок, где видна команда и итог `12 passed` (если число тестов изменилось после ваших правок, покажите фактическое число).

## 5. `05-full-test-suite.png` — все старые и новые тесты

Выполните:

```powershell
python -m pytest -q
```

Снимок должен показывать фактический итог. Если есть ошибки, не скрывайте их: исправьте зависимости командой `python -m pip install -e ".[dev]"` и повторите. В отчёте укажите только последний фактический результат.

## 6. `06-swagger-endpoints.png` — документация API

1. Запустите сервер: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`.
2. Откройте браузер: `http://127.0.0.1:8000/docs`.
3. Разверните теги `accounts`.
4. Покажите четыре операции: `POST /api/v1/users`, `DELETE /api/v1/users/{user_id}`, `PATCH /api/v1/users/{user_id}/block`, `POST /api/v1/auth/login`.

## 7. `07-postman-runner.png` — коллекция Postman

1. В Postman выберите **Import → Files**.
2. Укажите `postman/digital-dean-practice-05.postman_collection.json`.
3. Убедитесь, что сервер работает на `127.0.0.1:8000`.
4. Откройте коллекцию → **Run** → **Run Digital Dean API — Practice 05 Accounts**.
5. Запустите все запросы сверху вниз. Скрипты используют collection variables, поэтому запускать нужно с начала.
6. Сохраните снимок Runner с фактическими зелёными проверками и результатами запросов.

## 8. `08-persistence-before-after.png` — сохранение после перезапуска

1. Зарегистрируйте отдельного тестового пользователя со статусом `1` и выдуманным паролем длиной не менее 15 символов.
2. Проверьте `/api/v1/auth/login` — ответ должен быть JSON `true`.
3. Остановите сервер `Ctrl+C`.
4. Запустите его снова той же командой и с тем же файлом `var/digital-dean.sqlite3`.
5. Повторите login — ответ должен остаться `true`.
6. Заблокируйте пользователя через PATCH, снова перезапустите сервер и проверьте login — теперь должен быть `false`.
7. Сделайте снимки ответов до/после (можно два файла `08a-login-before.png`, `08b-login-after.png`).

## 9. `09-github-commits-tags.png` — GitHub

Этот снимок можно сделать только после работы в настоящем Git-клоне, который содержит историю `practice-04`. Покажите ветку `practice-05`, список собственных содержательных коммитов и аннотированные теги `practice-05-base`, `practice-05`. ZIP-архив не содержит `.git`, поэтому из него нельзя доказать исходную историю или корректное происхождение ветки.

## Вставка в отчёт

Вставьте каждый PNG в соответствующий раздел `REPORT.md`/документа отчёта. Подпись формата: `Рисунок 1 — Структура проєкту в VS Code`. Нумерацию делайте по порядку появления. Не вставляйте снимки, которые показывают придуманные или чужие результаты.
