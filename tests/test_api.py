from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_market_snapshot():
    res = client.get('/api/market/snapshot')
    assert res.status_code == 200
    body = res.json()
    assert len(body['items']) >= 10


def test_recommendations_has_10_each_side():
    res = client.get('/api/recommendations')
    assert res.status_code == 200
    body = res.json()
    assert len(body['add_positions']) == 10
    assert len(body['reduce_positions']) == 10


def test_symbol_advice_categories():
    res = client.get('/api/advice/600519.SH')
    assert res.status_code == 200
    action = res.json()['action']
    assert action in ['持仓', '加仓', '减仓', '清仓']


def test_audience_request_and_script():
    req = client.post('/api/audience/request', json={'symbol': '600519.SH', 'user': 'tester'})
    assert req.status_code == 200

    script = client.get('/api/script')
    assert script.status_code == 200
    payload = script.json()
    assert payload['male_script']
    assert payload['female_script']
    assert '不构成投资建议' in payload['risk_disclaimer']


def test_tts_endpoint_generates_wav_file():
    res = client.post('/api/tts', json={'text': '测试语音', 'speaker': 'female'})
    assert res.status_code == 200
    data = res.json()
    out = Path(data['audio_path'])
    assert out.exists()
    assert out.suffix.lower() == '.wav'
