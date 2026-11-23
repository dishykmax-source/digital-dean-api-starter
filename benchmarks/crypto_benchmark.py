"""Вимірювання продуктивності: 6 комбінацій × 3 розміри × 2 операції.

Запуск з кореня проєкту:
    python -m benchmarks.crypto_benchmark --output-dir results/practice-02

У вимірюваний час входить створення об'єкта бібліотеки, шифрування або
розшифрування з перевіркою тега та обгортка адаптера. HTTP, файли, JSON,
друк і генерація ключів — поза таймером.
"""
import argparse
import csv
import datetime
import gc
import json
import os
import platform
import random
import subprocess
import sys
import uuid
from pathlib import Path
from secrets import token_bytes
from statistics import median, quantiles
from time import get_clock_info, perf_counter_ns

from app.security.adapters import open_bytes, seal_bytes
from app.security.nonce import NonceSequence
from app.security.profiles import COMBINATIONS, KEY_BYTES

SIZES = (1024, 65536, 1048576)
WARMUP = 10
SERIES = 5
OPERATIONS = 100
CONTEXT_BYTES = 64
SEED = 20260101
RAW_FIELDS = ["run_id", "backend", "algorithm", "size_bytes", "operation",
              "series_index", "operations", "total_ns", "mean_ns"]


def measure_batch_total(operation, arguments):
    if not arguments:
        raise ValueError("Empty batch")
    started = perf_counter_ns()
    for item in arguments:
        operation(*item)
    elapsed = perf_counter_ns() - started
    if elapsed <= 0:
        raise RuntimeError("Invalid elapsed time")
    return elapsed


def measure_batch(operation, arguments):
    """Середній час однієї операції в серії, нс."""
    return measure_batch_total(operation, arguments) / len(arguments)


def summarize(series_mean_ns, size_bytes):
    if len(series_mean_ns) != 5:
        raise ValueError("Five series required")
    q1, _, q3 = quantiles(series_mean_ns, n=4, method="inclusive")
    typical = median(series_mean_ns)
    if typical <= 0:
        raise ValueError("Time must be positive")
    return {
        "median_ns": typical,
        "iqr_ns": q3 - q1,
        "throughput_mib_s": size_bytes * 1e9 / (2**20 * typical),
    }


class _ComboState:
    """Незалежні ключ і послідовність nonce для пари «бібліотека, алгоритм»."""

    def __init__(self, algorithm):
        self.key = token_bytes(KEY_BYTES[algorithm])
        self.nonces = NonceSequence(limit=10**9)


def _prepare_encrypt(state, backend, algorithm, data, aad, count):
    return [(backend, algorithm, state.key, state.nonces.next(), data, aad)
            for _ in range(count)]


def _prepare_decrypt(state, backend, algorithm, data, aad, count):
    # Один коректний конверт зі свіжим nonce; повторне розшифрування допустиме.
    nonce = state.nonces.next()
    ct, tag = seal_bytes(backend, algorithm, state.key, nonce, data, aad)
    return [(backend, algorithm, state.key, nonce, ct, tag, aad)] * count


def _prepare(op, *args):
    return (_prepare_encrypt if op == "encrypt" else _prepare_decrypt)(*args)


def _function(op):
    return seal_bytes if op == "encrypt" else open_bytes


def _cpu_model():
    try:
        if sys.platform == "win32":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        if os.path.exists("/proc/cpuinfo"):
            for line in open("/proc/cpuinfo", encoding="utf-8"):
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def _acceleration_note():
    """Лише те, що можна прочитати з системи; висновків за результатами не робимо."""
    try:
        if os.path.exists("/proc/cpuinfo"):
            for line in open("/proc/cpuinfo", encoding="utf-8"):
                if line.lower().startswith("flags"):
                    flags = line.split(":", 1)[1].split()
                    return {"aes_flag": "aes" in flags, "pclmulqdq_flag": "pclmulqdq" in flags,
                            "source": "/proc/cpuinfo"}
    except Exception:
        pass
    return "not determined"


def _openssl_version():
    try:
        from cryptography.hazmat.backends.openssl.backend import backend
        return backend.openssl_version_text()
    except Exception:
        return "unavailable"


