#!/usr/bin/env python3
"""Stáhne Google Shopping XML feed a převede ho na data/products.json pro katalog."""
import json, re, sys, urllib.request, datetime, pathlib, socket
import xml.etree.ElementTree as ET

FEED_URL = "https://www.luxuryfashionoutlet.eu/fotky61494/xml/google_nakupy.xml"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "products.json"
NS = {"g": "http://base.google.com/ns/1.0"}

# Delší názvy první, aby "ARMANI EXCHANGE" vyhrál nad "ARMANI".
BRANDS = [
    "ALEXANDER WANG", "ANIYE BY", "ARMANI EXCHANGE", "EMPORIO ARMANI", "ARMANI",
    "BALENCIAGA", "BALMAIN", "BLAUER", "HUGO BOSS", "BOSS", "CALVIN KLEIN", "CAMP DAVID",
    "CARLO COLUCCI", "JUST CAVALLI", "ROBERTO CAVALLI", "CAVALLI", "CECIL", "COCCINELLE",
    "DESIGUAL", "DIESEL", "DKNY", "DOLCE & GABBANA", "DSQUARED2", "DSQUARED", "EMILIO PUCCI",
    "FERRARI", "FRACOMINA MILANO", "FRACOMINA", "FURLA", "GANT", "GAP", "GAUDÍ", "GAUDI",
    "GIVENCHY", "GUESS", "JOHN GALLIANO", "KARL LAGERFELD", "KENZO", "LA MARTINA",
    "LAMBORGHINI", "LEE", "LEVIS", "LEVI'S", "LIU JO", "LOVE MOSCHINO", "MOSCHINO",
    "MARKS & SPENCER", "MARNI", "MICHAEL KORS", "MISSGUIDED", "MUSTANG", "NAPAPIJRI",
    "PEPE JEANS", "PHILIPP PLEIN", "PINKO", "PRADA", "REPLAY", "STREET ONE", "TIMBERLAND",
    "TOMMY HILFIGER", "TRUSSARDI", "TWINSET MILANO", "TWINSET", "VALENTINO", "VERSACE",
    "VICTORIA BECKHAM", "VILA", "VERO MODA", "ZARA",
]
BRAND_PATTERNS = [(b, re.compile(r"(?<![A-Z0-9])" + re.escape(b) + r"(?![A-Z0-9])", re.I)) for b in BRANDS]


def text(item, tag):
    el = item.find(tag, NS) if ":" in tag else item.find(tag)
    return (el.text or "").strip() if el is not None else ""


def parse_price(s):
    m = re.match(r"([\d.,]+)", s or "")
    if not m:
        return 0.0
    return float(m.group(1).replace(",", "."))


def detect_brand(title):
    for name, pat in BRAND_PATTERNS:
        if pat.search(title):
            return name
    return ""


PACK_RE = re.compile(r"(\d+)\s*(?:ks|pcs|kusů|kusy|kus)\b", re.I)


def detect_pack(description, title):
    m = PACK_RE.search(description) or PACK_RE.search(title)
    return int(m.group(1)) if m else None


def split_title(title):
    # "GUESS jeans (Velkoobchod džíny Guess)" -> name, subtitle
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", title, re.S)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title.strip(), ""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else FEED_URL
    if src.startswith("http"):
        # GitHub runnery nemají IPv6 – vynutíme IPv4 (host má A i AAAA záznam).
        _orig = socket.getaddrinfo
        socket.getaddrinfo = lambda *a, **k: [r for r in _orig(*a, **k) if r[0] == socket.AF_INET] or _orig(*a, **k)
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 (compatible; lfo-katalog-bot/1.0)"})
        last = None
        for attempt in range(3):
            try:
                raw = urllib.request.urlopen(req, timeout=60).read()
                break
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"pokus {attempt + 1} selhal: {e}", file=sys.stderr)
        else:
            raise last
    else:
        raw = pathlib.Path(src).read_bytes()

    root = ET.fromstring(raw)
    products = []
    for item in root.iter("item"):
        title = text(item, "g:title")
        name, subtitle = split_title(title)
        images = [text(item, "g:image_link")] + [
            (el.text or "").strip() for el in item.findall("g:additional_image_link", NS)
        ]
        images = [i for i in images if i]
        cat_path = [c.strip() for c in text(item, "g:product_type").split(">") if c.strip()]
        price = parse_price(text(item, "g:price"))
        description = text(item, "g:description")
        products.append({
            "id": text(item, "g:id"),
            "title": title,
            "name": name,
            "subtitle": subtitle,
            "brand": detect_brand(title),
            "category": cat_path,
            "price": price,
            "currency": (text(item, "g:price").split() + ["CZK"])[1] if price else "CZK",
            "inStock": text(item, "g:availability").lower() == "in stock",
            "link": text(item, "link"),
            "image": images[0] if images else "",
            "images": images,
            "pack": detect_pack(description, title),
            "description": description,
        })

    out = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": FEED_URL,
        "count": len(products),
        "products": products,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OK: {len(products)} products -> {OUT}")


if __name__ == "__main__":
    main()
