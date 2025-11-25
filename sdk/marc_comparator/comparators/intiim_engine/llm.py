# marc_diff/llm.py
from __future__ import annotations
from typing import Optional, Literal, Dict, Tuple

import hashlib
import os
import requests
import threading

try:
    from llama_cpp import Llama
    _LLAMA_CPP_IMPORT_ERROR = None
except ImportError as exc:
    Llama = None
    _LLAMA_CPP_IMPORT_ERROR = exc


# Configuration

# Ollama (HTTP server)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "20"))

os.environ["LLM_BACKEND"] = "llama_cpp"
os.environ["LLM_LLAMA_MODEL"] = "path_to_model.gguf"

LLM_LLAMA_MODEL = (
    os.getenv("LLM_LLAMA_MODEL")
    or os.getenv("LLM_LLAMA_MODEL_PATH")
    or os.getenv("LLAMA_CPP_MODEL")
    or os.getenv("LLM_MODEL")
    or ""
).strip()

LLM_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "64"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))
LLM_REPETITION_PENALTY = float(os.getenv("LLM_REPETITION_PENALTY", "1.0"))
LLM_DO_SAMPLE_ENV = os.getenv("LLM_DO_SAMPLE")
LLM_SEED = int(os.getenv("LLM_SEED", "0"))

DEFAULT_STOPS = (
    os.getenv("LLM_STOPS", "").split("|")
    if os.getenv("LLM_STOPS")
    else []
)

LLM_LLAMA_CONTEXT = int(os.getenv("LLM_LLAMA_CONTEXT", "4096"))
LLM_LLAMA_THREADS = int(os.getenv("LLM_LLAMA_THREADS", "0"))
LLM_LLAMA_BATCH = int(os.getenv("LLM_LLAMA_BATCH", "512"))
LLM_LLAMA_GPU_LAYERS = int(os.getenv("LLM_LLAMA_N_GPU_LAYERS", os.getenv("LLM_LLAMA_GPU_LAYERS", "-1")))
LLM_LLAMA_ROPE_SCALE = float(os.getenv("LLM_LLAMA_ROPE_SCALE", "1.0"))
LLM_LLAMA_ROPE_BASE  = float(os.getenv("LLM_LLAMA_ROPE_BASE", "0.0"))

_BACKEND_ENV_RAW = (os.getenv("LLM_BACKEND") or os.getenv("LLM_PROVIDER") or "").strip()

BackendLiteral = Literal["ollama", "llama_cpp"]

_CACHE: Dict[str, str] = {}
_LLAMA_MODEL = None
_LLAMA_LOCK = threading.Lock()




def _normalize_backend(value: Optional[str]) -> BackendLiteral:
    candidate = (value or "").strip().lower()
    if not candidate and _BACKEND_ENV_RAW:
        candidate = _BACKEND_ENV_RAW.strip().lower()
    aliases = {
        "llama_cpp": "llama_cpp",
        "llama-cpp": "llama_cpp",
        "llamacpp": "llama_cpp",
        "llama": "llama_cpp",
        "ollama": "ollama",
        "api": "ollama",
    }
    if not candidate:
        candidate = "ollama"
    candidate = aliases.get(candidate, candidate)
    if candidate not in {"ollama", "llama_cpp"}:
        raise ValueError("Unsupported LLM backend. Use 'ollama' or 'llama_cpp'.")
    return candidate


def _has_llama() -> bool:
    return Llama is not None and bool(LLM_LLAMA_MODEL)


LLM_BACKEND_DEFAULT = _normalize_backend(None)


def _ensure_llama_available() -> None:
    if Llama is None:
        raise RuntimeError(
            "llama_cpp backend requested but llama-cpp-python is not installed. "
            "Install with 'pip install llama-cpp-python'."
        ) from _LLAMA_CPP_IMPORT_ERROR
    if not LLM_LLAMA_MODEL:
        raise RuntimeError(
            "llama_cpp backend requested but no model path is configured. "
            "Set LLM_LLAMA_MODEL (or LLM_LLAMA_MODEL_PATH / LLAMA_CPP_MODEL) to your .gguf file."
        )


def _resolve_backend(value: Optional[BackendLiteral]) -> str:
    backend = _normalize_backend(value)
    if backend == "llama_cpp":
        _ensure_llama_available()
        return "llama_cpp"
    if backend == "ollama":
        return "ollama"
    raise ValueError(f"Unsupported LLM backend '{value}'. Expected 'ollama' or 'llama_cpp'.")



