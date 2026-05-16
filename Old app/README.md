# AI Manager

Lokální webová aplikace pro správu AI nástrojů a služeb na Macu. Otevřeš jeden dashboard a máš přehled o všem — co běží, co ne, a vše můžeš zapnout/vypnout jedním klikem.

![Dark theme dashboard](https://img.shields.io/badge/theme-dark-1c2128?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask)

---

## Co aplikace umí

### Služby
- **Ollama Server** — zobrazuje stav (běží / zastaveno), umožňuje spustit nebo zastavit
- **Open WebUI** — totéž + tlačítko pro otevření v prohlížeči jedním klikem
- Stav se automaticky obnovuje každých 6 sekund

### Ollama modely
- Seznam všech nainstalovaných modelů s velikostí a datem
- **Načíst do paměti** / **Uvolnit z paměti** — každý model lze zapnout/vypnout (přes Ollama API)
- **Přidat model** — stažení nového modelu přes `ollama pull` s live progress barem
- **Smazat model** — `ollama rm` s potvrzovacím dialogem
- Pokud zkusíš načíst model a Ollama server neběží, aplikace se zeptá jestli ho má nejdřív spustit

### Mac aplikace
- Rychlé spuštění **Docker**, **GitHub Desktop**, **Goose** přímo z dashboardu
- Zobrazuje zda aplikace právě běží (zelený indikátor)

---

## Technologie

| Vrstva | Technologie |
|--------|-------------|
| Backend | Python 3 + Flask |
| Frontend | HTML + Bootstrap 5 + vanilla JS |
| Komunikace | REST API (JSON) |
| Procesy | `subprocess` + Ollama REST API |

Žádný build step, žádný bundler — vše funguje ihned po instalaci Flasku.

---

## Struktura projektu

```
├── app.py                 # Flask backend — API endpointy, správa procesů
├── templates/
│   └── index.html         # Celý frontend (single-page, dark theme)
├── requirements.txt       # Závislosti (flask, requests)
└── start.sh               # Spouštěcí skript (vytvoří venv, nainstaluje deps, spustí)
```

---

## Instalace a spuštění

### Požadavky
- Python 3.10+
- [Ollama](https://ollama.com) nainstalovaná na Macu
- Open WebUI (volitelné) — přes Docker nebo `pip install open-webui`

### Spuštění

```bash
git clone <repo-url>
cd Ai_Manager_Claud_WEB
./start.sh
```

Skript automaticky:
1. Vytvoří Python virtuální prostředí (`.venv`)
2. Nainstaluje závislosti z `requirements.txt`
3. Spustí server na `http://localhost:7654`
4. Otevře dashboard v prohlížeči

### Ruční spuštění (bez skriptu)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## Konfigurace

### Jiný port pro Open WebUI

Pokud máš Open WebUI na jiném portu než 3000, uprav v `app.py`:

```python
"open-webui": {
    "port": 3000,           # změň na svůj port
    "open_url": "http://localhost:3000",  # a tady taky
}
```

### Přidání vlastní aplikace do sekce "Aplikace"

V `app.py` přidej záznam do slovníku `APPS`:

```python
APPS = {
    "moje-app": {
        "name": "Moje App",
        "icon": "🚀",
        "app_name": "Moje App",    # název pro `open -a "Moje App"`
        "process":  "Moje App",    # název procesu pro `pgrep`
    },
    # ...
}
```

### Přidání vlastní služby

Podobně v `SERVICES`:

```python
SERVICES = {
    "moje-sluzba": {
        "name": "Moje Služba",
        "icon": "⚡",
        "port": 1234,              # port na kterém služba běží
        "start_cmd": ["prikaz", "start"],
        "open_url": "http://localhost:1234",  # nebo None
    },
}
```

---

## API endpointy

| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | `/api/status` | Stav všech služeb |
| POST | `/api/services/<id>/start` | Spustit službu |
| POST | `/api/services/<id>/stop` | Zastavit službu |
| GET | `/api/models` | Seznam Ollama modelů |
| GET | `/api/models/running` | Modely načtené v paměti |
| POST | `/api/models/<name>/load` | Načíst model do paměti |
| POST | `/api/models/<name>/unload` | Uvolnit model z paměti |
| POST | `/api/models/pull` | Stáhnout nový model |
| GET | `/api/models/pull/status/<name>` | Průběh stahování |
| DELETE | `/api/models/<name>` | Smazat model |
| GET | `/api/apps/status` | Stav Mac aplikací |
| POST | `/api/apps/<id>/open` | Otevřít Mac aplikaci |

---

## Screenshoty

Dashboard zobrazuje služby (Ollama, Open WebUI), Mac aplikace (Docker, GitHub Desktop, Goose) a seznam Ollama modelů — vše v tmavém tématu s automatickou aktualizací stavu.
