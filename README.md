# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行并可发布的版本：
- 双角色（男/女）自动解说；
- 今日建议加仓 10 支 / 减仓 10 支；
- 个股问答给出持仓/加仓/减仓/清仓建议；
- 抖音 + 快手双平台同时直播互动（弹幕聚合与回复）；
- GPT-SoVITS 本地 TTS（失败自动回退）；
- 增加生产发布能力：健康检查、请求日志、请求ID、可选 API Key 鉴权、可配置 worker 启动。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

打开：<http://localhost:8000>

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

- `GET /health/live`：存活检查（liveness）
- `GET /health/ready`：就绪检查（readiness）

## 核心 API

- `GET /api/market/snapshot`：行情快照
- `GET /api/hot`：热门股票
- `GET /api/recommendations`：今日加仓 10 支 / 减仓 10 支
- `GET /api/advice/{symbol}`：个股建议（持仓/加仓/减仓/清仓）
- `GET /api/platform/status`：抖音/快手双平台直播状态
- `GET /api/platform/messages`：双平台互动消息聚合
- `POST /api/platform/messages`：写入平台消息（可选 API Key）
- `POST /api/platform/reply`：主播回复平台用户（可选 API Key）
- `POST /api/audience/request`：观众点股（可选 API Key）
- `GET /api/script`：双角色解说稿
- `POST /api/tts`：调用 GPT-SoVITS（可选 API Key）
- `GET /api/live/state`：直播看板状态（含互动消息）

## 发布建议

1. 反向代理（Nginx）开启 TLS。
2. 设置 `APP_API_KEY` 并在调用写接口时传 `X-API-Key`。
3. `APP_ALLOWED_ORIGINS` 仅保留正式域名。
4. 通过 systemd 或容器编排设置进程自启动与重启策略。
5. 定期轮转日志并监控 `/health/*`。

## 合规说明

系统内置风险提示模板：
> 仅供学习交流，不构成投资建议。
