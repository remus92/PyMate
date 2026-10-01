"""
Tool-urile pe care modelul le poate apela: execuție cod, citire/scriere fișiere.
"""

import subprocess
import sys
from pathlib import Path

from config import WORKSPACE_DIR

# Workspace-ul absolut (sandbox pentru fișiere)
WORKSPACE = Path(WORKSPACE_DIR).resolve()
WORKSPACE.mkdir(exist_ok=True, parents=True)


def _safe_path(path: str) -> Path | None:
    """Returnează calea absolută dacă e în workspace, altfel None."""
    p = (WORKSPACE / path).resolve()
    if not str(p).startswith(str(WORKSPACE)):
        return None
    return p


def run_python(code: str) -> str:
    """Execută cod Python și returnează stdout/stderr."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=WORKSPACE,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()

        if result.returncode == 0:
            return f"OK\n{out}" if out else "OK (fără output)"
        return f"EROARE (exit {result.returncode}):\n{err}"
    except subprocess.TimeoutExpired:
        return "EROARE: timeout (30s depășit)"
    except Exception as e:
        return f"EROARE: {type(e).__name__}: {e}"


def read_file(path: str) -> str:
    """Citește un fișier din workspace."""
    p = _safe_path(path)
    if p is None:
        return "EROARE: acces în afara workspace-ului"
    if not p.exists():
        return f"EROARE: {path} nu există"
    if not p.is_file():
        return f"EROARE: {path} nu e fișier"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"EROARE la citire: {e}"


def write_file(path: str, content: str) -> str:
    """Scrie un fișier în workspace (suprascrie dacă există)."""
    p = _safe_path(path)
    if p is None:
        return "EROARE: acces în afara workspace-ului"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK: scris {len(content)} caractere în {path}"
    except Exception as e:
        return f"EROARE la scriere: {e}"


def list_files() -> str:
    """Listează fișierele din workspace."""
    files = [
        str(f.relative_to(WORKSPACE))
        for f in WORKSPACE.rglob("*")
        if f.is_file()
    ]
    return "\n".join(sorted(files)) if files else "(workspace gol)"


def delete_file(path: str) -> str:
    """Șterge un fișier din workspace."""
    p = _safe_path(path)
    if p is None:
        return "EROARE: acces în afara workspace-ului"
    if not p.exists():
        return f"EROARE: {path} nu există"
    try:
        p.unlink()
        return f"OK: șters {path}"
    except Exception as e:
        return f"EROARE la ștergere: {e}"


# Mapare nume -> funcție (dispatcher)
TOOLS = {
    "run_python": run_python,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "delete_file": delete_file,
}


# Schema tool-urilor pentru Ollama (OpenAI-compatible)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Execută cod Python și returnează stdout/stderr. "
                "Folosește pentru a testa orice cod scris înainte de a-l da utilizatorului."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Cod Python complet de executat.",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Citește conținutul unui fișier din workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Cale relativă față de workspace.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Scrie (sau suprascrie) un fișier în workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Listează fișierele din workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Șterge un fișier din workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
]



def pip_install(package: str) -> str:
    """Instalează unul sau mai multe pachete pip în mediul curent."""
    import sys
    packages = package.replace(",", " ").split()
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", *packages],
        capture_output=True, text=True, timeout=180,
        cwd=WORKSPACE,
    )
    out = (r.stdout or "") + (r.stderr or "")
    return out[-1200:] if r.returncode == 0 else f"EROARE:\n{out[-1200:]}"


def web_search(query: str, max_results: int = 5, region: str = "wt-wt") -> str:
    """Caută pe internet prin DuckDuckGo.
    region: 'wt-wt' = worldwide, 'ro-ro' = România, 'fr-fr' = Franța, 'us-en' = SUA, 'de-de' = Germania
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "EROARE: rulează pip_install('ddgs')"

    try:
        results = DDGS().text(query, max_results=max_results, region=region)
        if not results:
            return f"Niciun rezultat pentru: {query}"
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title','')}\n   {r.get('href','')}\n   {r.get('body','')}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"EROARE la căutare: {type(e).__name__}: {e}"


def get_weather(location: str) -> str:
    """Returnează vremea curentă pentru un oraș, prin wttr.in (fără API key)."""
    try:
        import requests
    except ImportError:
        return "EROARE: rulează pip_install('requests')"
    try:
        url = f"https://wttr.in/{location}?format=j1"
        r = requests.get(url, timeout=15, headers={"User-Agent": "curl/8.0"})
        r.raise_for_status()
        data = r.json()

        current = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        city = area.get("areaName", [{}])[0].get("value", location)
        country = area.get("country", [{}])[0].get("value", "")

        desc = current["weatherDesc"][0]["value"]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        wind_dir = current["winddir16Point"]

        return (
            f"Vremea în {city}, {country}:\n"
            f"- Stare: {desc}\n"
            f"- Temperatură: {temp}°C (resimțită: {feels}°C)\n"
            f"- Umiditate: {humidity}%\n"
            f"- Vânt: {wind} km/h din {wind_dir}"
        )
    except Exception as e:
        return f"EROARE la vreme: {type(e).__name__}: {e}"


def fetch_url(url: str, max_chars: int = 3000) -> str:
    """Descarcă o pagină web și returnează textul principal."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return "EROARE: lipsește requests sau beautifulsoup4."
    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)
        return text[:max_chars] + ("\n...[trunchiat]" if len(text) > max_chars else "")
    except Exception as e:
        return f"EROARE la fetch: {type(e).__name__}: {e}"


TOOLS["pip_install"] = pip_install
TOOLS["web_search"] = web_search
TOOLS["get_weather"] = get_weather
TOOLS["fetch_url"] = fetch_url

TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "pip_install",
        "description": "Instalează pachete pip. Folosește când lipsește un modul.",
        "parameters": {
            "type": "object",
            "properties": {"package": {"type": "string"}},
            "required": ["package"]
        }
    }
})

TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Returnează vremea curentă pentru un oraș. Folosește pentru 'ce vreme e la X'.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Numele orașului (ex: Paris, București, London)"}
            },
            "required": ["location"]
        }
    }
})

TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Caută pe internet. Pentru vreme preferă get_weather.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
                "region": {"type": "string", "description": "'wt-wt' worldwide, 'ro-ro' România, 'fr-fr' Franța"}
            },
            "required": ["query"]
        }
    }
})

TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "fetch_url",
        "description": "Descarcă textul unei pagini web.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    }
})
