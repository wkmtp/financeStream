# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行并可发布的**动态直播流**版本（非网页展示）：
- 双角色（男/女）自动解说；
- 今日建议加仓 10 支 / 减仓 10 支；
- 个股问答给出持仓/加仓/减仓/清仓建议；
- 抖音 + 快手双平台同时直播互动（弹幕聚合与回复）；
- 双引擎 TTS：Piper + GPT-SoVITS 自动路由（失败自动回退）；
- FFmpeg 动态画面叠字推流到 RTMP；
- 生产能力：健康检查、请求日志、请求ID、可选 API Key 鉴权、可配置 worker 启动。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

## 动态直播控制

1. 启动直播：
```bash
curl -X POST http://localhost:8000/api/live/start \
  -H 'Content-Type: application/json' \
  -d '{"platform":"douyin","rtmp_url":"rtmp://push.example.com/live/room001"}'
```

2. 查看状态：
```bash
curl http://localhost:8000/api/live/stream-status
```

3. 停止直播：
```bash
curl -X POST http://localhost:8000/api/live/stop
```

## 生产环境变量

```bash
# 应用
export APP_NAME="AI Stock Live Studio"
export APP_ENV="prod"
export APP_DEBUG="false"
export APP_ALLOWED_ORIGINS="https://your-domain.com"
export APP_MAX_QUEUE="500"

# 可选：写接口鉴权，不设置则关闭鉴权
export APP_API_KEY="replace-with-strong-key"

# uvicorn
export UVICORN_WORKERS="2"
export UVICORN_LOG_LEVEL="info"

# TTS 路由策略
export TTS_DEFAULT_ENGINE="auto"                  # auto|piper|gpt_sovits
export TTS_AUTO_SHORT_TEXT_THRESHOLD="56"

# Piper
export PIPER_BIN="piper"
export PIPER_MODEL_MALE="/data/piper/zh_CN-male.onnx"
export PIPER_CONFIG_MALE="/data/piper/zh_CN-male.onnx.json"
export PIPER_MODEL_FEMALE="/data/piper/zh_CN-female.onnx"
export PIPER_CONFIG_FEMALE="/data/piper/zh_CN-female.onnx.json"
export PIPER_TIMEOUT="12"

# GPT-SoVITS
export GPT_SOVITS_API_URL="http://127.0.0.1:9880/tts"
export GPT_SOVITS_TIMEOUT="20"
export GPT_SOVITS_TEXT_LANG="zh"
export GPT_SOVITS_PROMPT_LANG="zh"
export GPT_SOVITS_REF_AUDIO_MALE="/data/voices/male_ref.wav"
export GPT_SOVITS_PROMPT_TEXT_MALE="这是男主播参考音"
export GPT_SOVITS_REF_AUDIO_FEMALE="/data/voices/female_ref.wav"
export GPT_SOVITS_PROMPT_TEXT_FEMALE="这是女主播参考音"
```

## 健康检查

- `GET /health/live`
- `GET /health/ready`

## 合规说明

系统内置风险提示模板：
> 仅供学习交流，不构成投资建议。