def _load_llama_model():
    global _LLAMA_MODEL
    if _LLAMA_MODEL is not None:
        return _LLAMA_MODEL
    with _LLAMA_LOCK:
        if _LLAMA_MODEL is not None:
            return _LLAMA_MODEL
        _ensure_llama_available()

        model_path = LLM_LLAMA_MODEL
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"llama.cpp model file not found: {model_path}")
        if not model_path.endswith(".gguf"):
            raise RuntimeError(f"Expected a .gguf file, got: {model_path}")

        kwargs: Dict[str, object] = {
            "model_path": model_path,
            "n_ctx": LLM_LLAMA_CONTEXT,
            "n_batch": LLM_LLAMA_BATCH,
            "n_gpu_layers": LLM_LLAMA_GPU_LAYERS, 
            "verbose": False,
            "seed": LLM_SEED,
        }
        if LLM_LLAMA_THREADS > 0:
            kwargs["n_threads"] = LLM_LLAMA_THREADS
        if LLM_LLAMA_ROPE_BASE > 0:
            kwargs["rope_freq_base"] = LLM_LLAMA_ROPE_BASE
        if LLM_LLAMA_ROPE_SCALE != 1.0:
            kwargs["rope_freq_scale"] = LLM_LLAMA_ROPE_SCALE

        llama = Llama(**kwargs)
        _LLAMA_MODEL = llama
        return _LLAMA_MODEL


def _sampling_params() -> Tuple[bool, float, float]:
    """
    Decide deterministic vs sampling based on env/temperature.
    Returns: (do_sample, temperature, top_p)
    """
    do_sample_env = (LLM_DO_SAMPLE_ENV or "").strip().lower()
    if do_sample_env in {"true", "false"}:
        do_sample = (do_sample_env == "true")
    else:
        do_sample = LLM_TEMPERATURE > 0.0

    temperature = max(LLM_TEMPERATURE, 1e-6) if do_sample else 0.0
    top_p = LLM_TOP_P if do_sample else 1.0
    return do_sample, temperature, top_p


def _llama_generate(prompt: str) -> str:
    llama = _load_llama_model()
    _, temperature, top_p = _sampling_params()

    try:
        out = llama.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=LLM_MAX_NEW_TOKENS,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=LLM_REPETITION_PENALTY,
            stop=DEFAULT_STOPS,
            stream=False,
        )
        text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
        if text:
            return text
    except Exception:
        pass

    out = llama.create_completion(
        prompt=prompt,
        max_tokens=LLM_MAX_NEW_TOKENS,
        temperature=temperature,
        top_p=top_p,
        repeat_penalty=LLM_REPETITION_PENALTY,
        stop=DEFAULT_STOPS,
        stream=False,
    )
    return (out.get("choices") or [{}])[0].get("text", "") or ""

def _ollama_generate(prompt: str) -> str:
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=OLLAMA_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def _cache_key(prompt: str, backend: str) -> str:
    salt = f"{backend}|{LLM_MAX_NEW_TOKENS}|{LLM_TEMPERATURE}|{LLM_TOP_P}|{LLM_REPETITION_PENALTY}|{','.join(DEFAULT_STOPS)}"
    return f"{salt}:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()}"


def generate_text(prompt: str, *, backend: Optional[BackendLiteral] = None) -> str:
    resolved = _resolve_backend(backend)
    allow_fallback = backend is None
    key = _cache_key(prompt, resolved)
    if key in _CACHE:
        return _CACHE[key]

    try:
        if resolved == "ollama":
            txt = _ollama_generate(prompt)
        else:
            txt = _llama_generate(prompt)
    except Exception:
        if resolved == "ollama" and allow_fallback and _has_llama():
            resolved = "llama_cpp"
            key = _cache_key(prompt, resolved)
            if key in _CACHE:
                return _CACHE[key]
            txt = _llama_generate(prompt)
        elif resolved == "llama_cpp" and allow_fallback:
            resolved = "ollama"
            key = _cache_key(prompt, resolved)
            if key in _CACHE:
                return _CACHE[key]
            txt = _ollama_generate(prompt)
        else:
            raise

    _CACHE[key] = txt
    return txt


