# Практична робота 03

## Варіант
Номер у списку 7; `7 mod 4 = 3`. Індивідуальна вимога — додати `summary` до API-відповіді.

## Встановлення (Python 3.12+)
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip install -r requirements-practice-03.txt
```

`cryptography==48.0.1` потрібна для вбудованого HPKE API, що використовується в цій роботі.

## Запуск
```bash
python examples/practice_03_rsa.py
python -m benchmarks.asymmetric_benchmark
python -m benchmarks.plot_asymmetric_results
python -m pytest
python -m uvicorn app.main:app --reload
```

API: `GET http://127.0.0.1:8000/api/v1/lab/crypto/asymmetric-benchmark-results`.
Swagger: `http://127.0.0.1:8000/docs`.

## Застереження
HPKE Base не автентифікує відправника. RSA-OAEP напряму призначений лише для малих повідомлень. Для гібридного RSA/AES використовується новий AES-256 ключ і 12-байтовий nonce на кожне повідомлення. Не використовуйте навчальний код як готовий production-протокол.