def _git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unavailable"


def collect_environment():
    import cryptography
    try:
        import Crypto
        crypto_version = Crypto.__version__
    except Exception:
        crypto_version = "not installed"
    return {
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "cryptography": cryptography.__version__,
        "pycryptodome": crypto_version,
        "openssl_used_by_cryptography": _openssl_version(),
        "hardware_acceleration": _acceleration_note(),
        "perf_counter_resolution_s": get_clock_info("perf_counter").resolution,
        "git_commit": _git_commit(),
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def run_benchmark(output_dir, sizes=SIZES, warmup=WARMUP, operations=OPERATIONS,
                  seed=SEED, combos=None, log=print):
    combos = list(combos or COMBINATIONS)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    data_rng = random.Random(seed)          # не для криптографічних ключів
    order_rng = random.Random(seed + 1)
    states = {c: _ComboState(c[1]) for c in combos}
    raw, series_means = [], {}

    gc.collect()
    gc.disable()
    try:
        for size in sizes:
            data = data_rng.randbytes(size)           # однакові байти для всіх
            aad = data_rng.randbytes(CONTEXT_BYTES)   # однаковий 64-байтовий контекст
            # 1) точність відновлення в кожній комбінації
            for backend, algorithm in combos:
                st = states[(backend, algorithm)]
                nonce = st.nonces.next()
                ct, tag = seal_bytes(backend, algorithm, st.key, nonce, data, aad)
                if open_bytes(backend, algorithm, st.key, nonce, ct, tag, aad) != data:
                    raise RuntimeError(f"Round trip failed: {backend} {algorithm} {size}")
            for op in ("encrypt", "decrypt"):
                fn = _function(op)
                # 2) прогрівання (свіжі nonce також тут)
                for backend, algorithm in combos:
                    st = states[(backend, algorithm)]
                    for item in _prepare(op, st, backend, algorithm, data, aad, warmup):
                        fn(*item)
                # 3) п'ять серій, порядок комбінацій змінюється
                for s in range(1, SERIES + 1):
                    order = combos[:]
                    order_rng.shuffle(order)
                    for backend, algorithm in order:
                        st = states[(backend, algorithm)]
                        args = _prepare(op, st, backend, algorithm, data, aad, operations)
                        gc.collect()
                        total = measure_batch_total(fn, args)
                        mean = total / operations
                        raw.append({"run_id": run_id, "backend": backend, "algorithm": algorithm,
                                    "size_bytes": size, "operation": op, "series_index": s,
                                    "operations": operations, "total_ns": total, "mean_ns": mean})
                        series_means.setdefault((backend, algorithm, size, op), []).append(mean)
                        del args
            log(f"size {size} B done")
    finally:
        gc.enable()

    results = []
    for size in sizes:
        for backend, algorithm in combos:
            for op in ("encrypt", "decrypt"):
                means = series_means[(backend, algorithm, size, op)]
                results.append({"backend": backend, "algorithm": algorithm, "size_bytes": size,
                                "operation": op, "series_mean_ns": means,
                                **summarize(means, size)})
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "environment": collect_environment(),
        "parameters": {
            "sizes_bytes": list(sizes), "warmup": warmup, "series": SERIES,
            "operations_per_series": operations, "context_bytes": CONTEXT_BYTES,
            "includes_library_object_creation": True, "data_seed": seed,
        },
        "results": results,
    }
    with open(out / "raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_FIELDS)
        writer.writeheader()
        writer.writerows(raw)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default="results/practice-02")
    parser.add_argument("--operations", type=int, default=OPERATIONS,
                        help="операцій у серії (базово 100; зміна = інший профіль)")
    parser.add_argument("--warmup", type=int, default=WARMUP)
    args = parser.parse_args()
    if (args.operations, args.warmup) != (OPERATIONS, WARMUP):
        print("УВАГА: нестандартний профіль; вкажіть його у звіті", file=sys.stderr)
    report = run_benchmark(args.output_dir, operations=args.operations, warmup=args.warmup)
    print(f"run_id={report['run_id']} rows={len(report['results'])} -> {args.output_dir}")


if __name__ == "__main__":
    main()
