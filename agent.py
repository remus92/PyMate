"""
Agentul: trimite mesaje la model, gestionează tool-calling-ul în buclă.
Include fallback pentru modele care scriu tool calls ca text JSON.
"""

import json
import re
from typing import Callable

import ollama

from config import (
    MODEL,
    THINKING,
    MAX_ITERATIONS,
    TEMPERATURE,
    NUM_CTX,
    NUM_PREDICT,
    NUM_GPU,
    NUM_BATCH,
    TOP_P,
    TOP_K,
    REPEAT_PENALTY,
)
from tools import TOOLS, TOOLS_SCHEMA


SYSTEM_PROMPT = """Te numești PyMate. Ești un asistent AI cu acces la internet și capabil să ruleze cod Python local.

Comportament:
- Răspunde în limba în care ți se scrie.
- La salutări simple, răspunde scurt.
- Fii concis.

Tool-uri:
- run_python(code), write_file, read_file, list_files, delete_file
- pip_install(package)
- get_weather(location): vremea curentă — FOLOSEȘTE pentru orice întrebare despre vreme
- web_search(query, region): caută pe internet
- get_news(topic, country): știri recente
- fetch_url(url): citește o pagină

REGULI CRITICE pentru informații actuale:
- Cunoștințele tale sunt din trecut. NU ai informații despre prezent.
- Pentru ORICE întrebare despre:
  • cine este/ce face o persoană publică ACUM (președinte, prim-ministru, CEO)
  • ce se întâmplă ACUM (războaie, evenimente, alegeri)
  • prețuri, cursuri valutare, versiuni de software
  • data, ora, anul curent
  • orice eveniment după 2024
  → OBLIGATORIU apelezi `web_search` sau `get_news` ÎNAINTE să răspungi.
- NU răspunde din memorie la astfel de întrebări. Răspunsul tău va fi GREȘIT.
- Dacă nu ești sigur, caută. Mai bine pierzi 3 secunde căutând decât să dai un răspuns greșit.

Exemplu corect:
  User: "Cine e președintele SUA?"
  Tu: apelezi web_search("current US president 2026") → citești rezultate → răspungi.

Exemplu GREȘIT (nu face asta):
  User: "Cine e președintele SUA?"
  Tu: "Joe Biden" (din memorie, fără căutare)

Alte reguli:
- Pentru cod: testează cu `run_python` înainte de răspunsul final.
- NU folosi sintaxă Jupyter.
- Dacă un tool returnează un rezultat valid, NU re-rula același cod.
- Pentru vreme folosește `get_weather`, nu `web_search`.
"""











def _build_options() -> dict:
    return {
        "temperature": TEMPERATURE,
        "num_ctx": NUM_CTX,
        "num_predict": NUM_PREDICT,
        "num_gpu": NUM_GPU,
        "num_batch": NUM_BATCH,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "repeat_penalty": REPEAT_PENALTY,
    }


def _normalize_args(args) -> dict:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_json_tool_calls(text: str) -> list[dict]:
    """
    Fallback: caută blocuri JSON de forma {"name": "...", "arguments": {...}}
    în text și le transformă în tool_calls.
    """
    if not text:
        return []

    calls = []

    # 1) blocuri ```json ... ``` sau ``` ... ```
    code_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = list(code_blocks)

    # 2) JSON simplu, neîncadrat în ```
    #    căutăm "{ ... "name" ... "arguments" ... }"
    if not candidates:
        # găsim toate acoladele echilibrate
        depth = 0
        start = None
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(text[start:i + 1])
                    start = None

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue

        # format {"name": ..., "arguments": {...}}
        if isinstance(obj, dict) and "name" in obj and "arguments" in obj:
            if obj["name"] in TOOLS:
                calls.append({
                    "function": {
                        "name": obj["name"],
                        "arguments": obj["arguments"],
                    }
                })
        # format {"function": {"name": ..., "arguments": ...}}
        elif isinstance(obj, dict) and "function" in obj:
            fn = obj["function"]
            if isinstance(fn, dict) and fn.get("name") in TOOLS:
                calls.append({"function": fn})

    return calls


def _execute_tool_call(tc: dict) -> tuple[str, dict, str]:
    """Execută un tool call, returnează (nume, args, rezultat)."""
    fn = tc.get("function", {})
    fn_name = fn.get("name", "")
    args = _normalize_args(fn.get("arguments", {}))

    if fn_name not in TOOLS:
        result = f"EROARE: tool necunoscut '{fn_name}'"
    else:
        try:
            result = TOOLS[fn_name](**args)
        except TypeError as e:
            result = f"EROARE argumente pentru {fn_name}: {e}"
        except Exception as e:
            result = f"EROARE la {fn_name}: {type(e).__name__}: {e}"

    return fn_name, args, str(result)


def chat(
    messages: list[dict],
    on_tool_call: Callable[[str, dict, str], None] | None = None,
) -> str:
    if not messages or messages[0].get("role") != "system":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for _ in range(MAX_ITERATIONS):
        try:
            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                options=_build_options(),
            )
        except Exception as e:
            return f"EROARE la apelarea modelului: {e}"

        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content", "") or ""

        # FALLBACK: dacă modelul a scris tool call-ul ca text JSON
        if not tool_calls and content:
            extracted = _extract_json_tool_calls(content)
            if extracted:
                tool_calls = extracted
                # curățăm textul de blocurile JSON rămase, ca să nu le vadă userul
                # (opțional, păstrăm explicațiile)
                content = re.sub(r"```(?:json)?\s*\{.*?\}\s*```", "", content, flags=re.DOTALL).strip()
                content = re.sub(
                    r"\{\s*\"name\"\s*:\s*\".*?\"\s*,\s*\"arguments\"\s*:\s*\{.*?\}\s*\}",
                    "", content, flags=re.DOTALL
                ).strip()

        if not tool_calls:
            return content.strip() or "(răspuns gol)"

        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            fn_name, args, result = _execute_tool_call(tc)
            if on_tool_call:
                try:
                    on_tool_call(fn_name, args, result)
                except Exception:
                    pass
            messages.append({
                "role": "tool",
                "content": result,
            })

    return "Am atins limita de iterații fără un răspuns final."
