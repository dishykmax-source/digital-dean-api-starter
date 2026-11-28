"""Reproducible Practice 03 benchmark: 5 profiles, 22 real correctness checks."""
import argparse, csv, datetime, json, os, platform, random, statistics, subprocess, uuid
from pathlib import Path
from time import perf_counter_ns, get_clock_info
from app.security.asymmetric import CONTEXT, PROFILES, SIZES, DecryptionError, decrypt, encrypt, generate_keypair, oaep_max_bytes

DIRECT = ("rsa2048-oaep", "rsa3072-oaep")
HYBRID = ("rsa3072-oaep-aes256gcm", "hpke-x25519-aes256gcm", "hpke-p256-aes256gcm")
ALL = DIRECT + HYBRID
FIELDS = ["group", "profile", "operation", "payload_bytes", "series_index", "operations", "elapsed_ns", "ns_per_operation", "ciphertext_bytes"]

def expect_failure(fn):
    try: fn()
    except Exception: return True
    return False

def stats(values):
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return float(statistics.median(values)), float(q3-q1)

def run_benchmark(output_dir="results/practice-03", operations=20, seed=20261124):
    out=Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    rng=random.Random(seed); run_id=datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6]
    keys={p:generate_keypair(p) for p in ALL}
    checks=[]
    def check(name, profile, ok, detail=""):
        checks.append({"name":name,"profile":profile,"passed":bool(ok),"detail":detail})
    # 5 roundtrip + 5 wrong key + 5 tamper + 5 wrong context + 2 OAEP boundaries.
    for p in ALL:
        sizes=(64,) if p in DIRECT else (1024,65536,1048576)
        for size in sizes:
            msg=rng.randbytes(size); env=encrypt(p,keys[p].public_key(),msg)
            check("roundtrip",p,decrypt(p,keys[p],env)==msg,f"{size} bytes")
        env=encrypt(p,keys[p].public_key(),b"negative test")
        wrong=generate_keypair(p)
        check("wrong_key",p,expect_failure(lambda:decrypt(p,wrong,env)))
        damaged=env[:-1]+bytes([env[-1]^1])
        check("tamper",p,expect_failure(lambda:decrypt(p,keys[p],damaged)))
        check("wrong_context",p,expect_failure(lambda:decrypt(p,keys[p],env,CONTEXT+b"x")))
    for p in DIRECT:
        max_len=oaep_max_bytes(PROFILES[p].key_bits)
        good=encrypt(p,keys[p].public_key(),b"x"*max_len)
        ok = decrypt(p,keys[p],good)==b"x"*max_len and expect_failure(lambda:encrypt(p,keys[p].public_key(),b"x"*(max_len+1)))
        check("oaep_boundary",p,ok,f"max={max_len}; max+1 rejected")
    if len(checks)!=28 or not all(c['passed'] for c in checks):
        raise RuntimeError(f"Correctness checks failed: {checks}")
    raw=[]; keygen=[]
    for p in ALL:
        times=[]
        for i in range(1,6):
            t=perf_counter_ns(); generate_keypair(p); elapsed=perf_counter_ns()-t
            times.append(float(elapsed)); raw.append(dict(group="key_generation",profile=p,operation="keygen",payload_bytes=0,series_index=i,operations=1,elapsed_ns=elapsed,ns_per_operation=elapsed,ciphertext_bytes=0))
        med,iqr=stats(times); keygen.append(dict(profile=p,series_ns=times,median_ns=med,iqr_ns=iqr))
    results=[]
    for size in SIZES:
        profiles=DIRECT if size==64 else HYBRID
        msg=rng.randbytes(size)
        for p in profiles:
            priv=keys[p]; pub=priv.public_key()
            # Prepare valid decrypt envelopes before the timer.
            dec_envs=[encrypt(p,pub,msg) for _ in range(operations)]
            for op in ("encrypt","decrypt"):
                means=[]; cipher_len=0
                for si in range(1,6):
                    order=list(range(operations)); rng.shuffle(order)
                    started=perf_counter_ns()
                    if op=="encrypt":
                        envs=[encrypt(p,pub,msg) for _ in order]
                        cipher_len=len(envs[0])
                    else:
                        plains=[decrypt(p,priv,dec_envs[j]) for j in order]
                    elapsed=perf_counter_ns()-started; mean=elapsed/operations; means.append(mean)
                    if op=="encrypt":
                        assert all(decrypt(p,priv,e)==msg for e in envs)
                        cipher_len=len(envs[0])
                    else:
                        assert all(x==msg for x in plains); cipher_len=len(dec_envs[0])
                    raw.append(dict(group=PROFILES[p].kind,profile=p,operation=op,payload_bytes=size,series_index=si,operations=operations,elapsed_ns=elapsed,ns_per_operation=mean,ciphertext_bytes=cipher_len))
                med,iqr=stats(means)
                throughput=(size*1e9/((2**20)*med)) if p in HYBRID else None
                results.append(dict(profile=p,operation=op,payload_bytes=size,series_mean_ns=means,median_ns=med,iqr_ns=iqr,ciphertext_bytes=cipher_len,throughput_mib_s=throughput))
    try: commit=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
    except Exception: commit="unavailable (not a git checkout)"
    report={"schema_version":1,"run_id":run_id,"environment":{"python":platform.python_version(),"os":platform.platform(),"architecture":platform.machine(),"cpu_count":os.cpu_count(),"cryptography":__import__('cryptography').__version__,"perf_counter_resolution_s":get_clock_info('perf_counter').resolution,"source_commit":commit,"date_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()},"parameters":{"sizes_bytes":list(SIZES),"operations_per_series":operations,"series":5,"key_generation_series":5,"context":CONTEXT.decode(),"order_seed":seed,"timer":"perf_counter_ns"},"key_generation":keygen,"results":results,"checks":checks}
    # atomic write after all semantic checks
    tmp=out/'raw.csv.tmp'
    with tmp.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(raw)
    tmp.replace(out/'raw.csv')
    tmpj=out/'report.json.tmp'; tmpj.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); tmpj.replace(out/'report.json')
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',default='results/practice-03'); a=ap.parse_args(); r=run_benchmark(a.output_dir); print(f"{r['run_id']}: {len(r['results'])} results, {len(r['checks'])} checks")
