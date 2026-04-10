"""OG image generation for shared profiles (1200×630)."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
_FONT_PATH = _FONTS_DIR / "PlusJakartaSans-VariableFont_wght.ttf"

# Colors
_BG = "#f6f5f1"
_TEXT = "#1a1a1a"
_TEXT_MUTED = "#6b6b6b"
_DOT_EMPTY = "#d4d4d4"

# Score dot colors (same as frontend ScoreDots.svelte)
_DOT_COLORS = {
    "low": "#ca8a04",  # gold — score ≤ 40
    "mid": "#16a34a",  # green — score ≤ 80
    "high": "#1d68a7",  # blue — score > 80
}


def _dot_color(score: float | None) -> str:
    if score is None:
        return _DOT_EMPTY
    if score <= 40:
        return _DOT_COLORS["low"]
    if score <= 80:
        return _DOT_COLORS["mid"]
    return _DOT_COLORS["high"]


def _load_font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(_FONT_PATH), size)
    font.set_variation_by_axes([weight])
    return font


def _score_to_dots(score: float | None) -> list[str]:
    """Convert 0-100 score to 5 dots: 'full', 'half', or 'empty'."""
    if score is None:
        return ["empty"] * 5
    # Map score to 0-5 scale
    filled = score / 20.0
    dots = []
    for i in range(5):
        threshold = i + 1
        if filled >= threshold - 0.25:
            dots.append("full")
        elif filled >= threshold - 0.75:
            dots.append("half")
        else:
            dots.append("empty")
    return dots


def _draw_dots(draw: ImageDraw.ImageDraw, x: int, y: int, score: float | None, dot_r: int = 10):
    """Draw 5 score dots at (x, y)."""
    color = _dot_color(score)
    dots = _score_to_dots(score)
    spacing = dot_r * 3
    for i, state in enumerate(dots):
        cx = x + i * spacing
        cy = y
        if state == "full":
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=color)
        elif state == "half":
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=_DOT_EMPTY)
            # Draw left half filled
            draw.pieslice([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], 90, 270, fill=color)
        else:
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=_DOT_EMPTY)


def gerar_og_image(
    partidos: list[dict],
    total_respostas: int,
    slug: str,
) -> bytes:
    """Generate 1200×630 OG image PNG bytes."""
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), _BG)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_logo = _load_font(900, 36)
    font_title = _load_font(700, 40)
    font_partido = _load_font(700, 32)
    font_rank = _load_font(800, 28)
    font_footer = _load_font(400, 20)

    # Logo top-left
    draw.text((60, 40), "voto.vc", fill=_TEXT, font=font_logo)

    # Title centered
    title = "Meu alinhamento político"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, 120), title, fill=_TEXT, font=font_title)

    # Top 3 partidos
    y_start = 210
    for i, p in enumerate(partidos[:3]):
        sigla = p.get("sigla", "?")
        score = p.get("score")
        rank_label = f"#{i + 1}"
        y = y_start + i * 100

        # Rank number
        draw.text((120, y), rank_label, fill=_TEXT_MUTED, font=font_rank)

        # Party name
        draw.text((190, y - 4), sigla, fill=_TEXT, font=font_partido)

        # Score dots
        _draw_dots(draw, x=420, y=y + 16, score=score, dot_r=12)

        # Score text
        if score is not None:
            score_text = f"{score:.0f}%"
            draw.text((620, y - 2), score_text, fill=_TEXT_MUTED, font=font_rank)

    # Footer
    footer = f"Baseado em {total_respostas} votos · voto.vc/p/{slug}"
    bbox = draw.textbbox((0, 0), footer, font=font_footer)
    fw = bbox[2] - bbox[0]
    draw.text(((w - fw) // 2, h - 70), footer, fill=_TEXT_MUTED, font=font_footer)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
