"""ダウンロードキューのテーブルウィジェット。"""
from __future__ import annotations

from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
)

_STATUS_COLOR: Dict[str, str] = {
    "queued":      "#888888",
    "downloading": "#2196F3",
    "processing":  "#FF9800",
    "done":        "#4CAF50",
    "failed":      "#F44336",
    "cancelled":   "#9E9E9E",
}

_STATUS_LABEL: Dict[str, str] = {
    "queued":      "待機中",
    "downloading": "ダウンロード中",
    "processing":  "処理中",
    "done":        "完了",
    "failed":      "失敗",
    "cancelled":   "キャンセル",
}

_COLUMNS = ["タイトル / URL", "ステータス", "進捗", "速度", "残り時間", ""]
_COL_TITLE  = 0
_COL_STATUS = 1
_COL_PROG   = 2
_COL_SPEED  = 3
_COL_ETA    = 4
_COL_ACT    = 5


class QueueWidget(QTableWidget):
    cancel_requested = pyqtSignal(str)  # タスクID

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(0, len(_COLUMNS), parent)
        self._id_to_row: Dict[str, int] = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # セットアップ
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setHorizontalHeaderLabels(_COLUMNS)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(_COL_TITLE,  QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_PROG,   QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(_COL_PROG, 150)
        hh.setSectionResizeMode(_COL_SPEED,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_ETA,    QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(_COL_ACT,    QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(_COL_ACT, 50)

        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def add_task(self, task_id: str, display: str) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self._id_to_row[task_id] = row

        self.setItem(row, _COL_TITLE,  QTableWidgetItem(display))
        self._set_status_item(row, "queued")

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        self.setCellWidget(row, _COL_PROG, bar)

        self.setItem(row, _COL_SPEED, QTableWidgetItem(""))
        self.setItem(row, _COL_ETA,   QTableWidgetItem(""))

        btn = QPushButton("✕")
        btn.setFixedSize(34, 24)
        btn.setToolTip("キャンセル / 削除")
        btn.clicked.connect(lambda _, tid=task_id: self._on_cancel(tid))
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.addWidget(btn)
        self.setCellWidget(row, _COL_ACT, container)

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
        bar: Optional[QProgressBar] = self.cellWidget(row, _COL_PROG)
        if bar:
            bar.setValue(int(pct))
        self._set_cell(row, _COL_SPEED, speed)
        self._set_cell(row, _COL_ETA, eta)

    def update_status(self, task_id: str, status: str) -> None:
        row = self._id_to_row.get(task_id)
        if row is None:
            return
        self._set_status_item(row, status)
        if status == "done":
            bar: Optional[QProgressBar] = self.cellWidget(row, _COL_PROG)
            if bar:
                bar.setValue(100)

    def update_title(self, task_id: str, title: str) -> None:
        row = self._id_to_row.get(task_id)
        if row is None:
            return
        self._set_cell(row, _COL_TITLE, title)

    def remove_finished(self) -> None:
        """完了 / キャンセル / 失敗したすべての行を削除する。"""
        finished_statuses = {"done", "failed", "cancelled"}
        rows_to_remove = []
        for task_id, row in self._id_to_row.items():
            item = self.item(row, _COL_STATUS)
            if item and item.data(Qt.ItemDataRole.UserRole) in finished_statuses:
                rows_to_remove.append((row, task_id))

        for row, task_id in sorted(rows_to_remove, reverse=True):
            self.removeRow(row)
            del self._id_to_row[task_id]

        # 削除後に行マップを再構築する
        self._id_to_row = {
            tid: r - sum(1 for old_r, _ in rows_to_remove if old_r < r)
            for tid, r in self._id_to_row.items()
        }

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _set_status_item(self, row: int, status: str) -> None:
        label = _STATUS_LABEL.get(status, status)
        item = QTableWidgetItem(label)
        color = _STATUS_COLOR.get(status, "#888888")
        item.setForeground(QColor(color))
        item.setData(Qt.ItemDataRole.UserRole, status)
        self.setItem(row, _COL_STATUS, item)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        existing = self.item(row, col)
        if existing:
            existing.setText(text)
        else:
            self.setItem(row, col, QTableWidgetItem(text))

    def _on_cancel(self, task_id: str) -> None:
        self.cancel_requested.emit(task_id)
