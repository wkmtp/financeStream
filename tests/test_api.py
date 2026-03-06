from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_market_snapshot():
    res = client.get('/api/market/snapshot')
    assert res.status_code == 200
    body = res.json()
    assert len(body['items']) >= 3


def test_audience_request_and_script():
    req = client.post('/api/audience/request', json={'symbol': '600519.SH', 'user': 'tester'})
    assert req.status_code == 200

    script = client.get('/api/script')
    assert script.status_code == 200
    payload = script.json()
    assert payload['male_script']
    assert payload['female_script']
    assert '风险' in payload['risk_disclaimer']


def test_tts_endpoint_generates_wav_file():
    res = client.post('/api/tts', json={'text': '测试语音', 'speaker': 'female'})
    assert res.status_code == 200
    data = res.json()
    out = Path(data['audio_path'])
    assert out.exists()
    assert out.suffix.lower() == '.wav'
