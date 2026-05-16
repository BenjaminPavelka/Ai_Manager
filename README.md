# 🤖 AI Manager

[![Build & Release](https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP/actions/workflows/release.yml/badge.svg)](https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP/actions/workflows/release.yml)
[![Latest Release](https://img.shields.io/github/v/release/BenjaminPavelka/Ai_Manager_Claud_APP)](https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-12%2B-blue?logo=apple)](https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP/releases/latest)

Nativní macOS menu-bar aplikace pro správu lokálních AI služeb, modelů a nástrojů.  
Žije v menu baru – vždy po ruce, žádné zbytečné okno.

---

## ⬇️ Stažení

**[→ Stáhnout nejnovější verzi](https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP/releases/latest)**

1. Stáhni `AI.Manager.zip` z Releases
2. Rozbal a přetáhni `AI Manager.app` do `/Applications`
3. Pravý klik na app → **Otevřít** (první spuštění – obejde macOS security dialog)

> **Požadavek:** [Ollama](https://ollama.ai) nainstalovaná lokálně.

---

## Co umí

| Funkce | Popis |
|---|---|
| **Menu bar ikonka** | 🤖 když Ollama běží a model je načtený, 🌙 jinak |
| **Stav služeb** | Ollama Server a Open WebUI – ● Běží / ○ Zastaveno |
| **Spustit / Zastavit** | Ovládání služeb přímo z menu baru |
| **Modely v paměti** | Výpis všech načtených Ollama modelů jménem |
| **Mac Aplikace** | Docker, GitHub Desktop, Goose – stav + klik = otevřít |
| **Dashboard** | Webové UI v prohlížeči na localhost:7654 |
| **Notifikace** | macOS upozornění při pádu nebo spuštění služby |

---

## Architektura

```
main.py            – vstupní bod: Flask vlákno + rumps na hlavním vlákně
backend.py         – Flask REST API (/api/* endpointy)
menu_bar.py        – rumps menu bar + crash monitor
services_config.py – konfigurace služeb a aplikací (jedno místo)
version.py         – číslo verze
templates/
  index.html       – webový dashboard (Bootstrap 5)
resources/         – AppIcon.icns pro build
.github/workflows/
  release.yml      – GitHub Actions: build + GitHub Release při tagu
```

**Jak to funguje:**
- Flask běží v daemon vlákně na portu `7654`
- rumps drží hlavní vlákno (macOS požadavek pro GUI)
- Menu se refreshuje každých 8 s, crash monitor polluje každých 10 s
- Data (poznámky k modelům) se ukládají do `~/Library/Application Support/AI Manager/`

---

## Vývoj

### Požadavky

- macOS 12+
- Python 3.11+ (`brew install python`)
- [Ollama](https://ollama.ai)

### Instalace

```bash
git clone https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP.git
cd Ai_Manager_Claud_APP
./install.sh
```

`install.sh` vytvoří virtualní prostředí, nainstaluje závislosti a zaregistruje LaunchAgent (autostart po přihlášení).

### Ruční spuštění

```bash
./start.sh
```

### Správa LaunchAgent

```bash
# Zastavit
launchctl unload ~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist

# Spustit
launchctl load ~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist

# Log
tail -f ~/Library/Logs/AIManager.log
```

---

## Vydání nové verze

```bash
# 1. Uprav číslo verze
echo 'VERSION = "0.2.0"' > version.py

# 2. Commit + tag
git add version.py
git commit -m "v0.2.0"
git tag v0.2.0
git push && git push --tags
```

GitHub Actions automaticky sestaví `.app` a vytvoří GitHub Release s přiloženým `.zip`.

### Sémantické verzování

| Změna verze | Kdy |
|---|---|
| `0.1.0 → 0.1.1` | Oprava chyby |
| `0.1.x → 0.2.0` | Nová funkce |
| `0.x.x → 1.0.0` | Stabilní release |

---

## Přidání nové služby

V [`services_config.py`](services_config.py):

```python
"moje-sluzba": {
    "name":        "Moje Služba",
    "description": "Co dělá",
    "icon":        "🔧",
    "port":        8888,
    "start_cmd":   ["moje-sluzba", "--start"],
    "open_url":    "http://localhost:8888",
},
```

Menu bar, crash monitor i notifikace se přizpůsobí automaticky.

## Přidání nové Mac aplikace

V [`services_config.py`](services_config.py):

```python
"moje-app": {
    "name":     "Moje App",
    "icon":     "🛠",
    "app_name": "Moje App",
    "process":  "Moje App",
},
```

---

## Stará verze

Původní čistě webová verze (Flask + prohlížeč) je zachována v [`Old app/`](Old%20app/).
