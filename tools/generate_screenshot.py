"""Generate a representative screenshot of the MarkItDown GUI for the README.

We can't easily take a real screenshot of a Flet desktop app from this
CLI environment, so this script renders a high-fidelity mockup that
matches the app's actual Material 3 design language. Anyone running the
app can replace `assets/screenshot.png` with a real capture if desired.

Run from the repo root:
    python tools/generate_screenshot.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# --- Constants -----------------------------------------------------------

WIDTH, HEIGHT = 1200, 800
BG = (250, 250, 250)              # page background
SURFACE = (255, 255, 255)         # card / panel surface
SURFACE_VARIANT = (243, 242, 241)  # drop zone
OUTLINE = (225, 223, 221)         # hairline borders
OUTLINE_VARIANT = (237, 235, 233) # subtler dividers
ON_SURFACE = (32, 31, 30)         # primary text
ON_SURFACE_VAR = (96, 94, 92)     # secondary text
PRIMARY = (0, 120, 212)           # Microsoft blue
RED = (209, 52, 56)               # FAILED
GREEN = (16, 124, 16)             # DONE
ORANGE = (202, 80, 16)            # CANCELLED
AMBER_BG = (255, 244, 224)        # warning background

# Fonts (Windows paths; works on this dev box)
FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


# --- Drawing helpers -----------------------------------------------------

def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int] | None = None,
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    s: str,
    *,
    f: ImageFont.FreeTypeFont | None = None,
    fill: tuple[int, int, int] = ON_SURFACE,
) -> None:
    draw.text(xy, s, font=f or font(13), fill=fill)


def text_size(s: str, f: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = f.getbbox(s)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def chip(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    *,
    bg: tuple[int, int, int] = (232, 238, 246),
    fg: tuple[int, int, int] = PRIMARY,
    f: ImageFont.FreeTypeFont | None = None,
) -> int:
    """Render a chip; return the right x for layout."""
    f = f or font(12)
    pad_x, pad_y = 10, 5
    tw, th = text_size(label, f)
    box = (xy[0], xy[1], xy[0] + tw + 2 * pad_x, xy[1] + th + 2 * pad_y)
    draw.rounded_rectangle(box, radius=10, fill=bg)
    draw.text((xy[0] + pad_x, xy[1] + pad_y), label, font=f, fill=fg)
    return box[2]


# --- Top bar -------------------------------------------------------------

def draw_top_bar(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((0, 0, WIDTH, 64), fill=SURFACE)
    draw.line((0, 64, WIDTH, 64), fill=OUTLINE_VARIANT, width=1)
    # Title
    draw.text((28, 20), "MarkItDown", font=font(20, bold=True), fill=ON_SURFACE)
    # Version chip on the right
    chip(draw, (WIDTH - 100, 22), "v0.1.0")


# --- Navigation rail -----------------------------------------------------

NAV_ITEMS = [
    ("主页", True),
    ("设置", False),
    ("插件", False),
    ("关于", False),
]


def draw_rail(draw: ImageDraw.ImageDraw) -> None:
    rail_x = 0
    rail_w = 88
    draw.rectangle((rail_x, 64, rail_x + rail_w, HEIGHT), fill=SURFACE)
    draw.line((rail_x + rail_w, 64, rail_x + rail_w, HEIGHT), fill=OUTLINE_VARIANT, width=1)
    item_h = 72
    y = 64 + 16
    for label, selected in NAV_ITEMS:
        cx = rail_x + rail_w // 2
        # Icon: simple filled circle as a stand-in for an Icon glyph
        if selected:
            # Selected indicator pill behind the icon
            draw.rounded_rectangle(
                (rail_x + 12, y, rail_x + rail_w - 12, y + item_h - 12),
                radius=12,
                fill=(232, 238, 246),  # primary container light
            )
            draw.ellipse((cx - 10, y + 12, cx + 10, y + 32), fill=PRIMARY)
        else:
            draw.ellipse((cx - 9, y + 14, cx + 9, y + 32), fill=ON_SURFACE_VAR)
        text_w, _ = text_size(label, font(12))
        draw.text((cx - text_w // 2, y + 40), label, font=font(12), fill=ON_SURFACE)
        y += item_h


# --- Main content --------------------------------------------------------

def draw_drop_zone(draw: ImageDraw.ImageDraw, x: int, y: int, w: int) -> int:
    h = 200
    box = (x, y, x + w, y + h)
    rounded_rect(draw, box, radius=12, fill=SURFACE_VARIANT, outline=OUTLINE, width=2)
    cx = x + w // 2
    # Cloud icon (a stylized shape)
    draw.ellipse((cx - 30, y + 28, cx + 30, y + 72), fill=PRIMARY)
    # Title
    title = "拖入文件到此处"
    tw, _ = text_size(title, font(18, bold=True))
    draw.text((cx - tw // 2, y + 86), title, font=font(18, bold=True), fill=ON_SURFACE)
    # Subtitle
    sub = "或 点击选择文件"
    sw, _ = text_size(sub, font(13))
    draw.text((cx - sw // 2, y + 116), sub, font=font(13), fill=ON_SURFACE_VAR)
    # Button
    btn_label = "选择文件"
    bw, bh = text_size(btn_label, font(13))
    btn_w, btn_h = bw + 32, 32
    btn_x = cx - btn_w // 2
    btn_y = y + 142
    draw.rounded_rectangle(
        (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
        radius=16,
        outline=PRIMARY,
        width=1,
    )
    draw.text(
        (btn_x + 16, btn_y + 8),
        btn_label,
        font=font(13),
        fill=PRIMARY,
    )
    # Footer note
    note = "支持 PDF / Word / Excel / PPT / HTML / EPUB / ZIP 等(暂不支持图片与音频)"
    nw, _ = text_size(note, font(11))
    draw.text((cx - nw // 2, y + h - 22), note, font=font(11), fill=ON_SURFACE_VAR)
    return y + h


def draw_task_header(draw: ImageDraw.ImageDraw, x: int, y: int, w: int) -> int:
    # "任务列表 (3)" left
    draw.text((x, y + 6), "任务列表 (3)", font=font(16, bold=True), fill=ON_SURFACE)
    # Right side: 3 buttons
    right_x = x + w
    # Order from right: 开始转换 (primary), 清空, 清除已完成
    # We'll place them right-aligned with 8px gaps.
    btn_labels = ["清除已完成", "清空", "开始转换"]
    btn_fills = [ON_SURFACE_VAR, ON_SURFACE_VAR, SURFACE]
    btn_bg = [None, None, PRIMARY]
    # Build from right to left
    cursor = right_x
    for label, fill, bg in zip(reversed(btn_labels), reversed(btn_fills), reversed(btn_bg)):
        bw, bh = text_size(label, font(13))
        pad = 16
        total_w = bw + 2 * pad
        if bg is not None:
            # Filled
            btn_x = cursor - total_w
            btn_y = y
            draw.rounded_rectangle((btn_x, btn_y, cursor, btn_y + 32), radius=4, fill=bg)
            draw.text((btn_x + pad, btn_y + 9), label, font=font(13), fill=(255, 255, 255))
        else:
            # Text only
            btn_x = cursor - bw - pad
            draw.text((btn_x, btn_y + 9), label, font=font(13), fill=fill)
        cursor -= total_w + 8
    return y + 48


def draw_job_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    *,
    filename: str,
    status_color: tuple[int, int, int],
    status_text: str,
    status_label: str,
    info_extra: list[tuple[str, tuple[int, int, int]]] | None = None,
    actions: list[tuple[str, tuple[int, int, int], bool]] | None = None,
) -> int:
    """One row. info_extra = [(text, color)]. actions = [(label, color, is_filled)]"""
    h = 64 if not info_extra else 64 + 18 * len(info_extra)
    box = (x, y, x + w, y + h)
    rounded_rect(draw, box, radius=0, fill=SURFACE, outline=None)
    draw.line((x, y + h, x + w, y + h), fill=OUTLINE_VARIANT, width=1)

    # Status circle
    draw.ellipse((x + 16, y + 22, x + 40, y + 46), fill=status_color)

    # File icon + name
    draw.rounded_rectangle((x + 52, y + 24, x + 68, y + 40), radius=3, fill=ON_SURFACE_VAR)
    draw.text((x + 76, y + 22), filename, font=font(14, bold=True), fill=ON_SURFACE)

    # Status text (right of name)
    sl_w, _ = text_size(status_label, font(12))
    draw.text((x + w - 380, y + 24), status_label, font=font(12), fill=ON_SURFACE_VAR)

    # Progress ring (if running)
    if status_text == "running":
        ring_cx = x + w - 350
        ring_cy = y + 32
        # Background ring
        draw.ellipse((ring_cx - 8, ring_cy - 8, ring_cx + 8, ring_cy + 8), outline=OUTLINE, width=2)
        # Foreground arc — approximate with a 3/4 circle by drawing an arc
        draw.arc((ring_cx - 8, ring_cy - 8, ring_cx + 8, ring_cy + 8), start=30, end=330, fill=PRIMARY, width=2)

    # Actions (right side)
    cursor = x + w - 16
    for label, color, filled in reversed(actions or []):
        if filled:
            bw, bh = text_size(label, font(13))
            pad = 14
            total_w = bw + 2 * pad
            cursor -= total_w
            draw.rounded_rectangle((cursor, y + 16, cursor + total_w, y + 48), radius=4, fill=color)
            draw.text((cursor + pad, y + 24), label, font=font(13), fill=(255, 255, 255))
            cursor -= 8
        else:
            bw, _ = text_size(label, font(13))
            cursor -= bw
            draw.text((cursor, y + 24), label, font=font(13), fill=color)
            cursor -= 18

    # Extra info lines (errors, install hints)
    if info_extra:
        for i, (line, color) in enumerate(info_extra):
            draw.text((x + 76, y + 44 + i * 18), line, font=font(12 if i == 0 else 11), fill=color)

    return y + h


def draw_preview_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int) -> int:
    h = 200
    box = (x, y, x + w, y + h)
    rounded_rect(draw, box, radius=8, fill=SURFACE, outline=OUTLINE, width=1)
    # Header row: doc icon + filename + buttons
    draw.rounded_rectangle((x + 16, y + 18, x + 30, y + 32), radius=3, fill=PRIMARY)
    draw.text((x + 40, y + 16), "report.pdf", font=font(14, bold=True), fill=ON_SURFACE)
    # Right-aligned action buttons
    btn_y = y + 14
    for label in ["保存为", "复制全部"]:
        bw, _ = text_size(label, font(13))
        total_w = bw + 12
        bx = x + w - 16 - total_w
        draw.text((bx, btn_y + 4), label, font=font(13), fill=PRIMARY)
    # Markdown body
    body_x = x + 16
    body_y = y + 56
    body_w = w - 32
    body_h = h - 70
    draw.rounded_rectangle(
        (body_x, body_y, body_x + body_w, body_y + body_h),
        radius=8,
        fill=(248, 248, 248),
        outline=OUTLINE_VARIANT,
        width=1,
    )
    sample_lines = [
        "# 季度报告",
        "",
        "## 概述",
        "本季度营收同比增长 23%,主要受新品线推动。",
        "",
        "## 关键数据",
        "- 总营收: ¥12.4M",
        "- 新客户: 184",
        "- 满意度: 4.6/5",
    ]
    line_y = body_y + 12
    for ln in sample_lines:
        draw.text((body_x + 14, line_y), ln, font=font(12), fill=ON_SURFACE)
        line_y += 18
        if line_y > body_y + body_h - 8:
            break
    return y + h


# --- Compose -------------------------------------------------------------

def render() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    draw_top_bar(draw)
    draw_rail(draw)

    main_x = 88 + 16
    main_w = WIDTH - main_x - 16

    # Drop zone
    y = 80
    y = draw_drop_zone(draw, main_x, y, main_w) + 12
    # Task list
    y = draw_task_header(draw, main_x, y, main_w)

    # Card 1: running
    y = draw_job_card(
        draw, main_x, y, main_w,
        filename="Q3-report.pdf",
        status_color=PRIMARY,
        status_text="running",
        status_label="转换中...",
        actions=[("取消", PRIMARY, False)],
    )
    # Card 2: done
    y = draw_job_card(
        draw, main_x, y, main_w,
        filename="data.xlsx",
        status_color=GREEN,
        status_text="done",
        status_label="完成",
        actions=[("删除", ON_SURFACE_VAR, False), ("打开文件夹", PRIMARY, False), ("预览", PRIMARY, False)],
    )
    # Card 3: failed
    y = draw_job_card(
        draw, main_x, y, main_w,
        filename="notes.docx",
        status_color=RED,
        status_text="failed",
        status_label="失败",
        info_extra=[
            ("缺少 Python 依赖: mammoth", RED),
            ("pip install 'markitdown[docx]'", ON_SURFACE_VAR),
        ],
        actions=[("删除", ON_SURFACE_VAR, False), ("复制安装命令", PRIMARY, False), ("重试", PRIMARY, False)],
    )

    # Preview panel (if room — keep at fixed position from bottom)
    draw_preview_panel(draw, main_x, HEIGHT - 220, main_w)
    return img


def main() -> None:
    out_path = Path("assets/screenshot.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = render()
    img.save(out_path, format="PNG", optimize=True)
    print(f"[OK] wrote {out_path}  ({out_path.stat().st_size} bytes, {img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
