# AI 炒股直播软件（Jetson Xavier NX）

这是一个可运行的 MVP：
- 双角色（男/女）自动解说；
- 根据行情热度自动选股，并可插入观众点名股票；
- 提供实时曲线直播看板（Web）；
- 提供本地 TTS 接口（默认示例音频，便于替换 GPT-SoVITS/XTTS）；
- 面向 Jetson Xavier NX 的部署建议。

## 1. 项目结构

```text
app/
  main.py                # FastAPI API + 页面入口
  models.py              # 数据模型
  services/
    market.py            # 行情模拟与热点评分
    script_engine.py     # DeepSeek 脚本生成适配层（当前为可运行模板逻辑）
    tts_engine.py        # 本地 TTS 适配层（默认生成示例音频）
  templates/index.html   # 直播控制台页面
  static/                # JS/CSS
tests/test_api.py        # API 测试
```

## 2. 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

打开：<http://localhost:8000>

## 3. 核心 API

- `GET /api/market/snapshot`：返回实时行情快照
- `GET /api/hot`：返回热门股票
- `POST /api/audience/request`：观众点股
- `GET /api/script`：生成双角色解说稿
- `POST /api/tts`：本地 TTS 合成（可替换为 GPT-SoVITS）
- `GET /api/live/state`：看板轮询接口

## 4. Jetson Xavier NX 落地建议

1. DeepSeek 使用云 API；
2. TTS 在本地 GPU 跑 GPT-SoVITS/XTTS（将 `TTSEngine.synthesize` 替换为实际推理）；
3. 直播导播建议 OBS + FFmpeg，页面作为叠层源。

详细见：
- `docs/architecture.md`
- `docs/jetson_deploy.md`
- `prompts/deepseek_stock_commentary.md`
- `workflows/n8n_workflow_template.json`

## 5. 合规说明

系统内置风险提示模板：
> 以上内容仅供学习交流，不构成投资建议，请独立决策并控制仓位。

上线前请根据当地平台与法规补充投资相关合规策略。
