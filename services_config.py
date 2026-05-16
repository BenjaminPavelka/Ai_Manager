PORT = 7654

SERVICES = {
    "ollama": {
        "name": "Ollama Server",
        "description": "Lokální LLM inference server",
        "icon": "🦙",
        "port": 11434,
        "start_cmd": ["ollama", "serve"],
        "open_url": None,
    },
    "open-webui": {
        "name": "Open WebUI",
        "description": "Webové UI pro chat s lokálními modely",
        "icon": "🌐",
        "port": 3000,
        "start_cmd": None,
        "open_url": "http://localhost:3000",
    },
}

APPS = {
    "docker": {
        "name": "Docker",
        "icon": "🐳",
        "app_name": "Docker",
        "process": "Docker Desktop",
    },
    "github-desktop": {
        "name": "GitHub Desktop",
        "icon": "🐙",
        "app_name": "GitHub Desktop",
        "process": "GitHub Desktop",
    },
    "goose": {
        "name": "Goose",
        "icon": "🪿",
        "app_name": "Goose",
        "process": "Goose",
    },
}
