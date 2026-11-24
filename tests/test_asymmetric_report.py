import json
from fastapi.testclient import TestClient
from app.main import app
from app.api import asymmetric_lab

client=TestClient(app)
def test_report_404(monkeypatch,tmp_path):
    monkeypatch.setattr(asymmetric_lab,'REPORT_PATH',tmp_path/'missing.json')
    assert client.get('/api/v1/lab/crypto/asymmetric-benchmark-results').status_code==404

def test_summary_and_filter(monkeypatch,tmp_path):
    p=tmp_path/'report.json'; p.write_text(json.dumps({'schema_version':1,'run_id':'test','environment':{},'parameters':{},'key_generation':[{'profile':'a','series_ns':[1]*5,'median_ns':1,'iqr_ns':0}],'results':[{'profile':'p','operation':'encrypt','payload_bytes':64,'series_mean_ns':[1]*5,'median_ns':1,'iqr_ns':0,'ciphertext_bytes':256,'throughput_mib_s':None},{'profile':'q','operation':'decrypt','payload_bytes':1024,'series_mean_ns':[1]*5,'median_ns':1,'iqr_ns':0,'ciphertext_bytes':1072,'throughput_mib_s':1}],'checks':[{'name':'ok','profile':'p','passed':True}]}))
    monkeypatch.setattr(asymmetric_lab,'REPORT_PATH',p)
    r=client.get('/api/v1/lab/crypto/asymmetric-benchmark-results')
    assert r.status_code==200 and r.json()['summary']=={'key_profiles_count':1,'results_count':2,'checks_count':1,'all_checks_passed':True}
