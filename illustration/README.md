# 场景插画模块

## 配置

在项目 `.env` 中添加以下内容，然后停止旧服务并重新运行 `api.py`：

```dotenv
IMAGE_API_KEY=这里填写绘图平台Key
IMAGE_BASE_URL=https://api.openai-next.com/v1
IMAGE_MODEL=gpt-image-2
IMAGE_TIMEOUT=180
```

Base URL 必须和 Key 的供应商匹配。使用官方 OpenAI Key 时改为
`https://api.openai.com/v1`。网关必须支持 `/images/generations` 和
`data[0].b64_json` PNG 响应；模型名称按用户指定保留为 `gpt-image-2`。
本地测试不证明平台已开通此模型；首次真实调用需要填写 Key 后验证。

## 流程和文件

`llm/qwen.py` 为每个 `analysis.items` 事件保留 `visual_scene`，包含
scene、characters、action、environment、time_atmosphere、key_objects。
`client.py` 拼接固定 `style.txt` 和场景描述，调用绘图 API。
`service.py` 处理旧记录的场景补全、内容变更检测、图片保存。
图片位于 `data/illustrations`；SQLite `illustrations` 表关联事件、场景和完整提示词。

点击每个事件的“生成场景卡”才产生绘图请求。录音和转写不自动触发绘图费用。
成功生成的图片复用；编辑文字或替换录音后旧图不再展示，可以再次生成。
失败不影响录音记录；不自动重试。超时可能已产生费用，请先查平台任务/账单。
提示词可促进角色一致性，但无法保证每次白兔完全相同。

## 测试步骤

1. 运行 `api.py`，刷新 `/app`。未填 Key 时点击生成，应提示配置 IMAGE_API_KEY，原记录仍存在。
2. 配置 Key 后重启，上传或录制“明天下午三点和朋友去喝咖啡”，勾选 AI 分析。
3. 事件中应包含 visual_scene，点击“生成场景卡”，等待图片生成。
4. 应出现奶油色背景的小白兔和动物朋友咖啡场景。刷新页面后图片仍在，可继续听原声。
5. 测试两个独立事件，各自生成对应图片；勾选完成不会移除图片。
6. 旧记录也可点击生成，程序先调用文本模型补全对应事件的场景。

离线回归：`D:\minicamp\.venv\Scripts\python.exe -m unittest test.test_illustration`。
测试使用临时数据库和模拟 API，不花费额度。
