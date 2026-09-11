# LFO katalog

Statický katalog produktů z Google Shopping XML feedu LuxuryFashionOutlet.eu s filtrováním
podle kategorie, značky, ceny, dostupnosti a fulltextem.

- `scripts/build_feed.py` – stáhne feed a převede ho do `data/products.json` (značka se odvozuje z titulku).
- `index.html` – jednostránková aplikace bez závislostí, čte `data/products.json`.
- `.github/workflows/update-feed.yml` – každých 6 hodin obnoví data, commitne a nasadí GitHub Pages.

Lokálně:

```bash
python3 scripts/build_feed.py
python3 -m http.server 8080
```

Vložení na web (iframe):

```html
<iframe src="https://<user>.github.io/lfo-katalog/" style="width:100%;height:100vh;border:0"></iframe>
```

## Flask varianta (vlastní hosting, živý feed)

```bash
pip install -r requirements.txt
python app.py          # http://localhost:5000
```

Feed se stahuje při prvním požadavku a pak nejvýše jednou za 30 minut (`FEED_TTL` v sekundách).
`GET /api/refresh` vynutí okamžité obnovení.
