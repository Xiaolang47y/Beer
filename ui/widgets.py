# -*- coding: utf-8 -*-
"""Shared widgets for Beer."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QFrame


def popup_background_color(combo):
    """Return the background colour the popup container should use.

    Qt stylesheets do not reliably update QWidget.palette(), so we inspect the
    stylesheet that is actually applied to the combo or its ancestors.
    """
    widget = combo
    while widget is not None:
        stylesheet = widget.styleSheet()
        if stylesheet:
            if '#2b2b2b' in stylesheet or '#3c3f41' in stylesheet:
                return '#3c3f41'
            if '#f5f5f5' in stylesheet or '#ffffff' in stylesheet:
                return '#ffffff'
        widget = widget.parent()
    return '#ffffff'


def fix_combobox_popup(combo):
    """Remove the white/black bars around a combo box dropdown popup."""
    view = combo.view()
    if view is None:
        return
    view.setFrameShape(QFrame.Shape.NoFrame)

    container = view.parentWidget()
    if container is not None and isinstance(container, QFrame):
        container.setFrameShape(QFrame.Shape.NoFrame)
        container.setFrameShadow(QFrame.Shadow.Plain)
        container.setLineWidth(0)
        container.setMidLineWidth(0)
        container.setContentsMargins(0, 0, 0, 0)

        layout = container.layout()
        if layout is not None:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        background = popup_background_color(combo)
        container.setStyleSheet(
            f"QFrame {{ background-color: {background}; border: none; }}"
        )


class BeerComboBox(QComboBox):
    """ComboBox with a frameless popup that ignores mouse wheel changes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._fix_popup_frame()

    def _fix_popup_frame(self):
        fix_combobox_popup(self)

    def showPopup(self):
        super().showPopup()
        self._fix_popup_frame()

    def wheelEvent(self, event):
        event.ignore()
