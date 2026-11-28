"""Графіки та таблиця з results/practice-02/report.json.

Потрібен matplotlib (лише для графіків): python -m pip install matplotlib
Запуск: python -m benchmarks.plot_results
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/practice-02")
report = json.loads((DIR / "report.json").read_text(encoding="utf-8"))
rows = report["results"]
MIB = 2**20


def throughput(size, mean_ns):
    return size * 1e9 / (MIB * mean_ns)


def label(r):
    return f'{r["algorithm"]} / {r["backend"]}'


for op, title in (("encrypt", "Шифрування"), ("decrypt", "Перевірене розшифрування")):
    fig, ax = plt.subplots(figsize=(8, 5))
    series = sorted({(r["algorithm"], r["backend"]) for r in rows})
    for algorithm, backend in series:
        pts = sorted((r for r in rows if r["algorithm"] == algorithm and
                      r["backend"] == backend and r["operation"] == op),
                     key=lambda r: r["size_bytes"])
        x = [r["size_bytes"] for r in pts]
        y = [r["throughput_mib_s"] for r in pts]
        # розкид: мінімум і максимум серед п'яти серій
        lo = [throughput(r["size_bytes"], max(r["series_mean_ns"])) for r in pts]
        hi = [throughput(r["size_bytes"], min(r["series_mean_ns"])) for r in pts]
        ax.errorbar(x, y, yerr=[[a - b for a, b in zip(y, lo)], [b - a for a, b in zip(y, hi)]],
                    marker="o", capsize=3, label=f"{algorithm} / {backend}")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Розмір повідомлення, байтів")
    ax.set_ylabel("Пропускна здатність, МіБ/с (медіана 5 серій; смуги — min–max серій)")
    ax.set_title(f"{title}: пропускна здатність за розміром повідомлення")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(DIR / f"throughput_{op}.png", dpi=150)
    plt.close(fig)

print("| Комбінація | Розмір, Б | Операція | Медіана, нс | IQR, нс | МіБ/с | Розмір результату (S+16), Б |")
print("|---|---|---|---|---|---|---|")
for r in sorted(rows, key=lambda r: (r["algorithm"], r["backend"], r["size_bytes"], r["operation"])):
    print(f'| {label(r)} | {r["size_bytes"]} | {r["operation"]} | {r["median_ns"]:.0f} | '
          f'{r["iqr_ns"]:.0f} | {r["throughput_mib_s"]:.1f} | {r["size_bytes"] + 16} |')
print(f"\nГрафіки: {DIR / 'throughput_encrypt.png'}, {DIR / 'throughput_decrypt.png'}")