def ollama_generate(prompt: str) -> str:
    return generate_text(prompt, backend="ollama")


def load_llm(*, backend: Optional[BackendLiteral] = None) -> None:
    resolved = _resolve_backend(backend)
    allow_fallback = backend is None
    if resolved == "llama_cpp":
        try:
            _load_llama_model()
        except Exception:
            if allow_fallback:
                requests.get(f"{OLLAMA_URL}/api/tags", timeout=OLLAMA_TIMEOUT).raise_for_status()
            else:
                raise
    else: 
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=OLLAMA_TIMEOUT).raise_for_status()
        except Exception:
            if allow_fallback and _has_llama():
                _load_llama_model()
            else:
                raise


def llm_health(*, backend: Optional[BackendLiteral] = None) -> dict:
    resolved = _resolve_backend(backend)
    allow_fallback = backend is None
    fallback_used = False

    if resolved == "ollama":
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=OLLAMA_TIMEOUT)
            r.raise_for_status()
            data = r.json() if r.content else {}
            return {
                "status": "ok",
                "backend": "ollama",
                "default_backend": LLM_BACKEND_DEFAULT,
                "ollama_url": OLLAMA_URL,
                "requested_model": OLLAMA_MODEL,
                "models": [m.get("name") for m in data.get("models", [])] if isinstance(data, dict) else [],
            }
        except Exception:
            if not allow_fallback or not _has_llama():
                raise
            resolved = "llama_cpp"
            fallback_used = True

    llama = _load_llama_model()
    model_meta = getattr(llama, "metadata", None)
    details = {
        "status": "ok",
        "backend": "llama_cpp",
        "default_backend": LLM_BACKEND_DEFAULT,
        "model_path": LLM_LLAMA_MODEL,
        "context_length": LLM_LLAMA_CONTEXT,
        "n_threads": LLM_LLAMA_THREADS,
        "n_batch": LLM_LLAMA_BATCH,
        "n_gpu_layers": LLM_LLAMA_GPU_LAYERS,
        "rope_freq_scale": LLM_LLAMA_ROPE_SCALE,
        "rope_freq_base": LLM_LLAMA_ROPE_BASE,
        "seed": LLM_SEED,
        "stops": DEFAULT_STOPS,
        "model_meta": model_meta or {},
    }
    if fallback_used:
        details["fallback_from"] = "ollama"
    return details


# Prompts

ROLE_HINTS = {
    "relator_code": (
        "Subfield $4 contains a 3-letter MARC relator code (case-insensitive), "
        "e.g., aut (author), trl (translator), edt (editor), nrt (narrator).\n"
        "Rules:\n"
        "• If A and B are different valid codes with different meanings → INCORRECT.\n"
        "• If one is a valid code and the other is the spelled-out equivalent (same meaning) → NON_STANDARDIZED.\n"
        "• Case-only or spacing-only differences in the same code → TYPO or IDENTICAL.\n"
    ),
    "language_code": (
        "Language codes are ISO 639-2/3 style (3 letters). Same code ≈ same meaning. "
        "Different codes → INCORRECT unless clearly synonyms/aliases for the same language (rare)."
    ),
    "rda_content_code": (
        "RDA content codes in 336$ b are controlled 3-letter codes (e.g., txt, spw). "
        "Different codes → INCORRECT, unless one side is the spelled-out label of the same code → NON_STANDARDIZED."
    ),
    "code_source": (
        "Subfield $2 is a source/authority code (e.g., czenas, eczenas, rdacontent). "
        "Case-only differences → TYPO. Different recognized sources reflect different authority systems → usually INCORRECT, "
        "unless they are known aliases for the same source → NON_STANDARDIZED."
    ),
    "udc": (
        "UDC notation in 080$a (e.g., 811.162.3, 811.162.3'243, (075), (07.062)81). "
        "Base number equality with auxiliaries added in one side indicates ADDITION; "
        "comparing a single subfield value of differing numbers is INCORRECT (not NON_STANDARDIZED)."
    ),
    "generic": (
        "Decide strictly by meaning:\n"
        "• TYPO = minor orthography/diacritics/punctuation only.\n"
        "• INCOMPLETE = one value is a subset/omission of the other.\n"
        "• NON_STANDARDIZED = same meaning, different form (abbrev, ISBD punctuation, word order, code vs label).\n"
        "• INCORRECT = different meaning/content.\n"
    ),
}

