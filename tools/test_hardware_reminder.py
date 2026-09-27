"""发送 StickS3 真实固件提醒协议并打印设备回执。

运行：python tools/test_hardware_reminder.py --seconds 10
"""
from __future__ import annotations

import argparse
import asyncio

try:
    from bleak import BleakClient, BleakScanner
except ModuleNotFoundError as exc:  # pragma: no cover - exercised on a clean machine
    raise SystemExit(
        "缺少 bleak。请在 D:\\minicamp 根目录运行："
        "uv pip install --python .venv\\Scripts\\python.exe bleak"
    ) from exc


SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
WRITE = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


async def main(seconds: int) -> None:
    if not 1 <= seconds <= 86400:
        raise SystemExit("seconds 必须在 1 到 86400 之间")
    device = await BleakScanner.find_device_by_name("StickS3-VoiceReminder", timeout=15)
    if device is None:
        for item in await BleakScanner.discover(timeout=8):
            if (item.name or "").startswith("StickS3"):
                device = item
                break
    if device is None:
        raise SystemExit("找不到 StickS3-VoiceReminder，请确认已开机且未被手机连接")

    def on_notify(_sender, data: bytearray) -> None:
        print("设备通知:", bytes(data).decode("utf-8", errors="replace"), flush=True)

    async with BleakClient(device) as client:
        await client.start_notify(NOTIFY, on_notify)
        await client.write_gatt_char(WRITE, f"REMIND:{seconds}".encode(), response=False)
        print(f"已发送 REMIND:{seconds}，等待设备播报…", flush=True)
        await asyncio.sleep(seconds + 4)
        await client.stop_notify(NOTIFY)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=10)
    asyncio.run(main(parser.parse_args().seconds))
