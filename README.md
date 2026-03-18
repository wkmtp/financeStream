# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行并可发布的**动态直播流**版本（非网页展示）：
- 行情层采用 **AkShare + 东方财富 API** 优先获取实时行情，失败时回退本地模拟；
- 互动层采用 **OpenClaw** 对接抖音 + 快手弹幕与回复；
- 推理层采用 **DeepSeek** 生成双角色讲解与每只入选股票的股评；
- 交易层自动生成每日买进/卖出/持仓，并统计累计收益；
- 背景叠字实时展示：讨论标的、双角色话术、当日买卖、当前持仓、累计收益、个股股评；
- TTS 采用 Piper + GPT-SoVITS 双引擎自动路由；
- FFmpeg 动态画面叠字推流到 RTMP。

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

## 核心接口

- `GET /api/market/snapshot`：实时行情快照（AkShare/东方财富优先）
- `GET /api/recommendations`：今日加仓/减仓推荐 + 每只入选股票股评
- `GET /api/portfolio`：当日买卖、当前持仓、累计收益
- `GET /api/live/state`：直播完整运行态（含股评与组合）
- `POST /api/live/start`：启动 RTMP 动态直播
- `POST /api/live/stop`：停止 RTMP 动态直播

## 生产环境变量

```bash
# OpenClaw
export OPENCLAW_API_URL="http://127.0.0.1:9000"
export OPENCLAW_TIMEOUT="8"

# DeepSeek
export DEEPSEEK_API_URL="https://api.deepseek.com/chat/completions"
export DEEPSEEK_API_KEY="your-deepseek-key"
export DEEPSEEK_MODEL="deepseek-chat"
export DEEPSEEK_TIMEOUT="18"

# TTS
export TTS_DEFAULT_ENGINE="auto"
export TTS_AUTO_SHORT_TEXT_THRESHOLD="56"
```

## 合规说明

系统内置风险提示模板：
> 仅供学习交流，不构成投资建议。
