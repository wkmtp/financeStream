from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_dynamic_mode():
    res = client.get('/')
    assert res.status_code == 200
    assert res.json()['message'] == 'dynamic live mode enabled'


def test_health_endpoints():
    live = client.get('/health/live')
    ready = client.get('/health/ready')
    assert live.status_code == 200
    assert ready.status_code == 200
    assert live.json()['status'] == 'live'
    assert ready.json()['status'] == 'ready'


def test_live_stream_status_endpoint():
    res = client.get('/api/live/stream-status')
    assert res.status_code == 200
    assert 'running' in res.json()


def test_live_stream_start_stop_contract():
    start = client.post('/api/live/start', json={'platform': 'douyin', 'rtmp_url': 'rtmp://example/live/room'})
    assert start.status_code == 200
    assert 'ok' in start.json()
    assert 'status' in start.json()

    stop = client.post('/api/live/stop')
    assert stop.status_code == 200
    assert 'ok' in stop.json()


def test_market_snapshot():
    res = client.get('/api/market/snapshot')
    assert res.status_code == 200
    body = res.json()
    assert len(body['items']) >= 10
    assert 'server_time' in body


def test_recommendations_has_10_each_side_and_comments():
    res = client.get('/api/recommendations')
    assert res.status_code == 200
    body = res.json()
    assert len(body['add_positions']) == 10
    assert len(body['reduce_positions']) == 10
    assert isinstance(body['comments'], list)


def test_symbol_advice_categories():
    res = client.get('/api/advice/600519.SH')
    assert res.status_code == 200
    action = res.json()['action']
    assert action in ['持仓', '加仓', '减仓', '清仓']


def test_portfolio_endpoint():
    res = client.get('/api/portfolio')
    assert res.status_code == 200
    body = res.json()
    assert 'cumulative_return_pct' in body
    assert 'todays_trades' in body
    assert 'positions' in body


def test_platform_status_and_messages():
    status = client.get('/api/platform/status')
    assert status.status_code == 200
    items = status.json()['items']
    assert {x['platform'] for x in items} == {'douyin', 'kuaishou'}

    messages = client.get('/api/platform/messages')
    assert messages.status_code == 200
    assert len(messages.json()['items']) >= 1


def test_platform_reply():
    res = client.post('/api/platform/reply', json={'platform': 'douyin', 'user': 'u1', 'text': '收到，稍后点评'})
    assert res.status_code == 200
    body = res.json()
    assert body['platform'] == 'douyin'


def test_audience_request_and_script_and_live_state():
    req = client.post('/api/audience/request', json={'symbol': '600519.SH', 'user': 'tester'})
    assert req.status_code == 200

    script = client.get('/api/script')
    assert script.status_code == 200
    payload = script.json()
    assert payload['male_script']
    assert payload['female_script']
    assert '不构成投资建议' in payload['risk_disclaimer']

    live = client.get('/api/live/state')
    assert live.status_code == 200
    live_payload = live.json()
    assert 'portfolio' in live_payload
    assert 'selected_comments' in live_payload


def test_tts_endpoint_generates_wav_file():
    res = client.post('/api/tts', json={'text': '测试语音', 'speaker': 'female', 'preferred_engine': 'piper'})
    assert res.status_code == 200
    data = res.json()
    out = Path(data['audio_path'])
    assert out.exists()
    assert out.suffix.lower() == '.wav'
    assert data['engine_used'] in ['piper', 'gpt_sovits', 'tone_fallback']
