# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行的 MVP：
- 双角色（男/女）自动解说；
- 根据行情热度自动选股，并可插入观众点名股票；
- 今日建议加仓 10 支 / 减仓 10 支；
- 客户询问具体股票时，输出持仓/加仓/减仓/清仓建议；
- 支持抖音 + 快手双平台同时直播互动（弹幕聚合与回复）；
- 双角色不间断互动，文案尽量短句以降低 token；
- TTS 已接入 GPT-SoVITS（本地 HTTP 服务），异常时自动回退示例音频。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

打开：<http://localhost:8000>

## GPT-SoVITS 环境变量

```bash
export GPT_SOVITS_API_URL="http://127.0.0.1:9880/tts"
export GPT_SOVITS_TIMEOUT="20"
export GPT_SOVITS_TEXT_LANG="zh"
export GPT_SOVITS_PROMPT_LANG="zh"
export GPT_SOVITS_REF_AUDIO_MALE="/data/voices/male_ref.wav"
export GPT_SOVITS_PROMPT_TEXT_MALE="这是男主播参考音"
export GPT_SOVITS_REF_AUDIO_FEMALE="/data/voices/female_ref.wav"
export GPT_SOVITS_PROMPT_TEXT_FEMALE="这是女主播参考音"
```

## 核心 API

- `GET /api/market/snapshot`：行情快照
- `GET /api/hot`：热门股票
- `GET /api/recommendations`：今日加仓 10 支 / 减仓 10 支
- `GET /api/advice/{symbol}`：个股建议（持仓/加仓/减仓/清仓）
- `GET /api/platform/status`：抖音/快手双平台直播状态
- `GET /api/platform/messages`：双平台互动消息聚合
- `POST /api/platform/reply`：向指定平台用户发送主播回复
- `POST /api/audience/request`：观众点股
- `GET /api/script`：双角色解说稿
- `POST /api/tts`：调用 GPT-SoVITS
- `GET /api/live/state`：直播看板状态（含不间断互动与平台消息）

## 合规说明

系统内置风险提示模板：
> 仅供学习交流，不构成投资建议。
