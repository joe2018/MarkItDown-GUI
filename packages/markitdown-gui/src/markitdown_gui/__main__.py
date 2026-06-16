"""Entry point: `python -m markitdown_gui` launches the Flet desktop app."""

import flet as ft

from .app import main

if __name__ == "__main__":
    ft.app(target=main)
