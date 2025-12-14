import json, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ===== 基础工具 =====
def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

BASE_DIR = Path(__file__).resolve().parent

def _font(size, bold=False):
    font_path = BASE_DIR / "fonts" / "NotoSansSC-VariableFont_wght.ttf"
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()

def _load_img(path: Path):
    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    return im

def _fit_contain(im, box_w, box_h):
    scale = min(box_w / im.width, box_h / im.height)
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    return im.resize((nw, nh), Image.LANCZOS)

# ===== 主渲染 =====
def render(theme_path: str, product_path: str, out_path: str):
    scale = 2  # 🔴 高清关键：2 = 清晰，3 = 更清晰（更慢）

    theme_p = Path(theme_path)
    base = theme_p.parent

    theme = json.loads(Path(theme_path).read_text(encoding="utf-8"))
    product = json.loads(Path(product_path).read_text(encoding="utf-8"))

    L = theme["layout"]
    C = theme["colors"]
    A = theme["assets"]

    W = int(L["page_width"])
    pad_l = int(L["padding_left"])
    pad_r = int(L["padding_right"])
    border_w = int(L["left_border_width"])
    x0 = border_w + pad_l
    x1 = W - pad_r

    # 预估高度
    section_base = 160
    sec_heights = []
    for key in theme["sections_order"]:
        sec = product["sections"].get(key, {})
        if key == "ingredients":
            groups = sec.get("groups", [])
            lines = sum(len(g.get("items", [])) for g in groups) + len(groups) * 2
        else:
            lines = len(sec.get("text_blocks", [])) * 3 + len(sec.get("list", []))
        sec_heights.append(section_base + max(0, lines - 4) * 26)

    H = int(
        L["header_height"]
        + L["gap_after_header"]
        + L["product_image_height"]
        + L["product_info_height"]
        + sum(sec_heights)
        + 60
    )

    img = Image.new("RGBA", (W * scale, H * scale), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)

    # 颜色
    green = _hex(C["primary"])
    title_bg = _hex(C["title_bar_bg"])
    divider = _hex(C["divider"])
    text = _hex(C["text"])
    tag_bg = _hex(C["tag_bg"])
    tag_border = _hex(C["tag_border"])
    tag_text = _hex(C["tag_text"])

    # 左侧色条
    d.rectangle([0, 0, border_w * scale, H * scale], fill=green)

    y = 0
    header_h = int(L["header_height"])

    # ===== Header Logo =====
    logo_path = base / A["header_logo"]
    if logo_path.exists():
        logo = _load_img(logo_path)
        logo_r = _fit_contain(logo, 420 * scale, 72 * scale)
        img.alpha_composite(
            logo_r,
            (x0 * scale, y * scale + (header_h * scale - logo_r.height) // 2),
        )

    # ===== 徽章 =====
    badge_d = int(L["badge_size"])
    badge_gap = int(L["badge_gap"])
    badges = A.get("header_badges", [])
    total = badge_d * len(badges) + badge_gap * max(0, len(badges) - 1)
    bx = x1 - total
    by = y + (header_h - badge_d) // 2

    for i, bp in enumerate(badges):
        p = base / bp
        cx = bx + i * (badge_d + badge_gap)
        if p.exists():
            b = _load_img(p)
            br = _fit_contain(b, badge_d * scale, badge_d * scale)
            img.alpha_composite(
                br,
                (
                    cx * scale + (badge_d * scale - br.width) // 2,
                    by * scale + (badge_d * scale - br.height) // 2,
                ),
            )

    y = header_h + int(L["gap_after_header"])

    # ===== 产品图（无黑框）=====
    box_h = int(L["product_image_height"])
    inner = int(L["product_image_padding"])
    pack_path = base / product.get("package_image", "")
    if pack_path.exists():
        pack = _load_img(pack_path)
        fitted = _fit_contain(
            pack,
            (x1 - x0 - 2 * inner) * scale,
            (box_h - 2 * inner) * scale,
        )
        img.alpha_composite(
            fitted,
            (
                (x0 + inner) * scale
                + ((x1 - x0 - 2 * inner) * scale - fitted.width) // 2,
                (y + inner) * scale
                + ((box_h - 2 * inner) * scale - fitted.height) // 2,
            ),
        )

    y += box_h + 16

    # ===== 标题 =====
    f_title = _font(32 * scale, True)
    f_sub = _font(20 * scale)
    f_small = _font(18 * scale)
    f_tag = _font(18 * scale, True)

    d.text((x0 * scale, y * scale), product.get("title_cn", ""), fill=text, font=f_title)
    d.text(
        (x0 * scale, (y + 42) * scale),
        product.get("title_original", ""),
        fill=(90, 90, 90),
        font=f_sub,
    )
    d.text(
        (x0 * scale, (y + 72) * scale),
        product.get("subtitle", ""),
        fill=(110, 110, 110),
        font=f_small,
    )

    # ===== 标签 =====
    if theme.get("tags", {}).get("enabled", True):
        tag_y = y + 110
        tag_h = int(theme["tags"]["style"]["height"])
        radius = int(theme["tags"]["style"]["radius"])
        gap = int(theme["tags"]["style"]["gap"])
        tx = x0

        for item in theme["tags"]["items"]:
            if not item.get("enabled", True):
                continue
            key = item["key"]
            label = item["label"]
            val = product.get("tags", {}).get(key, "")
            t = f"{label} {val}"
            bbox = d.textbbox((0, 0), t, font=f_tag)
            tw = (bbox[2] - bbox[0]) + 34 * scale
            d.rounded_rectangle(
                [
                    tx * scale,
                    tag_y * scale,
                    (tx + tw // scale) * scale,
                    (tag_y + tag_h) * scale,
                ],
                radius=radius * scale,
                fill=tag_bg,
                outline=tag_border,
                width=2 * scale,
            )
            d.text(
                ((tx + 16) * scale, (tag_y + 10) * scale),
                t,
                fill=tag_text,
                font=f_tag,
            )
            tx += tw // scale + gap

    y += int(L["product_info_height"])
    d.line([x0 * scale, y * scale, x1 * scale, y * scale], fill=divider, width=2 * scale)
    y += 18

    # ===== Sections（无黑框）=====
    icon_size = int(L["icon_size"])
    title_bar_h = int(L["title_bar_height"])
    section_gap = int(L["section_gap"])

    def wrap(text, max_w):
        out, cur = [], ""
        for ch in text:
            if d.textlength(cur + ch, font=f_small) <= max_w:
                cur += ch
            else:
                out.append(cur)
                cur = ch
        if cur:
            out.append(cur)
        return out

    def draw_section(y, key, height):
        meta = theme["sections_meta"][key]
        sec = product["sections"].get(key, {})

        icon_x = x0
        icon_y = y + 18
        icon_path = base / theme["assets"]["section_icons"].get(key, "")
        if icon_path.exists():
            ic = _load_img(icon_path)
            icr = _fit_contain(ic, icon_size * scale, icon_size * scale)
            img.alpha_composite(
                icr,
                (
                    icon_x * scale + (icon_size * scale - icr.width) // 2,
                    icon_y * scale + (icon_size * scale - icr.height) // 2,
                ),
            )

        bar_x0 = icon_x + icon_size + 16
        bar_y0 = y + 18
        d.rectangle(
            [bar_x0 * scale, bar_y0 * scale, x1 * scale, (bar_y0 + title_bar_h) * scale],
            fill=title_bg,
        )
        d.text(
            ((bar_x0 + 14) * scale, (bar_y0 + 10) * scale),
            meta["title"],
            fill=(40, 60, 55),
            font=_font(22 * scale, True),
        )

        ty = bar_y0 + title_bar_h + 28
        tx = bar_x0 + 16
        max_w = (x1 - tx - 16) * scale

        if key == "ingredients":
            for g in sec.get("groups", []):
                for ln in wrap(g.get("name", ""), max_w):
                    d.text((tx * scale, ty * scale), ln, fill=text, font=f_small)
                    ty += 26
                for it in g.get("items", []):
                    s = f"• {it.get('name','')} {it.get('amount','')}{it.get('unit','')}"
                    for ln in wrap(s, max_w):
                        d.text((tx * scale, ty * scale), ln, fill=text, font=f_small)
                        ty += 26
                ty += 8
        else:
            for para in sec.get("text_blocks", []):
                for ln in wrap(para, max_w):
                    d.text((tx * scale, ty * scale), ln, fill=text, font=f_small)
                    ty += 26
                ty += 6
            for bullet in sec.get("list", []):
                for ln in wrap("• " + bullet, max_w):
                    d.text((tx * scale, ty * scale), ln, fill=text, font=f_small)
                    ty += 26

        div_y = ty + 12
        d.line(
            [x0 * scale, div_y * scale, x1 * scale, div_y * scale],
            fill=divider,
            width=2 * scale,
        )
        return div_y + section_gap

    for key, h in zip(theme["sections_order"], sec_heights):
        sec = product["sections"].get(key, {})
        if key == "ingredients" and not sec.get("groups"):
            continue
        if key != "ingredients" and not sec.get("text_blocks") and not sec.get("list"):
            continue
        y = draw_section(y, key, h)

    # ===== 输出 =====
    final = img.resize((W, H), Image.LANCZOS)
    final.convert("RGB").save(out_path, "PNG")
