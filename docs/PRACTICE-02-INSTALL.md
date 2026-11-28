# Практична 2: як вставити файли в свій проєкт

## 1. Git (у вашому клоні, чисте робоче дерево)
```
git status --short
git remote -v                       # origin = ваш форк, upstream = викладацький
git fetch origin --tags
git switch -c practice-02 refs/tags/practice-01
python -m pytest
git fetch upstream
git merge --no-ff upstream/practice-02-starter -m "Import practice 2 scaffold"
git merge-base --is-ancestor refs/tags/practice-01 HEAD ; echo $?
git merge-base --is-ancestor upstream/practice-02-starter HEAD ; echo $?
git tag practice-02-base
python -m pytest tests/test_health.py
```
(у PowerShell код виходу: `$LASTEXITCODE`). Адреса upstream: `https://github.com/serhii-ch-eu/digital-dean-api-starter.git`
(у PDF на стор. 2 в посиланні є помилка `serhii-cheu`, правильна — `serhii-ch-eu`).
При конфлікті збережіть свою реалізацію роботи 1.

## 2. Скопіюйте файли з цього архіву поверх заготовки
`app/security/*`, `app/schemas/secure_note.py`, `app/repositories/secure_note_repository.py`,
`app/api/secure_notes.py`, `app/api/crypto_lab.py`, `benchmarks/*`, `tests/test_crypto.py`,
`tests/test_secure_notes.py`, `postman/digital-dean-practice-02.postman_collection.json`.
Якщо заготовка вже має файли з тими ж іменами — замініть їх (це і є «заповнення TODO»).
Заготовкові тести, що очікують NotImplementedError, не видаляйте: після реалізації вони мають пройти;
якщо якийсь очікує інші назви функцій — надішліть його текст.

## 3. app/main.py
```python
from app.api import secure_notes, crypto_lab
app.include_router(secure_notes.router, prefix="/api/v1")
app.include_router(crypto_lab.router, prefix="/api/v1")
```
і версія `0.2.0` (в `FastAPI(version="0.2.0")` та `pyproject.toml`).

## 4. pyproject.toml — додайте в існуючий список dependencies (не створюйте другий [project])
```
"cryptography==48.0.1",
"pycryptodome==3.24.0",
```
```
python -m pip install -e ".[dev]"
python -m pip install matplotlib      # лише для графіків
python -m pytest
```
Якщо pip не знаходить точну версію — використайте ту, що пропонує pip, і запишіть її у звіт.

## 5. Вимірювання (один процес, нічого паралельно не запускайте; ноутбук — у мережі живлення)
```
python -m benchmarks.crypto_benchmark --output-dir results/practice-02
python -m benchmarks.plot_results
```
Отримаєте `raw.csv` (180 рядків), `report.json` (36 рядків), два PNG і таблицю markdown у консолі.

## 6. Перевірка API
`python -m uvicorn app.main:app --reload --host 127.0.0.1` → Postman: імпорт колекції, Run collection
(крок 08 потребує створеного `results/practice-02/report.json`).

## 7. Коміти (мінімум 4 власні після practice-02-base) і публікація
1. залежності й криптографічні адаптери (`app/security/*`, pyproject)
2. інтеграція приміток у API (`schemas`, `repositories`, `api`, `main.py`)
3. автоматизовані перевірки (`tests/*`)
4. вимірювання, варіант, документація (`benchmarks/*`, `results/*`, `postman/*`, звіт)
```
python -m pytest
git status --short
git log --no-merges --oneline refs/tags/practice-02-base..HEAD
git push -u origin practice-02
git push origin refs/tags/practice-02-base
git tag -a practice-02 -m "Практична робота 2 завершена"
git push origin refs/tags/practice-02
git ls-remote --tags origin "refs/tags/practice-02*"
```
Не комітьте ключі, `.env`, `.venv`. Файли `results/practice-02/*` — комітьте (це докази експерименту).
