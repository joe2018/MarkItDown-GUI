"""Password-style text field with show/hide toggle.

A small reusable widget used by the settings page for API key inputs.
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft


def key_input(
    label: str,
    initial_value: str | None,
    on_change: Callable[[Optional[str]], None],
    placeholder: str = "",
) -> ft.Control:
    """Build a text field that masks input and has a visibility toggle.

    `on_change` is called with the new value every keystroke, or with
    `None` if the user clears the field. The initial value is shown
    as-is; if it's `None` the field starts empty.
    """
    state = {"visible": False, "current": initial_value or ""}

    def _on_text_change(e: ft.ControlEvent) -> None:
        state["current"] = e.control.value
        on_change(e.control.value if e.control.value else None)

    def _toggle(_: ft.ControlEvent) -> None:
        state["visible"] = not state["visible"]
        field.password = not state["visible"]
        toggle_btn.icon = (
            ft.Icons.VISIBILITY_OFF if state["visible"] else ft.Icons.VISIBILITY
        )
        field.update()
        toggle_btn.update()

    field = ft.TextField(
        label=label,
        value=initial_value or "",
        password=True,
        can_reveal_password=False,  # we provide our own toggle
        on_change=_on_text_change,
        hint_text=placeholder,
        expand=True,
    )
    toggle_btn = ft.IconButton(
        icon=ft.Icons.VISIBILITY,
        tooltip="显示/隐藏",
        on_click=_toggle,
    )

    return ft.Row(
        [field, toggle_btn],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )
