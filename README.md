# 🤖 AI Manager

Nativní macOS menu-bar aplikace pro správu lokálních AI služeb, modelů a nástrojů.  
Žije v menu baru – vždy po ruce, žádné zbytečné okno.

---

## Co umí

| Funkce | Popis |
|---|---|
| **Menu bar ikonka** | 🤖 když Ollama běží a model je načtený, 🌙 když ne |
| **Stav služeb** | Zobrazuje Ollama Server a Open WebUI (● Běží / ○ Zastaveno) |
| **Spustit / Zastavit** | Ovládání služeb přímo z menu baru |
| **Modely v paměti** | Výpis všech aktuálně načtených Ollama modelů jménem |
| **Mac Aplikace** | Docker, GitHub Desktop, Goose – status + klik = otevřít |
| **Dashboard** | Otevře webové UI v prohlížeči (localhost:7654) |
| **Notifikace** | macOS upozornění když služba spadne nebo se znovu spustí |

---

## Architektura

```
main.py            – vstupní bod: spouští Flask + rumps na hlavním vlákně
backend.py         – Flask REST API (všechny /api/ endpointy)
menu_bar.py        – rumps menu bar aplikace + crash monitor na pozadí
services_config.py – centrální konfigurace služeb a aplikací
templates/
  index.html       – webový dashboard (HTML/CSS/JS, Bootstrap 5)
resources/         – sem patří AppIcon.icns pro build
start.sh           – rychlý start přes virtuální prostředí
build.sh           – sestaví .app bundle pomocí py2app
Old app/           – původní čistě webová verze (bez menu baru)
```

### Jak to funguje uvnitř

- **Flask** běží v daemon vlákně na portu `7654`
- **rumps** drží hlavní vlákno (macOS to vyžaduje pro GUI)
- **Menu refresh** probíhá každých 8 sekund (timer na hlavním vlákně)
- **Crash monitor** běží v samostatném daemon vlákně, polluje každých 10 sekund a posílá macOS notifikace při změně stavu

---

## Požadavky

- macOS 12+
- Python 3.11+ (doporučeno přes Homebrew: `brew install python`)
- [Ollama](https://ollama.ai) nainstalovaná lokálně

---

## Instalace a spuštění

### 1. Naklonuj repozitář

```bash
git clone <repo-url>
cd Ai_Manager_Claud_APP
```

### 2. Vytvoř virtuální prostředí

> Složka může obsahovat `:` ve jméně (Dropbox), proto se venv vytváří mimo ni.

```bash
python3 -m venv ~/ai-manager-venv
~/ai-manager-venv/bin/pip install flask rumps pyobjc-framework-Cocoa
```

### 3. Spusť aplikaci

```bash
./start.sh
```

Ikonka 🌙 / 🤖 se objeví v menu baru. Dashboard je dostupný na [localhost:7654](http://localhost:7654).

---

## Build jako .app (volitelné)

Vytvoří samostatnou aplikaci kterou lze přidat do `/Applications`:

```bash
~/ai-manager-venv/bin/pip install py2app
./build.sh
open "dist/AI Manager.app"
```

> **Ikona:** vlož soubor `resources/AppIcon.icns` (1024×1024 px).  
> Pokud soubor chybí, odstraň z `setup.py` řádek `"iconfile": ...`.

### Automatické spouštění po přihlášení

Po přesunutí do `/Applications`:  
**Nastavení → Obecné → Přihlašovací položky** → přidat `AI Manager.app`

---

## Přidání nové služby

V [`services_config.py`](services_config.py) přidej záznam do `SERVICES`:

```python
"moje-sluzba": {
    "name":        "Moje Služba",
    "description": "Co dělá",
    "icon":        "🔧",
    "port":        8888,
    "start_cmd":   ["moje-sluzba", "--start"],
    "open_url":    "http://localhost:8888",  # nebo None
},
```

Menu bar, crash monitor i notifikace se přizpůsobí automaticky.

## Přidání nové Mac aplikace

V [`services_config.py`](services_config.py) přidej záznam do `APPS`:

```python
"moje-app": {
    "name":     "Moje App",
    "icon":     "🛠",
    "app_name": "Moje App",      # název pro `open -a`
    "process":  "Moje App",      # název procesu pro pgrep
},
```
