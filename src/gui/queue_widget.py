# ダウンロードキューのテーブルウィジェット。
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, cast

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from core.downloader import Status

# ─────────────────────────────────────────────────────────────────────
# 表示定数
# ─────────────────────────────────────────────────────────────────────

_STATUS_COLOR: Dict[str, str] = {
    Status.QUEUED:      "#888888",
    Status.DOWNLOADING: "#2196F3",
    Status.PROCESSING:  "#FF9800",
    Status.DONE:        "#4CAF50",
    Status.FAILED:      "#F44336",
    Status.CANCELLED:   "#9E9E9E",
}

_STATUS_LABEL: Dict[str, str] = {
    Status.QUEUED:      "待機中",
    Status.DOWNLOADING: "ダウンロード中",
    Status.PROCESSING:  "処理中",
    Status.DONE:        "完了",
    Status.FAILED:      "失敗",
    Status.CANCELLED:   "キャンセル",
}

# カラム定義
_COLUMNS    = ["タイトル / URL", "ステータス", "進捗", "速度", "残り時間", ""]
_COL_TITLE  = 0
_COL_STATUS = 1
_COL_PROG   = 2
_COL_SPEED  = 3
_COL_ETA    = 4
_COL_ACT    = 5


# ─────────────────────────────────────────────────────────────────────
# QueueWidget
# ─────────────────────────────────────────────────────────────────────

class QueueWidget(QTableWidget):
    # ダウンロードタスクを行単位で表示するテーブル。

    # タスク ID を引数にキャンセル要求を発火する
    cancel_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(0, len(_COLUMNS), parent)
        self._id_to_row: Dict[str, int] = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # セットアップ
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setHorizontalHeaderLabels(_COLUMNS)

        header = self.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(_COL_TITLE,  QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_PROG,   QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_SPEED,  QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_ETA,    QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_ACT,    QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(_COL_PROG, 150)
        self.setColumnWidth(_COL_ACT, 50)

        v_header = self.verticalHeader()
        assert v_header is not None
        v_header.setVisible(False)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setMinimumHeight(150)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def add_task(self, task_id: str, display: str) -> None:
        # 新規タスクの行をテーブル末尾に追加する。
        row = self.rowCount()
        self.insertRow(row)
        self._id_to_row[task_id] = row

        self.setItem(row, _COL_TITLE, QTableWidgetItem(display))
        self._set_status_item(row, Status.QUEUED)
        self.setCellWidget(row, _COL_PROG, self._new_progress_bar())
        self.setItem(row, _COL_SPEED, QTableWidgetItem(""))
        self.setItem(row, _COL_ETA,   QTableWidgetItem(""))
        self.setCellWidget(row, _COL_ACT, self._new_cancel_button(task_id))

    def update_progress(
        self,
        task_id: str,
        pct: float,
        speed: str,
        eta: str,
    ) -> None:
        row = self._id_to_row.get(task_id)
        if row is None:
            return
        bar = cast(Optional[QProgressBar], self.cellWidget(row, _COL_PROG))
        if bar is not None:
            bar.setValue(int(pct))
        self._set_cell(row, _COL_SPEED, speed)
        self._set_cell(row, _COL_ETA, eta)

    def update_status(self, task_id: str, status: str) -> None:
        row = self._id_to_row.get(task_id)
        if row is None:
            return
        self._set_status_item(row, status)
        if status == Status.DONE:
            bar = cast(Optional[QProgressBar], self.cellWidget(row, _COL_PROG))
            if bar is not None:
                bar.setValue(100)

    def update_title(self, task_id: str, title: str) -> None:
        row = self._id_to_row.get(task_id)
        if row is None:
            return
        self._set_cell(row, _COL_TITLE, title)

    def get_counts(self) -> Tuple[int, int]:
        # (完了数, 合計数) を返す。完了には done/failed/cancelled を含む。
        total = len(self._id_to_row)
        done = sum(
            1 for row in self._id_to_row.values()
            if self._row_status(row) in Status.TERMINAL
        )
        return done, total

    def remove_finished(self) -> None:
        # 完了 / キャンセル / 失敗したすべての行を削除する。
        to_remove: List[Tuple[int, str]] = [
            (row, task_id)
            for task_id, row in self._id_to_row.items()
            if self._row_status(row) in Status.TERMINAL
        ]

        # 行番号降順に削除してインデックスのズレを回避
        for row, task_id in sorted(to_remove, reverse=True):
            self.removeRow(row)
            del self._id_to_row[task_id]

        # 残った行の行番号を詰め直す
        self._id_to_row = {
            tid: row - sum(1 for removed_row, _ in to_remove if removed_row < row)
            for tid, row in self._id_to_row.items()
        }

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _new_progress_bar(self) -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        return bar

    def _new_cancel_button(self, task_id: str) -> QWidget:
        button = QPushButton("✕")
        button.setFixedSize(34, 24)
        button.setToolTip("キャンセル / 削除")
        button.clicked.connect(lambda _, tid=task_id: self.cancel_requested.emit(tid))

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.addWidget(button)
        return container

    def _set_status_item(self, row: int, status: str) -> None:
        item = QTableWidgetItem(_STATUS_LABEL.get(status, status))
        item.setForeground(QColor(_STATUS_COLOR.get(status, "#888888")))
        item.setData(Qt.ItemDataRole.UserRole, status)
        self.setItem(row, _COL_STATUS, item)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        existing = self.item(row, col)
        if existing is not None:
            existing.setText(text)
        else:
            self.setItem(row, col, QTableWidgetItem(text))

    def _row_status(self, row: int) -> Optional[str]:
        item = self.item(row, _COL_STATUS)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)
