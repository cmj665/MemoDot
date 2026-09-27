"""OpenAI 兼容大模型 API 封装。

使用阿里云 DashScope 的 OpenAI 兼容接口。API Key 只从 .env 读取。
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from openai import APIConnectionError, APITimeoutError, APIStatusError, OpenAI


class QwenClient:
    """通过 OpenAI 兼容协议调用配置的大模型。"""

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 120, max_retries: int = 2) -> None:
        if not api_key:
            raise ValueError("未配置 QWEN_API_KEY，请在项目 .env 文件中填写 API Key。")
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)

    def extract_memory(self, text: str) -> dict:
        """从识别文本中提取任务、时间、地点、标签等结构化字段。"""
        if not text.strip():
            return {"summary": "", "task": None, "time": None, "location": None, "tags": []}

        today = datetime.now().strftime("%Y年%m月%d日")
        try:
            response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是中文个人记忆整理助手。只输出合法 JSON，不要 Markdown。"
                        f"当前日期是 {today}。必须以当前日期为基准解析相对时间。"
                        "请将‘今天、明天、后天、下周一、月底’等相对时间换算为具体日期。"
                        "time 字段统一使用 YYYY年MM月DD日 格式；如果有时刻，使用 YYYY年MM月DD日 HH:MM。"
                        "无法确定具体日期时才使用 null，不要原样输出‘明天’或‘后天’。"
                        "请先判断输入中是否包含多个独立事件、任务或时间安排。"
                        "每个独立事件必须拆成 items 数组中的一个对象，不能把多个事件混在一起。"
                        "输出格式必须是 {items:[{summary,task,time,location,people,tags,intent,visual_scene}]}。"
                        "每个事件的 visual_scene 为对象，包含英文字符串 scene,characters,action,environment,time_atmosphere，"
                        "以及英文字符串数组 key_objects。只描述这个事件，不能混合其他事件。"
                        "用户固定用焦糖棕色小熊表示（圆耳朵、奶油色嘴部、黑色点状眼睛），朋友也用小熊表示，不出现人类或兔子。"
                        "描述具体可画的日常场景，不含文字、数字、标志，不编造改变事件含义的情节。"
                        "即使只有一个事件，也必须放在 items 数组中。"
                        "没有信息的字段使用 null，tags 使用字符串数组。"
                    ),
                },
                {"role": "user", "content": text},
            ],
            )
        except APITimeoutError as exc:
            raise RuntimeError("Qwen API 请求超时。请检查网络/VPN/代理后重试；也可以先不加 --analyze 测试 ASR。") from exc
        except APIConnectionError as exc:
            raise RuntimeError("无法连接 Qwen API。请确认 QWEN_BASE_URL、网络和 API 服务可访问。") from exc
        except APIStatusError as exc:
            raise RuntimeError(f"Qwen API 返回错误（HTTP {exc.status_code}）：{exc}") from exc
        content = self._response_text(response)
        # 兼容部分网关忽略 response_format、返回 ```json ...``` 的情况。
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # 兼容网关在 JSON 前后追加说明文字的情况。
            start = content.find("{")
            end = content.rfind("}")
            if start < 0 or end <= start:
                preview = content[:300].replace("\n", " ")
                raise RuntimeError(
                    f"Qwen 返回内容不是 JSON，无法提取结构化信息。返回预览：{preview}"
                )
            try:
                parsed = json.loads(content[start : end + 1])
            except json.JSONDecodeError as exc:
                preview = content[:300].replace("\n", " ")
                raise RuntimeError(
                    f"Qwen 返回的 JSON 格式不完整。返回预览：{preview}"
                ) from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("Qwen 返回的 JSON 不是对象格式。")
        # 统一输出 items 数组，便于数据库逐条保存和后续检索。
        if isinstance(parsed.get("items"), list):
            items = parsed["items"]
        else:
            # 兼容旧模型仍返回单个对象的情况。
            items = [parsed]
        normalized_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    "summary": item.get("summary"),
                    "task": item.get("task"),
                    "time": item.get("time"),
                    "location": item.get("location"),
                    "people": item.get("people"),
                    "tags": item.get("tags", []),
                    "intent": item.get("intent"),
                    "visual_scene": item.get("visual_scene") if isinstance(item.get("visual_scene"), dict) else None,
                }
            )
        return {"items": normalized_items}

    @staticmethod
    def _response_text(response: object) -> str:
        """兼容 OpenAI 对象、字典以及 OpenDev 直接返回字符串的格式。"""
        if isinstance(response, str):
            return response or "{}"

        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message") or {}
                    return str(message.get("content") or first.get("text") or "{}")
            return str(response.get("content") or response.get("text") or "{}")

        choices = getattr(response, "choices", None) or []
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None) if message is not None else None
            return str(content or getattr(choices[0], "text", None) or "{}")

        # 某些兼容网关返回自定义对象，尽量读取 content/text 属性。
        return str(getattr(response, "content", None) or getattr(response, "text", None) or "{}")
