# Как завершить GitHub-историю practice-05 без потери practice-04

**Почему нужен этот шаг:** загруженный ZIP не содержит скрытой папки `.git`. В нём есть файлы проекта, но нет коммитов и тегов. Нельзя создать честный `practice-05-base` или подтвердить происхождение от `practice-04`, просто распаковав ZIP. Не инициализируйте новую историю поверх ZIP — это потеряет доказательство предыдущей работы.

## Шаг 1. Клонировать свой настоящий репозиторий

Откройте PowerShell в папке, где храните проекты:

```powershell
git clone --branch practice-04 https://github.com/dishykmax-source/digital-dean-api-starter.git digital-dean-api-git
git -C digital-dean-api-git status
git -C digital-dean-api-git tag --list
```

Проверьте, что это действительно ваш форк и что в нём присутствует завершённый тег `practice-04`. Если GitHub просит авторизацию или ветки/тега нет, остановитесь и проверьте адрес репозитория в браузере.

## Шаг 2. Подключить исходный репозиторий преподавателя и получить каркас

```powershell
cd digital-dean-api-git
git remote add upstream https://github.com/serhii-ch-eu/digital-dean-api-starter.git
git fetch upstream practice-05-starter
git switch -c practice-05 practice-04
git merge --no-ff --no-edit upstream/practice-05-starter
```

Если `upstream` уже существует, не добавляйте его повторно: выполните `git remote -v`, затем `git fetch upstream practice-05-starter`. Если merge сообщает конфликт, не используйте `--abort` вслепую и не удаляйте файлы — сначала разрешите конфликты.

## Шаг 3. Зафиксировать baseline

Сразу после успешного слияния каркаса:

```powershell
git tag -a practice-05-base -m "Practice 05 starter baseline"
git show --stat practice-05-base
```

Тег baseline создаётся до ваших собственных реализаций. Если такой тег уже есть, не передвигайте и не перезаписывайте его.

## Шаг 4. Перенести готовые файлы из ZIP

1. Распакуйте `digital-dean-api-starter-practice-04-completed.zip` в отдельную папку.
2. Скопируйте содержимое распакованного проекта в `digital-dean-api-git`, **но не копируйте** `.git`, `.venv`, `var`, `__pycache__`, `.pytest_cache` и любые `*.sqlite*` файлы.
3. Подтвердите замену файлов, но не удаляйте файлы предыдущих практических.
4. Вернитесь в терминал `digital-dean-api-git` и проверьте `git status`.

## Шаг 5. Сделать четыре содержательных коммита

Сгруппируйте изменения по назначению. После каждого `git add` проверьте список staged-файлов через `git status`.

```powershell
# 1. Схема, соединения и повторяемая инициализация
git add app/db
git commit -m "Add SQLite schema and repeatable initialization"

# 2. Парольный профиль, модели и репозиторий
git add app/security/passwords.py app/schemas/user_account.py app/repositories/user_repository.py
git commit -m "Add PBKDF2 password profile and user repository"

# 3. Четыре HTTP-маршрути та підключення
git add app/api/accounts.py app/api/account_validation.py app/main.py
git commit -m "Add account registration login block and delete endpoints"

# 4. Тести, Postman, звіт та інструкції
git add tests/test_practice05_accounts.py postman/digital-dean-practice-05.postman_collection.json REPORT.md PRACTICE-05.md docs/practice-05-report-template.md docs/SCREENSHOTS-PRACTICE-05-RU.md docs/GIT-PRACTICE-05-RU.md
git commit -m "Add practice 05 tests Postman collection and report"
```

Если отдельный файл не изменился после merge, `git add` всё равно допустим; но коммит должен содержать реальные изменения. Не создавайте пустые коммиты ради количества.

## Шаг 6. Проверить и опубликовать

Сначала выполните тесты и проверьте, что база/секреты не попадут в Git:

```powershell
python -m pip install -e ".[dev]"
python -m app.db.initialize
python -m pytest -q tests/test_practice05_accounts.py
python -m pytest -q
git status --short
git log --oneline practice-05-base..HEAD
git merge-base --is-ancestor practice-04 HEAD
```

Последняя команда должна завершиться без ошибки (код возврата 0). Только после фактического успешного тестирования:

```powershell
git push -u origin practice-05
git push origin tag practice-05-base
git tag -a practice-05 -m "Practice 5 verified result"
git push origin tag practice-05
```

Если тег `practice-05-base` уже был опубликован, не перезаписывайте его. Снимок GitHub делайте после проверки вкладок **Code**, **Commits** и **Tags**.
