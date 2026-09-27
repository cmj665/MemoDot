"""通过 BLE 接收 StickS3 音频并保存为 MP3。

协议来自 StickS3_VoiceBridge APK：Nordic UART Service，设备发送 8-bit
unsigned PCM 数据；本模块把它转换为 16-bit WAV，再编码为 MP3，供 ASR 使用。
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
from bleak import BleakClient, BleakScanner


class StickS3BleReceiver:
    """StickS3 BLE 音频接收器。"""

    DEVICE_NAME = "StickS3-VoiceReminder"
    SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
    WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

    def __init__(self, device_name: str = DEVICE_NAME, scan_timeout: float = 15.0) -> None:
        self.device_name = device_name
        self.scan_timeout = scan_timeout
        self.sample_rate = 8000
        self._audio = bytearray()
        self._started = asyncio.Event()
        self._finished = asyncio.Event()

    async def _find_device(self):
        """扫描指定名称的 StickS3。"""
        print(f"正在扫描 BLE 设备（{self.scan_timeout:.0f} 秒）...", flush=True)
        # 某些 Windows 蓝牙驱动返回的名称会带后缀，因此先精确匹配，
        # 再用前缀匹配，避免设备名称轻微变化导致无法连接。
        device = await BleakScanner.find_device_by_name(
            self.device_name, timeout=self.scan_timeout
        )
        if device is None:
            devices = await BleakScanner.discover(timeout=min(self.scan_timeout, 8.0))
            for candidate in devices:
                name = candidate.name or ""
                if name == self.device_name or name.startswith("StickS3"):
                    device = candidate
                    print(f"发现设备：{name} ({candidate.address})", flush=True)
                    break
        if device is None:
            raise RuntimeError(
                f"找不到 BLE 设备 {self.device_name}。请确认 StickS3 已开机、距离电脑较近、"
                "没有被手机或其他程序占用，并在 Windows 蓝牙设置中重新打开蓝牙。"
            )
        print(f"正在连接：{device.name or self.device_name} ({device.address})", flush=True)
        return device

    def _on_notification(self, _sender, data: bytearray) -> None:
        """处理 AUDIO_BEGIN、音频数据和 AUDIO_END 通知。"""
        if not data:
            return
        text = bytes(data).decode("utf-8", errors="ignore")
        if text.startswith("AUDIO_BEGIN:"):
            try:
                self.sample_rate = int(text.split(":", 1)[1].strip())
            except (TypeError, ValueError):
                self.sample_rate = 8000
            self._audio.clear()
            self._started.set()
            self._finished.clear()
            return
        if text.startswith("AUDIO_END:"):
            self._finished.set()
            return
        # 协议中的普通通知包就是原始 8-bit unsigned PCM。
        self._audio.extend(data)

    async def record(self) -> tuple[bytes, int]:
        """连接设备，录音直到 StickS3 发出 AUDIO_END。"""
        device = await self._find_device()
        async with BleakClient(device) as client:
            await client.start_notify(self.NOTIFY_UUID, self._on_notification)
            print("已连接 StickS3，请按硬件录音键开始，再按一次结束。", flush=True)
            await asyncio.wait_for(self._started.wait(), timeout=300)
            print(f"已收到 AUDIO_BEGIN（{self.sample_rate} Hz），正在接收音频...", flush=True)
            await self._finished.wait()
            print("已收到 AUDIO_END，正在保存录音...", flush=True)
            await client.stop_notify(self.NOTIFY_UUID)
        if not self._audio:
            raise RuntimeError("StickS3 没有发送音频数据。")
        return bytes(self._audio), self.sample_rate

    async def send_command(self, command: str) -> None:
        """发送一条下行 BLE 命令。

        录音 APK 只公开了 REC_START/REC_STOP；提醒命令必须与固件约定后再启用。
        该通用入口让协议接入不会改动现有录音流程。
        """
        command = command.strip()
        if not command or "\n" in command or "\r" in command:
            raise ValueError("BLE 命令不能为空且不能包含换行")
        device = await self._find_device()
        async with BleakClient(device) as client:
            await client.write_gatt_char(self.WRITE_UUID, command.encode("utf-8"), response=False)

    async def send_reminder(self, text: str, at: str) -> None:
        """在设备上启动倒计时提醒。

        固件协议是 ``REMIND:<seconds>``；文本不会下发，设备播放内置 WAV。
        ``at`` 接受 ISO-8601 时间，或直接传秒数。
        """
        if not text.strip() or not at.strip():
            raise ValueError("提醒内容和时间不能为空")
        try:
            seconds = int(at)
        except ValueError:
            target = datetime.fromisoformat(at.replace("Z", "+00:00"))
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            seconds = int((target - datetime.now(timezone.utc)).total_seconds())
        if seconds <= 0 or seconds > 24 * 60 * 60:
            raise ValueError("提醒时间必须在未来 24 小时内")
        await self.send_command(f"REMIND:{seconds}")

    @staticmethod
    def _encode_mp3(raw_pcm: bytes, sample_rate: int, output_path: Path) -> None:
        """把 8-bit unsigned PCM 转成单声道 MP3。"""
        with tempfile.TemporaryDirectory(prefix="sticks3_pcm_") as temp_dir:
            raw_path = Path(temp_dir) / "audio.u8"
            raw_path.write_bytes(raw_pcm)
            command = [
                imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
                "-y", "-f", "u8", "-ar", str(sample_rate), "-ac", "1",
                "-i", str(raw_path), "-codec:a", "libmp3lame", "-q:a", "4",
                str(output_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"PCM 转 MP3 失败：{result.stderr.strip()}")

    async def record_to_mp3(self, output_path: str | Path) -> Path:
        """录音并将结果保存为 MP3 文件。"""
        raw_pcm, sample_rate = await self.record()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._encode_mp3(raw_pcm, sample_rate, output)
        return output
