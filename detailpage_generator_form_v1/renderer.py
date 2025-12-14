
import json, os, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def _hex(c):
    c=c.lstrip("#")
    return tuple(int(c[i:i+2],16) for i in (0,2,4))

def _font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

def _load_img(path: Path):
    im = Image.open(path)
    if im.mode not in ("RGBA","RGB"):
        im = im.convert("RGBA")
    if im.mode == "RGB":
        im = im.convert("RGBA")
    return im

def _fit_contain(im, box_w, box_h):
    scale = min(box_w/im.width, box_h/im.height)
    nw, nh = max(1,int(im.width*scale)), max(1,int(im.height*scale))
    return im.resize((nw,nh), Image.LANCZOS)

def render(theme_path: str, product_path: str, out_path: str):
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

    # Estimate height by content length (simple heuristic)
    section_base = 160
    sec_heights = []
    for key in theme["sections_order"]:
        sec = product["sections"].get(key, {})
        if key == "ingredients":
            groups = sec.get("groups", [])
            lines = sum(len(g.get("items",[])) for g in groups) + len(groups)*2
        else:
            lines = len(sec.get("text_blocks", [])) * 3 + len(sec.get("list", []))
        sec_heights.append(section_base + max(0, lines-4)*26)

    H = int(L["header_height"] + L["gap_after_header"] + L["product_image_height"] + L["product_info_height"] + sum(sec_heights) + 60)

    img = Image.new("RGBA",(W,H),(255,255,255,255))
    d = ImageDraw.Draw(img)

    green = _hex(C["primary"])
    title_bg = _hex(C["title_bar_bg"])
    divider = _hex(C["divider"])
    text = _hex(C["text"])
    tag_bg = _hex(C["tag_bg"])
    tag_border = _hex(C["tag_border"])
    tag_text = _hex(C["tag_text"])

    # left border
    d.rectangle([0,0,border_w,H], fill=green)

    y=0
    header_h = int(L["header_height"])

    # Header logo
    logo_path = base / A["header_logo"]
    if logo_path.exists():
        logo = _load_img(logo_path)
        target_h = 72
        logo_r = _fit_contain(logo, 420, target_h)
        img.alpha_composite(logo_r, (x0, y + (header_h-logo_r.height)//2))
    else:
        d.rectangle([x0, y+44, x0+260, y+44+72], outline=(180,180,180), width=2)

    # Badges
    badge_d = int(L["badge_size"])
    badge_gap = int(L["badge_gap"])
    badges = A.get("header_badges", [])
    total = badge_d*len(badges) + badge_gap*max(0,len(badges)-1)
    bx = x1 - total
    by = y + (header_h - badge_d)//2
    for i, bp in enumerate(badges):
        p = base / bp
        cx = bx + i*(badge_d+badge_gap)
        if p.exists():
            b = _load_img(p)
            br = _fit_contain(b, badge_d, badge_d)
            # center in slot
            ox = cx + (badge_d - br.width)//2
            oy = by + (badge_d - br.height)//2
            img.alpha_composite(br, (ox, oy))
        else:
            d.ellipse([cx,by,cx+badge_d,by+badge_d], outline=(120,120,120), width=3, fill=(245,245,245))

    y = header_h + int(L["gap_after_header"])

    # Product image box (black border)
    box_h = int(L["product_image_height"])
    d.rectangle([x0,y,x1,y+box_h], outline=(0,0,0), width=2)
    inner = int(L["product_image_padding"])
    pack_path = base / product.get("package_image","")
    if pack_path.exists():
        pack = _load_img(pack_path)
        fitted = _fit_contain(pack, (x1-x0)-2*inner, box_h-2*inner)
        ox = x0 + inner + ((x1-x0)-2*inner - fitted.width)//2
        oy = y + inner + (box_h-2*inner - fitted.height)//2
        img.alpha_composite(fitted, (ox, oy))
    y += box_h + 16

    # Titles
    f_title = _font(32, True)
    f_sub = _font(20, False)
    f_small = _font(18, False)
    f_tag = _font(18, True)

    d.text((x0,y), product.get("title_cn",""), fill=text, font=f_title)
    d.text((x0,y+42), product.get("title_original",""), fill=(90,90,90), font=f_sub)
    d.text((x0,y+72), product.get("subtitle",""), fill=(110,110,110), font=f_small)

    # Tags row
    if theme.get("tags",{}).get("enabled", True):
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
            val = product.get("tags",{}).get(key,"")
            t = f"{label} {val}"
            bbox = d.textbbox((0,0), t, font=f_tag)
            tw = (bbox[2]-bbox[0]) + 34
            d.rounded_rectangle([tx, tag_y, tx+tw, tag_y+tag_h], radius=radius, fill=tag_bg, outline=tag_border, width=2)
            d.text((tx+16, tag_y+10), t, fill=tag_text, font=f_tag)
            tx += tw + gap

    y += int(L["product_info_height"])
    d.line([x0,y,x1,y], fill=divider, width=2)
    y += 18

    # Sections
    icon_size = int(L["icon_size"])
    title_bar_h = int(L["title_bar_height"])
    section_gap = int(L["section_gap"])

    def draw_section(y, key, height):
        meta = theme["sections_meta"][key]
        title = meta["title"]
        sec = product["sections"].get(key, {})
        # icon
        icon_x = x0
        icon_y = y + 18
        icon_path = base / theme["assets"]["section_icons"].get(key, "")
        if icon_path.exists():
            ic = _load_img(icon_path)
            icr = _fit_contain(ic, icon_size, icon_size)
            # center in slot
            # draw subtle circle background
            d.ellipse([icon_x, icon_y, icon_x+icon_size, icon_y+icon_size], outline=green, width=3, fill=(240,250,248))
            img.alpha_composite(icr, (icon_x + (icon_size-icr.width)//2, icon_y + (icon_size-icr.height)//2))
        else:
            d.ellipse([icon_x, icon_y, icon_x+icon_size, icon_y+icon_size], outline=green, width=3, fill=(240,250,248))

        bar_x0 = icon_x + icon_size + 16
        bar_y0 = y + 18
        d.rectangle([bar_x0, bar_y0, x1, bar_y0+title_bar_h], fill=title_bg)
        d.text((bar_x0+14, bar_y0+10), title, fill=(40,60,55), font=_font(22, True))

        body_y = bar_y0 + title_bar_h + 14
        content_x0 = bar_x0
        content_x1 = x1
        content_h = height - (18 + title_bar_h + 14 + 36)  # rough
        content_h = max(120, content_h)
        d.rectangle([content_x0, body_y, content_x1, body_y+content_h], outline=(0,0,0), width=2)

        # simple text rendering inside black box
        tx = content_x0 + 16
        ty = body_y + 14
        line_h = 26
        max_w = (content_x1 - content_x0) - 32

        def wrap(text):
            # naive wrap by characters (Chinese-friendly)
            out=[]
            cur=""
            for ch in text:
                test = cur + ch
                if d.textlength(test, font=f_small) <= max_w:
                    cur = test
                else:
                    out.append(cur)
                    cur = ch
            if cur:
                out.append(cur)
            return out

        if key == "ingredients":
            groups = sec.get("groups", [])
            for g in groups:
                gname = g.get("name","")
                for ln in wrap(gname):
                    d.text((tx,ty), ln, fill=text, font=f_small); ty += line_h
                for it in g.get("items", []):
                    s = f"• {it.get('name','')} {it.get('amount','')}{it.get('unit','')}".strip()
                    for ln in wrap(s):
                        d.text((tx,ty), ln, fill=text, font=f_small); ty += line_h
                ty += 8
        else:
            for para in sec.get("text_blocks", []):
                for ln in wrap(para):
                    d.text((tx,ty), ln, fill=text, font=f_small); ty += line_h
                ty += 6
            for bullet in sec.get("list", []):
                for ln in wrap("• " + bullet):
                    d.text((tx,ty), ln, fill=text, font=f_small); ty += line_h

        div_y = body_y + content_h + 18
        d.line([x0, div_y, x1, div_y], fill=divider, width=2)
        return div_y + section_gap

    for key, h in zip(theme["sections_order"], sec_heights):
        # hide if empty
        sec = product["sections"].get(key, {})
        empty = False
        if key == "ingredients":
            empty = len(sec.get("groups", [])) == 0
        else:
            empty = (len(sec.get("text_blocks", []))==0 and len(sec.get("list", []))==0)
        if empty:
            continue
        y = draw_section(y, key, h)

    img.convert("RGB").save(out_path, "PNG")
