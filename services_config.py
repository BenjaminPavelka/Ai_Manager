PORT = 7654

SERVICES = {
    "ollama": {
        "name": "Ollama Server",
        "description": "Local LLM inference server",
        "icon": "🦙",
        "port": 11434,
        "docker_container": None,
        "start_cmd": ["ollama", "serve"],
        "open_url": None,
        "cli_cmd": None,
    },
    "open-webui": {
        "name": "Open WebUI",
        "description": "Web UI for chatting with local models",
        "icon": "🌐",
        "port": 3000,
        "docker_container": None,
        "start_cmd": None,
        "open_url": "http://localhost:3000",
        "cli_cmd": None,
    },
    "openosint": {
        "name": "OpenOsint",
        "description": "OSINT tool with Ollama integration",
        "icon": "🕵️",
        "port": None,
        "docker_container": "openosint",
        "start_cmd": None,
        "open_url": None,
        "cli_cmd": (
            "docker exec -it"
            " $(docker ps --filter name=openosint --format '{{.Names}}' | head -1)"
            " openosint --provider ollama"
            " --ollama-host http://host.docker.internal:11434"
            " --ollama-model qwen3.6:35b"
        ),
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
