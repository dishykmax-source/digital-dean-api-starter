# Практична робота 04 — інструкція запуску

Ваш список №7 означає варіант №3 (summary).

## Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

Перед запуском benchmark бажано зробити коміт у Git, щоб `source_commit` записував реальний SHA коміту. Якщо ZIP-копія не має `.git`, спершу створіть/клонуйте Git-репозиторій і commit. Запуск експерименту:
```powershell
python -m benchmarks.hash_benchmark
python -m benchmarks.plot_hash_results
python -m uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`  
Endpoint: `http://127.0.0.1:8000/api/v1/lab/crypto/hash-benchmark-results`

Benchmark формує `report.json`, `raw.csv`, `avalanche.csv`. Вимірювання можуть тривати декілька хвилин; не запускайте паралельно інші важкі процеси. Не замінюйте власні результати синтетичними/прикладними числами.

## Git: продовжити Практичну 3 у своєму форку

Оскільки цей ZIP не містить `.git`-історії, не створюйте нову незалежну історію з нього. У своєму локальному clone/fork виконайте (якщо `upstream` уже налаштовано, `remote add` повторно не потрібен):
```powershell
git status --short
git remote -v
git fetch origin
git fetch upstream
git switch practice-03
git pull --ff-only origin practice-03
git switch -c practice-04 practice-03
```
Збережіть baseline tag перед інтеграцією каркаса, якщо у викладацького upstream є starter branch, згідно з методичкою. ZIP-пакет містить реалізацію файлів, яку можна перенести в цю робочу гілку, але Git merge/tag і push потрібно виконати у вашому clone.
