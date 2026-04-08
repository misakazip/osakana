# 現在の OS と CPU アーキテクチャを検出する。
from __future__ import annotations

import platform
from dataclasses import dataclass

# ARM 64bit とみなすアーキテクチャ名
_ARM64_NAMES = frozenset({"aarch64", "arm64"})


@dataclass(frozen=True)
class PlatformInfo:
    # プラットフォーム情報の不変レコード。

    system:       str   # "Windows" | "Linux" | "Darwin"
    machine:      str   # "x86_64"  | "aarch64" | "arm64" など
    is_windows:   bool
    is_linux:     bool
    is_macos:     bool
    is_arm64:     bool
    display_name: str   # 例: "Linux/x86_64"


def detect() -> PlatformInfo:
    # 現在のプラットフォームを検出して PlatformInfo を返す。
    system  = platform.system()
    machine = platform.machine()
    return PlatformInfo(
        system=system,
        machine=machine,
        is_windows=(system == "Windows"),
        is_linux=(system == "Linux"),
        is_macos=(system == "Darwin"),
        is_arm64=(machine.lower() in _ARM64_NAMES),
        display_name=f"{system}/{machine}",
    )