def _hint_for(role: str) -> str:
    return ROLE_HINTS.get(role, ROLE_HINTS["generic"])

def _render_context(tag: str, code: str|None, fieldA: Optional[str], fieldB: Optional[str], a: str, b: str) -> str:
    fa = fieldA or f"{tag} ${code or '?'} {a}"
    fb = fieldB or f"{tag} ${code or '?'} {b}"
    return f"Full field (Record A): {fa}\nFull field (Record B): {fb}\nSubfield values compared: A='{a}' vs B='{b}'."

def _parse_yes_no_response(txt: str) -> Optional[bool]:
    up = (txt or "").strip().upper()
    if not up:
        return None
    if "YES" in up and "NO" not in up:
        return True
    if "NO" in up and "YES" not in up:
        return False
    first = up.replace("*", " ").replace("_", " ").split()
    if not first:
        return None
    token = first[0]
    if token == "YES":
        return True
    if token == "NO":
        return False
    return None

def _ask_yes_no(role: str, tag: str, code: str|None, a: str, b: str,
                label: str, fieldA: Optional[str], fieldB: Optional[str],
                backend: Optional[BackendLiteral]) -> Optional[bool]:
    ctx = _render_context(tag, code, fieldA, fieldB, a, b)
    prompt = (
        "You are a MARC21 record QA assistant.\n"
        f"Role: {role}\n{_hint_for(role)}\n"
        f"{ctx}\n\n"
        f"Question: Is the difference BEST described as {label}? "
        "Answer strictly with a single token: YES or NO. If uncertain, answer NO."
    )
    try:
        txt = generate_text(prompt, backend=backend)
        return _parse_yes_no_response(txt)
    except Exception:
        return None

def _ask_best(role: str, tag: str, code: str|None, a: str, b: str,
              fieldA: Optional[str], fieldB: Optional[str],
              backend: Optional[BackendLiteral]) -> tuple[Optional[str], str]:
    ctx = _render_context(tag, code, fieldA, fieldB, a, b)
    prompt = (
        "You are a MARC21 record QA assistant.\n"
        f"Role: {role}\n{_hint_for(role)}\n"
        f"{ctx}\n\n"
        "Pick the single best category: IDENTICAL, TYPO, INCOMPLETE, NON_STANDARDIZED, INCORRECT.\n"
        "Answer with exactly one token only."
    )
    try:
        raw = generate_text(prompt, backend=backend).strip().upper()
        for k in ["IDENTICAL","TYPO","INCOMPLETE","NON_STANDARDIZED","INCORRECT"]:
            if k in raw:
                return k, raw
        return None, raw
    except Exception:
        return None, ""

CATEGORY = Literal["IDENTICAL","TYPO","INCOMPLETE","NON_STANDARDIZED","INCORRECT"]

def ask_same_written_differently(a: str, b: str, role: str, tag: str, code: str|None,
                                 fieldA: Optional[str] = None, fieldB: Optional[str] = None,
                                 *, backend: Optional[BackendLiteral] = None) -> dict:
    ctx = _render_context(tag, code, fieldA, fieldB, a, b)
    prompt = (
        "You are a MARC21 record QA assistant.\n"
        f"Role: {role}\n{_hint_for(role)}\n"
        f"{ctx}\n\n"
        "Question: Are these two values the same information but written differently?\n"
        "Answer strictly with a single token: YES or NO. If uncertain, answer NO."
    )
    try:
        raw = generate_text(prompt, backend=backend)
    except Exception:
        return {"answer": None, "raw": ""}
    return {"answer": _parse_yes_no_response(raw), "raw": raw}

def verify_label(a: str, b: str, role: str, label: CATEGORY, tag: str, code: str|None,
                 fieldA: Optional[str] = None, fieldB: Optional[str] = None,
                 *, backend: Optional[BackendLiteral] = None) -> dict:
    agreed = _ask_yes_no(role, tag, code, a, b, label, fieldA, fieldB, backend)
    suggested, raw = (None, "")
    if agreed is False or agreed is None:
        suggested, raw = _ask_best(role, tag, code, a, b, fieldA, fieldB, backend)
    return {"agreed": agreed, "suggested": suggested, "raw": raw}
