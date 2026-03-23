"""現在のOSとCPUアーキテクチャを検出する。"""
from __future__ import annotations

import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    system: str        # "Windows" | "Linux" | "Darwin"
    machine: str       # "x86_64" | "aarch64" | "arm64"
    is_windows: bool
    is_linux: bool
    is_macos: bool
    is_arm64: bool
    display_name: str  # 例: "Linux/x86_64"


def detect() -> PlatformInfo:
    system = platform.system()
    machine = platform.machine()
    is_arm64 = machine.lower() in ("aarch64", "arm64")
    return PlatformInfo(
        system=system,
        machine=machine,
        is_windows=(system == "Windows"),
        is_linux=(system == "Linux"),
        is_macos=(system == "Darwin"),
        is_arm64=is_arm64,
        display_name=f"{system}/{machine}",
    )
