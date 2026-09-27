# PocketMemory-AI

基于 M5Stack StickS3 的 AI 语音记录助手。当前阶段先开发 Python AI 服务端，不接入硬件。

## 当前实现范围

```text
WAV 音频 → FunASR → SenseVoiceSmall → 中文文本
```

OpenDev 的大模型 API 已接入；当前配置为 `deepseek-v4-1-flash-260910`。不加 `--analyze` 时只执行 ASR，加上后才会调用模型提取结构化信息。

## 目录

```text
main.py                 命令行入口，后续可接 FastAPI
config.py               .env 配置管理
asr/sensevoice.py       SenseVoiceSmall 封装
service/pipeline.py     音频到文字的业务管线
hardware/ble_receiver.py StickS3 BLE 音频接收与 MP3 编码
llm/qwen.py             Qwen 接口预留
test/test_asr.py        ASR 测试脚本
test/test_llm.py        LLM 占位测试
```

## 安装

建议 Python 3.11 或 3.12：

```powershell
cd D:\minicamp\PocketMemory-AI
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

模型默认读取：`D:\model\SenseVoiceSmall`。如需修改，在 `.env` 中设置 `SENSEVOICE_MODEL_DIR`。

## 测试

把测试录音放到 `test\test.wav`，然后运行：

```powershell
.\.venv\Scripts\python.exe main.py .\test\test.wav
```

## 接入 Qwen3.5-Plus

先复制配置模板并填写你自己的 API Key（不要把 Key 发到聊天或提交到 Git）：

```powershell
Copy-Item .env.example .env
notepad .env
```

将这一行改为你的 Key：

```text
QWEN_API_KEY=你的_API_Key
```

然后运行完整流程：

```powershell
.\.venv\Scripts\python.exe main.py .\test\test.wav --analyze
```

输出会包含 `text` 和 `analysis`。`analysis.items` 是事件数组；一句话里有多个独立事项时会拆成多条，每条包含 `summary`、`task`、`time`、`location`、`people`、`tags`、`intent` 字段。模型会根据运行当天日期，将“明天、后天、下周”等相对时间换算成 `YYYY年MM月DD日`，有具体时刻时使用 `YYYY年MM月DD日 HH:MM`。

注意：Qwen API 会产生网络请求和费用；不加 `--analyze` 时不会调用 API。若提示 Qwen API 请求超时，说明 SenseVoice 已识别成功，问题在访问 Qwen 服务的网络连接；请检查网络/VPN/代理后重试。

## 接入 StickS3 硬件

硬件通信单独放在 `hardware/`，不会和 ASR、LLM 代码混在一起。先安装新增依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install bleak
```

`bleak` 只在使用 `--ble` 时需要；普通本地音频测试不依赖它。

确保 StickS3 开机，并且没有被手机或其他程序占用，然后运行：

```powershell
.\.venv\Scripts\python.exe main.py --ble
```

程序会通过 BLE 搜索 `StickS3-VoiceBridge`，只监听硬件发送的 8-bit PCM。连接后按硬件录音键开始，再按一次硬件录音键结束，程序收到 `AUDIO_END` 后自动保存为：

```text
recordings/sticks3_年月日_时分秒.mp3
```

如果还要继续执行 SenseVoice 和 DeepSeek 结构化解析：

```powershell
.\.venv\Scripts\python.exe main.py --ble --analyze
```

这条命令的完整流程是：

```text
StickS3 BLE → 8-bit PCM → MP3 → SenseVoiceSmall → DeepSeek → items 数组
```

硬件协议来自 `StickS3_VoiceBridge.apk`：BLE 服务 UUID 为 `6e400001-b5a3-f393-e0a9-e50e24dcca9e`，写入特征为 `6e400002-b5a3-f393-e0a9-e50e24dcca9e`，通知特征为 `6e400003-b5a3-f393-e0a9-e50e24dcca9e`。

也可以运行：

```powershell
.\.venv\Scripts\python.exe -m test.test_asr
```

第一次识别会加载约 940 MB 的模型，后续调用会复用模型。音频会自动转换为 16 kHz、单声道格式。

## FastAPI 与本地记忆存储

安装依赖后启动：

```powershell
D:\minicamp\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> 可测试接口：

- `POST /memories/transcribe?analyze=false`：上传音频，只做 ASR。
- `POST /memories/transcribe?analyze=true`：上传音频并调用 OpenDev 模型。
- `GET /memories?limit=20`：查看最近记录。
- `GET /memories/search?q=图书馆`：搜索文本、任务、地点和标签。
- `POST /hardware/record?analyze=false`：等待一次 StickS3 按钮录音并自动保存。
- `POST /hardware/record?analyze=true`：硬件录音后同时调用 OpenDev 结构化解析。
- `POST /memories/{memory_id}/items/{item_index}/reminder`：把带时间的真实待办发送到 StickS3，设备倒计时后播放内置语音。
- `GET /health`：服务健康检查。
- `GET /app`：打开 PocketMemory 网页界面，进行硬件录音和历史搜索。

结果保存到 `data/pocketmemory.db`，每条记录包括文本、录音文件名和 `analysis.items`。

### 测试 StickS3 提醒

虚拟环境位于项目上一级目录。StickS3 烧录 `StickS3_VoiceReminder.ino` 后，
在 PowerShell 中从 `D:\minicamp` 执行：

```powershell
cd D:\minicamp
.\.venv\Scripts\python.exe PocketMemory-AI\tools\test_hardware_reminder.py --seconds 10
```

项目虚拟环境已经包含 `bleak`；如果是新环境，再执行
`uv pip install --python .venv\Scripts\python.exe bleak`。

脚本会发送固件实际支持的 `REMIND:10`，并打印 `REMINDER_SET`、倒计时和
`REMINDER_RINGING` 通知。

使用 `main.py --ble` 或 `main.py --ble --analyze` 时，硬件录音结果也会写入同一个 SQLite 数据库，并在输出中显示 `memory_id`。

查看 SQLite 数据的方式：

1. 浏览器打开 `http://127.0.0.1:8000/docs`，执行 `GET /memories`；
2. 使用 SQLite 可视化工具（如 DB Browser for SQLite）打开 `data/pocketmemory.db`；
3. 使用 Python 查询：

```powershell
D:\minicamp\.venv\Scripts\python.exe -c "from storage.store import MemoryStore; import json; print(json.dumps(MemoryStore().list_recent(), ensure_ascii=False, indent=2))"
```
