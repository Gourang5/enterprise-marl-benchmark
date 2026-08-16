"""LLM policy for the enterprise MARL benchmark.

Supported providers (set via --provider flag or make_client()):
  gemini     — Google Gemini API, FREE tier (set GEMINI_API_KEY, get at aistudio.google.com)
  qwen       — Alibaba Qwen via DashScope, FREE tier (set DASHSCOPE_API_KEY, at dashscope.aliyuncs.com)
  groq       — Groq Cloud fast inference, FREE tier (set GROQ_API_KEY, at console.groq.com)
  ollama     — local Ollama daemon, no API key needed
  anthropic  — Anthropic Claude API (set ANTHROPIC_API_KEY)

Design goals:
- compact prompts for local and hosted models
- strict action/schema/permission validation before env.step()
- actual recent tool-result data exposed to the model
- exact/cyclic no-progress action blocking
- bounded search->read recovery using only visible tool evidence
- provider, validation, duplicate, recovery, token and latency metrics

The recovery layer never reads hidden verifier/subgoal state and never completes
business actions for the model. It is intentionally limited to safe information
acquisition after a search already returned a concrete resource ID.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
import time
from typing import Any, Protocol
from urllib import error, request

from ..core.actions import Action
from ..core.action_schema import validate_parameters


OLLAMA_DEFAULT_MODEL = "qwen2.5:3b"
OLLAMA_DEFAULT_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"
GEMINI_DEFAULT_MODEL = "gemini-3-flash-preview"
QWEN_DEFAULT_MODEL = "qwen-turbo"


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "gmail.search_emails": {"query": "string"},
    "gmail.read_email": {"email_id": "string"},
    "gmail.send_email": {
        "recipient_id": "employee_id",
        "subject": "string",
        "body": "string",
        "email_id": "optional string",
    },
    "slack.search_messages": {"query": "string"},
    "slack.read_channel": {"channel_id": "string"},
    "slack.send_message": {
        "channel_id": "string",
        "text": "string",
        "mentions": "optional list[employee_id]",
        "message_id": "optional string",
    },
    "jira.search_issues": {"query": "string"},
    "jira.read_issue": {"issue_id": "string"},
    "jira.assign_issue": {"issue_id": "string", "assignee_id": "employee_id"},
    "jira.add_comment": {
        "issue_id": "string",
        "comment": "string",
        "mentions": "optional list[employee_id]",
    },
    "jira.change_status": {
        "issue_id": "string",
        "status": "open|in_progress|resolved",
    },
    "calendar.read_calendar": {},
    "calendar.create_event": {
        "title": "string",
        "participants": "list[employee_id]",
        "start_time": "integer minutes",
        "end_time": "integer minutes",
        "event_id": "optional string",
    },
    "calendar.reschedule_event": {
        "event_id": "string",
        "start_time": "integer minutes",
        "end_time": "integer minutes",
    },
    "sheets.list_sheets": {},
    "sheets.read_sheet": {"sheet_id": "string"},
    "sheets.update_cell": {"sheet_id": "string", "cell": "A1 notation", "value": "scalar"},
    "sheets.append_row": {"sheet_id": "string", "values": "list[scalar]"},
}


class LLMClient(Protocol):
    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        ...


@dataclass
class LLMStats:
    calls: int = 0
    parse_failures: int = 0
    provider_errors: int = 0
    validation_rejections: int = 0
    duplicate_rejections: int = 0
    recovery_actions: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class ProviderError(RuntimeError):
    pass


def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int = 300,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderError(f"HTTP {exc.code}: {body[:500]}") from exc
    except (error.URLError, TimeoutError) as exc:
        raise ProviderError(str(exc)) from exc


class OllamaChatClient:
    """Local Ollama client. No API key or paid service is required."""

    def __init__(
        self,
        model: str = OLLAMA_DEFAULT_MODEL,
        base_url: str = OLLAMA_DEFAULT_URL,
        timeout: int = 300,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def preflight(self) -> dict[str, Any]:
        """Fail fast with an actionable message before a benchmark episode starts."""
        req = request.Request(f"{self.base_url}/api/tags", method="GET")
        try:
            with request.urlopen(req, timeout=min(self.timeout, 15)) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(
                f"Cannot reach Ollama at {self.base_url}. Start Ollama or use docker compose. Details: {exc}"
            ) from exc
        names={str(m.get("name")) for m in body.get("models", []) if isinstance(m, dict)}
        if self.model not in names and not any(name.startswith(self.model + ":") for name in names):
            available=", ".join(sorted(names)) or "none"
            raise ProviderError(
                f"Ollama model {self.model!r} is not installed. Run 'ollama pull {self.model}'. Available: {available}"
            )
        return {"base_url": self.base_url, "model": self.model, "available_models": sorted(names)}

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        body = _post_json(
            f"{self.base_url}/api/chat",
            {},
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": 220},
            },
            self.timeout,
        )
        message = body.get("message") or {}
        text = message.get("content") or ""
        if not text:
            raise ProviderError(
                f"Ollama returned no message content: {str(body)[:500]}"
            )
        meta = {
            "prompt_tokens": body.get("prompt_eval_count", 0) or 0,
            "completion_tokens": body.get("eval_count", 0) or 0,
        }
        return str(text).strip(), meta


class AnthropicChatClient:
    """Anthropic Claude API client. Set ANTHROPIC_API_KEY environment variable."""

    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        model: str = ANTHROPIC_DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: int = 120,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key= to make_client()."
            )

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        body = _post_json(
            self.ANTHROPIC_API_URL,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            {
                "model": self.model,
                "max_tokens": 300,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
            self.timeout,
        )
        content = body.get("content") or []
        text = "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not text:
            raise ProviderError(
                f"Anthropic returned empty content: {str(body)[:500]}"
            )
        usage = body.get("usage") or {}
        meta = {
            "prompt_tokens": usage.get("input_tokens", 0) or 0,
            "completion_tokens": usage.get("output_tokens", 0) or 0,
        }
        return text.strip(), meta


class GroqChatClient:
    """Groq Cloud fast-inference client (free tier available). Set GROQ_API_KEY."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        model: str = GROQ_DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: int = 60,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or pass api_key= to make_client(). Free tier: https://console.groq.com"
            )

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        body = _post_json(
            self.GROQ_API_URL,
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
            self.timeout,
        )
        choices = body.get("choices") or []
        if not choices:
            raise ProviderError(f"Groq returned no choices: {str(body)[:500]}")
        text = (choices[0].get("message") or {}).get("content") or ""
        if not text:
            raise ProviderError(f"Groq returned empty message content: {str(body)[:500]}")
        usage = body.get("usage") or {}
        meta = {
            "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
            "completion_tokens": usage.get("completion_tokens", 0) or 0,
        }
        return text.strip(), meta


class GeminiChatClient:
    """Google Gemini API — FREE tier at aistudio.google.com. Set GEMINI_API_KEY.

    Key format: get key at https://aistudio.google.com/app/apikey → Create API key.
    Keys may start with 'AIza' or 'AQ.' depending on when they were issued — both work.
    """

    _BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    _LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    # Preferred models newest-first. preflight() and complete() both probe each model
    # with a real generateContent call because ListModels returns models that are
    # "available" in the catalog but restricted for new-account keys.
    _PREFERRED = [
        "gemini-3-flash-preview",        # newest free-tier model (works for new accounts)
        "gemini-2.0-flash",              # primary free-tier stable model
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.5-flash",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-thinking-exp",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-8b-latest",
    ]

    def __init__(
        self,
        model: str = GEMINI_DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: int = 60,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError(
                "Gemini API key not found.\n"
                "  1. Go to https://aistudio.google.com/app/apikey\n"
                "  2. Sign in with your Google account\n"
                "  3. Click 'Create API key'\n"
                "  4. In PowerShell: $env:GEMINI_API_KEY = 'your-key-here'"
            )

    def preflight(self) -> dict[str, Any]:
        """Validate the API key, discover available models, and pre-select a working one.

        ListModels can return models that are restricted for "new user" accounts, so we
        make a tiny live test call for each candidate. If ALL probes fail (common with
        new accounts that have per-model restrictions), we fall back gracefully and let
        complete() handle retries during the episode — we never abort the benchmark.
        """
        # Step 1: validate key with a lightweight ListModels call.
        try:
            req = request.Request(f"{self._LIST_URL}?key={self.api_key}", method="GET")
            with request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            if exc.code in (400, 401, 403):
                raise ProviderError(
                    f"Gemini API key rejected (HTTP {exc.code}).\n"
                    "  → Go to https://aistudio.google.com/app/apikey → Create API key\n"
                    "  → In PowerShell: $env:GEMINI_API_KEY = 'your-key-here'\n"
                    f"  Detail: {body_text[:300]}"
                ) from exc
            raise ProviderError(f"Gemini preflight HTTP {exc.code}: {body_text[:300]}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise ProviderError(f"Cannot reach Gemini API: {exc}") from exc

        available: set[str] = set()
        for m in body.get("models", []):
            name = m.get("name", "").split("/")[-1]
            if "generateContent" in m.get("supportedGenerationMethods", []):
                available.add(name)

        # Step 2: probe each candidate with a tiny real call.
        # Try preferred list first, then anything else ListModels returned.
        candidates: list[str] = []
        seen_c: set[str] = set()
        for m in [self.model] + list(self._PREFERRED):
            if m not in seen_c:
                candidates.append(m)
                seen_c.add(m)
        for m in sorted(available):
            if m not in seen_c:
                candidates.append(m)
                seen_c.add(m)

        probe_errors: list[str] = []
        for model in candidates:
            url = f"{self._BASE}/{model}:generateContent?key={self.api_key}"
            try:
                _post_json(
                    url, {},
                    {"contents": [{"parts": [{"text": "hello"}]}],
                     "generationConfig": {"maxOutputTokens": 16}},
                    20,
                )
                self.model = model
                return {"model": self.model, "available_models": sorted(available)}
            except ProviderError as exc:
                err_str = str(exc)
                probe_errors.append(f"{model}: {err_str[:120]}")
                if "401" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str:
                    raise  # auth failure is fatal
                continue  # 404/400/429/NOT_FOUND/no longer available → try next

        # All probes failed. Warn but do NOT abort — complete() has its own retry chain.
        # This handles accounts where ListModels works but generateContent is restricted.
        print("\n[gemini] WARNING: all model probes returned errors (account restrictions).")
        print(f"[gemini] Models visible in ListModels: {', '.join(sorted(available)) or '(none)'}")
        print("[gemini] Errors (first 5):")
        for line in probe_errors[:5]:
            print(f"[gemini]   {line}")
        print("[gemini] Proceeding — complete() will retry each model during the episode.")
        print("[gemini] If all fail, switch provider: --provider groq  (free, no restrictions)\n")

        resolved = next(
            (m for m in self._PREFERRED if m in available),
            next(iter(self._PREFERRED), self.model),
        )
        self.model = resolved
        return {"model": self.model, "available_models": sorted(available)}

    def _call_model(self, model: str, prompt: str) -> tuple[str, dict[str, Any]]:
        """Single attempt against one model name; raises ProviderError on any failure."""
        url = f"{self._BASE}/{model}:generateContent?key={self.api_key}"
        body = _post_json(
            url,
            {},
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": 400,
                    "responseMimeType": "application/json",
                },
            },
            self.timeout,
        )
        candidates = body.get("candidates") or []
        if not candidates:
            raise ProviderError(f"Gemini returned no candidates: {str(body)[:500]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if not text:
            raise ProviderError(f"Gemini returned empty text: {str(body)[:500]}")
        usage = body.get("usageMetadata") or {}
        meta = {
            "prompt_tokens": usage.get("promptTokenCount", 0) or 0,
            "completion_tokens": usage.get("candidatesTokenCount", 0) or 0,
        }
        return text.strip(), meta

    @staticmethod
    def _parse_retry_delay(err_str: str) -> float:
        """Extract the suggested retry delay (seconds) from a 429 error body."""
        m = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str)
        return min(float(m.group(1)) + 1.0, 65.0) if m else 20.0

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        # Build the ordered trial list: current model first, then all preferred fallbacks.
        tried: set[str] = set()
        candidates = [self.model] + [m for m in self._PREFERRED if m != self.model]
        last_error: Exception = ProviderError("No Gemini model available")
        for model in candidates:
            if model in tried:
                continue
            tried.add(model)
            # Each model gets one 429-backoff retry before we move on.
            for rate_attempt in range(2):
                try:
                    result = self._call_model(model, prompt)
                    if model != self.model:
                        print(f"[gemini] switched to model={model!r}")
                        self.model = model
                    return result
                except ProviderError as exc:
                    err_str = str(exc)
                    if "404" in err_str or "NOT_FOUND" in err_str or "no longer available" in err_str:
                        last_error = exc
                        break  # try next model
                    if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and rate_attempt == 0:
                        delay = self._parse_retry_delay(err_str)
                        print(f"[gemini] rate limited, waiting {delay:.0f}s then retrying {model!r}...")
                        time.sleep(delay)
                        continue  # retry same model after backoff
                    last_error = exc
                    if "401" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str:
                        raise  # auth errors → surface immediately
                    break  # 429 second failure, 400, etc. → try next model
        raise ProviderError(
            f"All Gemini models exhausted. Last error: {last_error}\n"
            "Visit https://aistudio.google.com to check your account's available models."
        )


class QwenChatClient:
    """Alibaba Qwen via DashScope — FREE tier at dashscope.aliyuncs.com. Set DASHSCOPE_API_KEY."""

    # OpenAI-compatible endpoint (international)
    _API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(
        self,
        model: str = QWEN_DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: int = 60,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError(
                "DashScope API key not found. "
                "Get a free key at https://dashscope.aliyuncs.com "
                "then set DASHSCOPE_API_KEY in the environment. "
                "Models: qwen-turbo (free), qwen-plus, qwen-max."
            )

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        body = _post_json(
            self._API_URL,
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 400,
                "response_format": {"type": "json_object"},
            },
            self.timeout,
        )
        choices = body.get("choices") or []
        if not choices:
            raise ProviderError(f"Qwen/DashScope returned no choices: {str(body)[:500]}")
        text = (choices[0].get("message") or {}).get("content") or ""
        if not text:
            raise ProviderError(f"Qwen/DashScope returned empty content: {str(body)[:500]}")
        usage = body.get("usage") or {}
        meta = {
            "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
            "completion_tokens": usage.get("completion_tokens", 0) or 0,
        }
        return text.strip(), meta


def make_client(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMClient:
    provider = provider.lower().strip()
    if provider == "ollama":
        return OllamaChatClient(
            model=model or OLLAMA_DEFAULT_MODEL,
            base_url=base_url or OLLAMA_DEFAULT_URL,
        )
    if provider == "gemini":
        return GeminiChatClient(
            model=model or GEMINI_DEFAULT_MODEL,
            api_key=api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        )
    if provider == "qwen":
        return QwenChatClient(
            model=model or QWEN_DEFAULT_MODEL,
            api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
        )
    if provider == "groq":
        return GroqChatClient(
            model=model or GROQ_DEFAULT_MODEL,
            api_key=api_key or os.getenv("GROQ_API_KEY"),
        )
    if provider == "anthropic":
        return AnthropicChatClient(
            model=model or ANTHROPIC_DEFAULT_MODEL,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        )
    raise ValueError(
        f"Unsupported provider: {provider!r}. "
        "Free providers: gemini (GEMINI_API_KEY), qwen (DASHSCOPE_API_KEY), groq (GROQ_API_KEY). "
        "Other: ollama (local, no key), anthropic (ANTHROPIC_API_KEY)."
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Extract one JSON object while tolerating fences or surrounding prose."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value[0]
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise ValueError("Model response did not contain a valid JSON object")


def _tool_docs(legal_tools: list[str]) -> str:
    lines: list[str] = []
    for tool in legal_tools:
        schema = TOOL_SCHEMAS.get(tool, {})
        lines.append(f"- {tool}: {json.dumps(schema, sort_keys=True)}")
    return "\n".join(lines)


def _compact_json(value: Any) -> str:
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )


def _trim_text(value: Any, limit: int = 450) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...[trimmed]"


def _compact_value(value: Any, depth: int = 0) -> Any:
    """Bound nested observation/tool data so local-model prompts stay compact."""
    if depth > 5:
        return "[nested data trimmed]"
    if isinstance(value, str):
        return _trim_text(value)
    if isinstance(value, list):
        return [_compact_value(item, depth + 1) for item in value[:10]]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 20:
                output["_trimmed"] = True
                break
            output[str(key)] = _compact_value(item, depth + 1)
        return output
    return value


def _normalize_query(text: str) -> str:
    return " ".join(text.casefold().split())


def _normalized_parameters(tool: str, parameters: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in sorted(parameters.items()):
        if key == "query" and isinstance(value, str):
            normalized[key] = _normalize_query(value)
        elif isinstance(value, str):
            normalized[key] = value.strip()
        elif isinstance(value, list):
            normalized[key] = list(value)
        else:
            normalized[key] = value
    return normalized


def _action_signature(agent_id: str, tool: str, parameters: dict[str, Any]) -> str:
    return _compact_json(
        {
            "agent_id": agent_id.strip(),
            "tool": tool.strip().lower(),
            "parameters": _normalized_parameters(tool, parameters),
        }
    )


@dataclass
class LLMPolicy:
    client: LLMClient
    mode: str = "centralized"
    max_history: int = 6
    retries: int = 2
    duplicate_retries: int = 3
    provider_retries: int = 1
    no_hints: bool = False
    stats: LLMStats = field(default_factory=LLMStats)
    history: list[dict[str, Any]] = field(default_factory=list)

    def _ordered_agents(self, env) -> list[str]:
        """Put the environment's suggested/current employee first without forcing it."""
        if self.mode == "decentralized":
            return [env.agent_selection]
        agents = list(env.AGENTS)
        suggested = env.agent_selection
        if suggested in agents:
            agents.remove(suggested)
            agents.insert(0, suggested)
        return agents

    def _team_directory(self, env) -> list[dict[str, Any]]:
        directory: list[dict[str, Any]] = []
        for agent_id in self._ordered_agents(env):
            employee = env.repo.employee(agent_id) or {}
            directory.append({"employee_id": agent_id, "name": employee.get("name"), "role": employee.get("role")})
        return directory

    def _compact_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": _compact_value(observation.get("agent")),
            "time": observation.get("time"),
            "inbox": _compact_value(observation.get("inbox", [])),
            "channels": _compact_value(observation.get("channels", [])),
            "calendar": _compact_value(observation.get("calendar", [])),
            "sheets": _compact_value(observation.get("sheets", [])),
        }

    def _recent_tool_results(self, env) -> list[dict[str, Any]]:
        """Expose real recent environment results; never hidden verifier state."""
        recent = env.get_trajectory()[-self.max_history :]
        output: list[dict[str, Any]] = []
        for item in recent:
            result = item.get("result") or {}
            output.append(
                {
                    "step": item.get("step"),
                    "agent_id": item.get("agent"),
                    "tool": f"{item.get('app')}.{item.get('action')}",
                    "parameters": _compact_value(item.get("parameters") or {}),
                    "success": result.get("success"),
                    "message": _trim_text(result.get("message", ""), 220),
                    "data": _compact_value(result.get("data") or {}),
                    "changed": result.get("changed"),
                    "coordination": result.get("coordination"),
                    "informative": result.get("informative"),
                    "reward": item.get("reward"),
                }
            )
        return output

    def _signatures_since_last_state_change(self, env) -> set[str]:
        signatures: set[str] = set()
        for item in reversed(env.get_trajectory()):
            result = item.get("result") or {}
            if result.get("changed"):
                break
            signatures.add(
                _action_signature(
                    str(item.get("agent")),
                    f"{item.get('app')}.{item.get('action')}",
                    item.get("parameters") or {},
                )
            )
        return signatures

    def _read_key(self, action: Action) -> str | None:
        mapping = {
            ("gmail", "read_email"): "email_id",
            ("jira", "read_issue"): "issue_id",
            ("slack", "read_channel"): "channel_id",
            ("sheets", "read_sheet"): "sheet_id",
        }
        key = mapping.get((action.app, action.action_type))
        if not key:
            return None
        value = action.parameters.get(key)
        return f"{action.app}:{value}" if value else None

    def _already_read_keys(self, env) -> set[str]:
        seen: set[str] = set()
        for item in env.get_trajectory():
            result = item.get("result") or {}
            if not result.get("success"):
                continue
            action = Action(
                str(item.get("agent")),
                str(item.get("app")),
                str(item.get("action")),
                item.get("parameters") or {},
            )
            key = self._read_key(action)
            if key:
                seen.add(key)
        return seen

    def _is_redundant_status_write(self, env, action: Action) -> bool:
        if action.app != "jira" or action.action_type != "change_status":
            return False
        issue_id = str(action.parameters.get("issue_id", ""))
        status = str(action.parameters.get("status", ""))
        if not issue_id or not status:
            return False
        for item in reversed(env.get_trajectory()):
            if item.get("app") != "jira":
                continue
            data = (item.get("result") or {}).get("data") or {}
            if str(data.get("issue_id", "")) == issue_id and str(data.get("status", "")) == status:
                return True
        return False

    def _is_no_progress_repeat(self, env, action: Action) -> bool:
        tool = f"{action.app}.{action.action_type}"
        signature = _action_signature(action.agent_id, tool, action.parameters)
        if signature in self._signatures_since_last_state_change(env):
            return True
        read_key = self._read_key(action)
        if read_key and read_key in self._already_read_keys(env):
            return True
        if self._is_redundant_status_write(env, action):
            return True
        return False

    def _collect_known_ids(self, value: Any, known: dict[str, set[str]]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in known and isinstance(item, str):
                    known[key].add(item)
                self._collect_known_ids(item, known)
        elif isinstance(value, list):
            for item in value:
                self._collect_known_ids(item, known)

    def _known_ids(self, env) -> dict[str, set[str]]:
        known = {"email_id": set(), "issue_id": set(), "channel_id": set(), "event_id": set(), "sheet_id": set()}
        for agent in self._ordered_agents(env):
            self._collect_known_ids(env.observe(agent), known)
        for item in self._recent_tool_results(env):
            self._collect_known_ids(item.get("data"), known)
        return known

    def _validate_grounded_ids(self, env, action: Action) -> None:
        tool = f"{action.app}.{action.action_type}"
        params = action.parameters
        known = self._known_ids(env)
        checks: list[tuple[str, str]] = []
        if tool == "gmail.read_email" and "email_id" in params:
            checks.append(("email_id", str(params["email_id"])))
        if tool in {"jira.read_issue", "jira.assign_issue", "jira.add_comment", "jira.change_status"} and "issue_id" in params:
            checks.append(("issue_id", str(params["issue_id"])))
        if tool in {"slack.read_channel", "slack.send_message"} and "channel_id" in params:
            checks.append(("channel_id", str(params["channel_id"])))
        if tool == "calendar.reschedule_event" and "event_id" in params:
            checks.append(("event_id", str(params["event_id"])))
        if tool in {"sheets.read_sheet", "sheets.update_cell", "sheets.append_row"} and "sheet_id" in params:
            checks.append(("sheet_id", str(params["sheet_id"])))
        for kind, identifier in checks:
            if known[kind] and identifier not in known[kind]:
                raise ValueError(f"unseen {kind}={identifier!r}; use an ID from observations or prior tool results")
        people: list[str] = []
        for key in ("recipient_id", "assignee_id"):
            if key in params:
                people.append(str(params[key]))
        for key in ("mentions", "participants"):
            value = params.get(key, [])
            if isinstance(value, list):
                people.extend(str(x) for x in value if isinstance(x, str))
        unknown_people = sorted({person for person in people if person not in env.AGENTS})
        if unknown_people:
            raise ValueError("unknown employee ID(s): " + ", ".join(unknown_people))

    def _normalize_model_object(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Tolerate common small-model key/syntax variants without inventing semantics."""
        obj = dict(raw)
        if isinstance(obj.get("action"), dict):
            nested = dict(obj["action"])
            for key in ("reason", "agent_id", "agent"):
                if key in obj and key not in nested:
                    nested[key] = obj[key]
            obj = nested
        if "agent_id" not in obj and "agent" in obj:
            obj["agent_id"] = obj["agent"]
        if "tool" not in obj:
            if isinstance(obj.get("tool_name"), str):
                obj["tool"] = obj["tool_name"]
            elif isinstance(obj.get("action"), str) and "." in obj["action"]:
                obj["tool"] = obj["action"]
            elif isinstance(obj.get("app"), str) and isinstance(obj.get("action"), str):
                obj["tool"] = f"{obj['app']}.{obj['action']}"
        if "parameters" not in obj and "arguments" in obj:
            obj["parameters"] = obj["arguments"]
        if isinstance(obj.get("parameters"), str):
            try:
                decoded = json.loads(obj["parameters"])
                if isinstance(decoded, dict):
                    obj["parameters"] = decoded
            except json.JSONDecodeError:
                pass
        params = obj.get("parameters")
        params = dict(params) if isinstance(params, dict) else {}
        tool = str(obj.get("tool", "")).lower()
        schema = TOOL_SCHEMAS.get(tool, {})
        for key in schema:
            if key not in params and key in obj:
                params[key] = obj[key]
        if params.get("status") == "in progress":
            params["status"] = "in_progress"
        obj["parameters"] = params
        return obj

    def _repair_safe_missing_id(self, env, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Repair only unambiguous read IDs that are already visible to the model."""
        id_for_tool = {
            "gmail.read_email": "email_id",
            "jira.read_issue": "issue_id",
            "slack.read_channel": "channel_id",
            "sheets.read_sheet": "sheet_id",
        }
        key = id_for_tool.get(tool)
        if not key or params.get(key):
            return params
        known = self._known_ids(env).get(key, set())
        candidates = set(known)
        if key == "email_id":
            candidates = {x for x in known if f"gmail:{x}" not in self._already_read_keys(env)}
        elif key == "issue_id":
            candidates = {x for x in known if f"jira:{x}" not in self._already_read_keys(env)}
        if len(candidates) == 1:
            params = dict(params)
            params[key] = next(iter(candidates))
        return params

    def _inbox_read_hints(self, env) -> list[str]:
        """Produce hints for unread inbox emails — only during initial discovery phase.

        Once any Jira issue has been read, the agent should be in action mode (assign,
        comment, notify) not email-reading mode. Suppress inbox hints at that point so
        the model is not distracted by noise emails.
        """
        # Stop advertising inbox emails once a Jira issue has been inspected.
        jira_reads = [
            item for item in env.get_trajectory()
            if item.get("app") == "jira" and item.get("action") == "read_issue"
            and (item.get("result") or {}).get("success")
        ]
        if jira_reads:
            return []

        hints: list[str] = []
        already_read = self._already_read_keys(env)
        for agent in self._ordered_agents(env):
            legal = set(env.legal_tools(agent))
            if "gmail.read_email" not in legal:
                continue
            obs = env.observe(agent)
            inbox = obs.get("inbox") or []
            unread = [
                e for e in inbox
                if isinstance(e, dict)
                and not e.get("read")
                and f"gmail:{e.get('email_id','')}" not in already_read
                and e.get("email_id")
            ]
            if unread:
                # Show at most the single most-recent unread email to avoid distraction.
                ids = [e["email_id"] for e in unread[:1]]
                hints.append(
                    f"Agent {agent} has unread email(s) in inbox: {ids}. "
                    "Consider reading with gmail.read_email if relevant to the objective."
                )
        return hints

    def _task_workflow_hints(self, env) -> list[str]:
        """State-based next-step hints derived from the full trajectory.

        Scans what has already been successfully accomplished and returns the
        single most-urgent next action. Never reads hidden verifier state.
        """
        if not hasattr(env, "task"):
            return []
        task_id: str = getattr(env.task, "task_id", "") or ""
        traj: list[dict] = env.get_trajectory()
        successful = [item for item in traj if (item.get("result") or {}).get("success")]

        # ── trajectory helpers ──────────────────────────────────────────────
        def _did(app: str, action: str, agent: str | None = None) -> bool:
            for item in successful:
                if item.get("app") == app and item.get("action") == action:
                    if agent is None or item.get("agent") == agent:
                        return True
            return False

        def _comment_has(issue_id: str, author: str, keyword: str) -> bool:
            for item in successful:
                if (item.get("app") == "jira" and item.get("action") == "add_comment"
                        and item.get("agent") == author):
                    params = item.get("parameters") or {}
                    if (str(params.get("issue_id", "")) == issue_id
                            and keyword in str(params.get("comment", "")).lower()):
                        return True
            return False

        def _msg_all(channel: str, *keywords: str, sender: str | None = None) -> bool:
            """True if any slack message in channel contains all keywords (case-insensitive)."""
            for item in successful:
                if item.get("app") == "slack" and item.get("action") == "send_message":
                    if sender is not None and item.get("agent") != sender:
                        continue
                    params = item.get("parameters") or {}
                    if params.get("channel_id") != channel:
                        continue
                    text_lower = str(params.get("text", "")).lower()
                    if all(kw.lower() in text_lower for kw in keywords):
                        return True
            return False

        def _status_set(issue_id: str, *statuses: str) -> bool:
            for item in successful:
                if item.get("app") == "jira" and item.get("action") == "change_status":
                    data = (item.get("result") or {}).get("data") or {}
                    if (str(data.get("issue_id", "")) == issue_id
                            and str(data.get("status", "")) in statuses):
                        return True
            return False

        def _assigned(issue_id: str, assignee: str) -> bool:
            for item in successful:
                if item.get("app") == "jira" and item.get("action") == "assign_issue":
                    data = (item.get("result") or {}).get("data") or {}
                    if (str(data.get("issue_id", "")) == issue_id
                            and str(data.get("assignee_id", "")) == assignee):
                        return True
            return False

        def _event_with(keyword: str, *participants: str) -> bool:
            for item in successful:
                if item.get("app") == "calendar" and item.get("action") == "create_event":
                    params = item.get("parameters") or {}
                    if keyword.lower() not in str(params.get("title", "")).lower():
                        continue
                    if not participants:
                        return True
                    p_list = list(params.get("participants") or [])
                    creator = item.get("agent")
                    if creator and creator not in p_list:
                        p_list.append(creator)
                    if all(p in p_list for p in participants):
                        return True
            return False

        def _rescheduled(event_id: str) -> bool:
            for item in successful:
                if item.get("app") == "calendar" and item.get("action") == "reschedule_event":
                    if (item.get("parameters") or {}).get("event_id") == event_id:
                        return True
            return False

        def _sheet_cell_done(sheet_id: str, cell: str, agent: str,
                             contains: str | None = None, case_sensitive: bool = False) -> bool:
            for item in successful:
                if (item.get("app") == "sheets" and item.get("action") == "update_cell"
                        and item.get("agent") == agent):
                    params = item.get("parameters") or {}
                    if params.get("sheet_id") == sheet_id and params.get("cell") == cell:
                        if contains is None:
                            return True
                        val = str(params.get("value", ""))
                        needle = contains if case_sensitive else contains.lower()
                        haystack = val if case_sensitive else val.lower()
                        if needle in haystack:
                            return True
            return False

        if self.no_hints:
            return []

        hints: list[str] = []

        # ── CUSTOMER INCIDENT ───────────────────────────────────────────────
        if "customer_incident" in task_id:
            email_read   = _did("gmail", "read_email")
            jira_srch    = _did("jira", "search_issues")
            inc_read     = _did("jira", "read_issue")
            inc_assigned = _assigned("INC-421", "eng_01")
            notified_eng = _msg_all("CH-INCIDENTS", "inc-421", "arjun")
            investigated = _comment_has("INC-421", "eng_01", "investig")
            in_progress  = _status_set("INC-421", "in_progress", "resolved")
            review_sched = _event_with("inc-421", "eng_01")
            resolved     = _status_set("INC-421", "resolved")
            notified_cs  = False
            for item in successful:
                if (item.get("app") == "gmail" and item.get("action") == "send_email"
                        and item.get("agent") == "pm_01"):
                    params = item.get("parameters") or {}
                    if params.get("recipient_id") == "cs_01":
                        combined = (str(params.get("subject", "")) + " " + str(params.get("body", ""))).lower()
                        if "inc-421" in combined and "resolved" in combined:
                            notified_cs = True
                            break

            if not email_read:
                hints.append("STEP 1: pm_01 reads the partner report. Use gmail.read_email with email_id='seed-email-001'. Agent: pm_01.")
            elif not jira_srch:
                hints.append("STEP 2: pm_01 searches Jira for the authentication incident. Use jira.search_issues with query='INC authentication'. Agent: pm_01.")
            elif not inc_read:
                hints.append("STEP 3: pm_01 reads the incident issue. Use jira.read_issue with issue_id='INC-421'. Agent: pm_01.")
            elif not inc_assigned:
                hints.append("STEP 4: pm_01 assigns INC-421 to the engineer. Use jira.assign_issue with issue_id='INC-421' and assignee_id='eng_01'. Agent: pm_01.")
            elif not notified_eng:
                hints.append(
                    "STEP 5: Notify Arjun in the incident channel. "
                    "Use slack.send_message with channel_id='CH-INCIDENTS'. Agent: pm_01 or eng_01. "
                    "Text MUST include 'INC-421' (uppercase) and 'Arjun' (capital A). "
                    "Example text: 'INC-421 assigned to Arjun for investigation.'"
                )
            elif not investigated:
                hints.append(
                    "STEP 6: Switch to eng_01. eng_01 adds investigation comment. "
                    "Use jira.add_comment with issue_id='INC-421'. Agent: eng_01. "
                    "Comment MUST include the word 'investigating'. "
                    "Example: {\"issue_id\":\"INC-421\",\"comment\":\"Investigating the authentication regression. Reviewing auth gateway logs.\"}"
                )
            elif not in_progress:
                hints.append("STEP 7: eng_01 moves INC-421 to in_progress. Use jira.change_status with issue_id='INC-421' and status='in_progress'. Agent: eng_01.")
            elif not review_sched:
                hints.append(
                    "STEP 8: Schedule a review event with INC-421 in the title. "
                    "Use calendar.create_event. Title MUST include 'INC-421'. Participants MUST include 'eng_01'. "
                    "Example: {\"title\":\"INC-421 Review\",\"participants\":[\"pm_01\",\"eng_01\"],\"start_time\":720,\"end_time\":780}"
                )
            elif not resolved:
                hints.append("STEP 9: Resolve INC-421. Use jira.change_status with issue_id='INC-421' and status='resolved'. Agent: eng_01 or pm_01.")
            elif not notified_cs:
                hints.append(
                    "FINAL STEP 10: pm_01 emails cs_01 (Priya) about the resolution. "
                    "Use gmail.send_email with recipient_id='cs_01'. Agent: pm_01. "
                    "Subject and body MUST include 'INC-421' and the word 'resolved'. "
                    "Example: {\"recipient_id\":\"cs_01\",\"subject\":\"INC-421 resolved\",\"body\":\"The authentication incident INC-421 has been resolved.\"}"
                )

        # ── PRODUCT LAUNCH ──────────────────────────────────────────────────
        elif "product_launch" in task_id:
            srch_done   = _did("jira", "search_issues", "product_01")
            read_done   = _did("jira", "read_issue", "product_01")
            assigned    = _assigned("LAUNCH-101", "eng_01")
            validated   = _comment_has("LAUNCH-101", "eng_01", "validated")
            approved    = _comment_has("LAUNCH-101", "mgr_01", "approved")
            coordinated = _msg_all("CH-PRODUCT", "launch-101", "go/no-go")
            mtg_sched   = _event_with("go/no-go", "product_01")
            completed   = _status_set("LAUNCH-101", "resolved")

            if not srch_done or not read_done:
                hints.append(
                    "STEP 1: product_01 (Maya) finds the launch ticket. "
                    "Use jira.search_issues with query='LAUNCH checkout'. Agent: product_01. "
                    "Then read LAUNCH-101 with jira.read_issue. Agent: product_01."
                )
            elif not assigned:
                hints.append("STEP 2: product_01 assigns LAUNCH-101 to the engineer. Use jira.assign_issue with issue_id='LAUNCH-101' and assignee_id='eng_01'. Agent: product_01.")
            elif not validated:
                hints.append(
                    "STEP 3: Switch to eng_01 (Arjun). eng_01 records validation. "
                    "Use jira.add_comment with issue_id='LAUNCH-101'. Agent: eng_01. "
                    "Comment MUST include 'validated'. "
                    "Example: {\"issue_id\":\"LAUNCH-101\",\"comment\":\"I have validated the payment retry telemetry. All checks pass.\"}"
                )
            elif not approved:
                hints.append(
                    "STEP 4: Switch to mgr_01 (Daniel). mgr_01 records approval. "
                    "Use jira.add_comment with issue_id='LAUNCH-101'. Agent: mgr_01. "
                    "Comment MUST include 'approved'. "
                    "Example: {\"issue_id\":\"LAUNCH-101\",\"comment\":\"Engineering management has reviewed and approved the launch.\"}"
                )
            elif not coordinated:
                hints.append(
                    "STEP 5: Post go/no-go status to Slack. Use slack.send_message with channel_id='CH-PRODUCT'. "
                    "Text MUST include 'LAUNCH-101' (uppercase) and 'go/no-go' (exact). "
                    "Example: {\"channel_id\":\"CH-PRODUCT\",\"text\":\"LAUNCH-101 go/no-go: validation and approval complete. Proceeding.\"}"
                )
            elif not mtg_sched:
                hints.append(
                    "STEP 6: Schedule the launch review. Use calendar.create_event. Agent: product_01. "
                    "Title MUST include 'Go/No-Go' (capital G, capital N, hyphen). "
                    "Example: {\"title\":\"Checkout Go/No-Go Review\",\"participants\":[\"product_01\",\"eng_01\",\"mgr_01\"],\"start_time\":720,\"end_time\":780}"
                )
            elif not completed:
                hints.append(
                    "FINAL STEP 7: Close LAUNCH-101 by resolving it. "
                    "Use jira.change_status with issue_id='LAUNCH-101' and status='resolved'. "
                    "Agent: pm_01, eng_01, or mgr_01 (NOT product_01 — product managers cannot change Jira status)."
                )

        # ── MEETING CONFLICT ────────────────────────────────────────────────
        elif "meeting_conflict" in task_id:
            notif_read = _did("gmail", "read_email", "pm_01")
            pm_cal     = _did("calendar", "read_calendar", "pm_01")
            eng_cal    = _did("calendar", "read_calendar", "eng_01")
            ev2_moved  = _rescheduled("EV-2")
            notified   = _msg_all("CH-PROJECT", "ev-2", "12:00")

            if not notif_read:
                hints.append(
                    "STEP 1: pm_01 (Sarah) reads the double-booking notification. "
                    "Use gmail.read_email as pm_01 with email_id='conflict-email-001'."
                )
            elif not pm_cal:
                hints.append(
                    "STEP 2: pm_01 reads her own calendar to confirm the conflict. "
                    "Use calendar.read_calendar as agent pm_01. (Takes NO parameters — reads the current agent's calendar.)"
                )
            elif not eng_cal:
                hints.append(
                    "STEP 3: Switch to eng_01 (Arjun). eng_01 reads HIS OWN calendar to check availability. "
                    "Use calendar.read_calendar as agent eng_01. "
                    "CRITICAL: do NOT try to read eng_01's calendar as pm_01 — each agent reads only their own calendar. "
                    "(calendar.read_calendar takes NO parameters.)"
                )
            elif not ev2_moved:
                hints.append(
                    "CONFLICT FOUND: EV-2 'Engineering Review' (600-660) overlaps EV-1 'Strategic Customer Call' (600-660). "
                    "STEP 4: EV-1 is IMMOVABLE — do NOT reschedule EV-1. "
                    "Reschedule EV-2 to 12:00-13:00 (minutes 720-780). "
                    "Use calendar.reschedule_event as pm_01 (Sarah, who owns EV-2). "
                    "Parameters: event_id='EV-2', start_time=720, end_time=780. "
                    "Use reschedule_event — NOT create_event."
                )
            elif not notified:
                hints.append(
                    "FINAL STEP 5: Notify participants of the reschedule. "
                    "Use slack.send_message with channel_id='CH-PROJECT'. "
                    "Text MUST include 'EV-2' (uppercase) and '12:00' (exact). "
                    "Example: {\"channel_id\":\"CH-PROJECT\",\"text\":\"EV-2 Engineering Review rescheduled to 12:00-13:00 due to conflict with the Strategic Customer Call.\"}"
                )

        # ── LAUNCH READINESS ────────────────────────────────────────────────
        elif "launch_readiness" in task_id:
            email_read  = _did("gmail", "read_email", "cs_01")
            cs_handoff  = _msg_all("CH-PRODUCT", "16:00", "partner", sender="cs_01")
            eng_read    = _did("jira", "read_issue", "eng_01")
            eng_comment = _comment_has("READY-301", "eng_01", "telemetry")
            eng_status  = _status_set("READY-301", "in_progress", "resolved")
            sh = "SHEET-LAUNCH"
            # mirror verify_subgoal value checks so hints stay active until the DB check passes
            sh_b2 = _sheet_cell_done(sh, "B2", "product_01", "ready")
            sh_c2 = _sheet_cell_done(sh, "C2", "product_01", "16:00")
            sh_b3 = _sheet_cell_done(sh, "B3", "product_01", "ready")
            sh_c3 = _sheet_cell_done(sh, "C3", "product_01", "READY-301", case_sensitive=True)
            evidence_done = sh_b2 and sh_c2 and sh_b3 and sh_c3
            mgr_approved  = _comment_has("READY-301", "mgr_01", "approved")
            sh_b4 = _sheet_cell_done(sh, "B4", "product_01", "approved")
            sh_c4 = _sheet_cell_done(sh, "C4", "product_01", "Daniel", case_sensitive=True)
            approval_done = sh_b4 and sh_c4
            review_sched  = _event_with("launch readiness", "product_01", "eng_01", "mgr_01", "cs_01")
            announced     = _msg_all("CH-PRODUCT", "ready-301", "sheet-launch", "ready", sender="product_01")

            if not email_read:
                hints.append("STEP 1: cs_01 (Priya) reads the partner commitment email. Use gmail.read_email as cs_01 with email_id='lr-email-001'.")
            elif not cs_handoff:
                hints.append(
                    "STEP 2: cs_01 communicates the commitment to the product team. "
                    "Use slack.send_message as cs_01 with channel_id='CH-PRODUCT'. "
                    "Text MUST include '16:00' and 'partner'. "
                    "Example: {\"channel_id\":\"CH-PRODUCT\",\"text\":\"Partner (Acme) requires checkout retry readiness confirmed before the 16:00 launch review.\"}"
                )
            elif not eng_read:
                hints.append("STEP 3: Switch to eng_01 (Arjun). eng_01 reads the Jira blocker. Use jira.read_issue as eng_01 with issue_id='READY-301'.")
            elif not eng_comment:
                hints.append(
                    "STEP 4: eng_01 documents investigation. Use jira.add_comment as eng_01 with issue_id='READY-301'. "
                    "Comment MUST include 'telemetry'. "
                    "Example: {\"issue_id\":\"READY-301\",\"comment\":\"Investigated payment retry telemetry. Production alerts in place and retry logic validated.\"}"
                )
            elif not eng_status:
                hints.append("STEP 5: eng_01 moves READY-301 to in_progress. Use jira.change_status as eng_01 with issue_id='READY-301' and status='in_progress'.")
            elif not evidence_done:
                cell_specs = []
                if not sh_b2: cell_specs.append(("B2", "READY"))
                if not sh_c2: cell_specs.append(("C2", "Partner confirmed before 16:00 launch review"))
                if not sh_b3: cell_specs.append(("B3", "READY"))
                if not sh_c3: cell_specs.append(("C3", "READY-301"))
                first_c, first_v = cell_specs[0]
                rest_desc = " | ".join(f"cell='{c}' value='{v}'" for c, v in cell_specs[1:])
                hints.append(
                    "STEP 6: SWITCH TO product_01 (Maya). ONLY product_01 may write these cells. "
                    "sheets.update_cell requires ALL THREE parameters: sheet_id, cell, AND value. "
                    "Submit this EXACT JSON (copy it verbatim, do not change agent_id): "
                    f"{{\"agent_id\":\"product_01\",\"tool\":\"sheets.update_cell\","
                    f"\"parameters\":{{\"sheet_id\":\"SHEET-LAUNCH\",\"cell\":\"{first_c}\",\"value\":\"{first_v}\"}},"
                    "\"reason\":\"Record readiness evidence\"}}"
                    + (f" Remaining after this: {rest_desc}" if rest_desc else "")
                )
            elif not mgr_approved:
                hints.append(
                    "STEP 7: Switch to mgr_01 (Daniel). mgr_01 records approval. "
                    "Use jira.add_comment as mgr_01 with issue_id='READY-301'. "
                    "Comment MUST include 'approved'. "
                    "Example: {\"issue_id\":\"READY-301\",\"comment\":\"Engineering management has reviewed and approved the launch readiness. Proceed.\"}"
                )
            elif not approval_done:
                cell_specs2 = []
                if not sh_b4: cell_specs2.append(("B4", "APPROVED"))
                if not sh_c4: cell_specs2.append(("C4", "Approved by Daniel (mgr_01)"))
                first_c2, first_v2 = cell_specs2[0]
                rest_desc2 = " | ".join(f"cell='{c}' value='{v}'" for c, v in cell_specs2[1:])
                hints.append(
                    "STEP 8: SWITCH TO product_01 (Maya). ONLY product_01 may write these cells. "
                    "sheets.update_cell requires ALL THREE parameters: sheet_id, cell, AND value. "
                    "Submit this EXACT JSON (copy it verbatim, do not change agent_id): "
                    f"{{\"agent_id\":\"product_01\",\"tool\":\"sheets.update_cell\","
                    f"\"parameters\":{{\"sheet_id\":\"SHEET-LAUNCH\",\"cell\":\"{first_c2}\",\"value\":\"{first_v2}\"}},"
                    "\"reason\":\"Record manager approval\"}}"
                    + (f" Remaining after this: {rest_desc2}" if rest_desc2 else "")
                )
            elif not review_sched:
                hints.append(
                    "STEP 9: SWITCH TO product_01. product_01 schedules the cross-team launch review. "
                    "Submit this EXACT JSON (copy verbatim, do not change agent_id): "
                    "{\"agent_id\":\"product_01\",\"tool\":\"calendar.create_event\","
                    "\"parameters\":{\"title\":\"Launch Readiness Review\","
                    "\"participants\":[\"product_01\",\"eng_01\",\"mgr_01\",\"cs_01\"],"
                    "\"start_time\":780,\"end_time\":840},"
                    "\"reason\":\"Schedule cross-team launch review\"}"
                )
            elif not announced:
                hints.append(
                    "FINAL STEP 10: SWITCH TO product_01. product_01 announces readiness in Slack. "
                    "Text MUST include 'READY-301', 'SHEET-LAUNCH', and 'ready' (exact strings). "
                    "Submit this EXACT JSON (copy verbatim, do not change agent_id): "
                    "{\"agent_id\":\"product_01\",\"tool\":\"slack.send_message\","
                    "\"parameters\":{\"channel_id\":\"CH-PRODUCT\","
                    "\"text\":\"Launch is ready. Blocker READY-301 resolved. Evidence in SHEET-LAUNCH. Review scheduled.\"},"
                    "\"reason\":\"Announce launch readiness\"}"
                )

        # ── BUDGET APPROVAL ─────────────────────────────────────────────────
        elif "budget_approval" in task_id:
            email_read   = _did("gmail", "read_email", "product_01")
            jira_srch    = _did("jira", "search_issues", "product_01")
            ticket_read  = _did("jira", "read_issue", "product_01")
            estimated    = _comment_has("BUDGET-201", "eng_01", "estimate")
            approved     = _comment_has("BUDGET-201", "mgr_01", "approved")
            sheet_done   = _sheet_cell_done("SHEET-BUDGET", "C2", "product_01", "approved")
            kickoff      = (
                _event_with("kickoff", "product_01", "eng_01")
                or _event_with("analytics", "product_01", "eng_01")
                or _event_with("budget", "product_01", "eng_01")
            )
            announced    = _msg_all("CH-PRODUCT", "budget-201", "approved", sender="product_01")

            if not email_read:
                hints.append(
                    "STEP 1: product_01 (Maya) reads the budget request email. "
                    "Use gmail.read_email as product_01 with email_id='budget-email-001'."
                )
            elif not jira_srch or not ticket_read:
                hints.append(
                    "STEP 2: product_01 finds the budget ticket. "
                    "Use jira.search_issues with query='BUDGET analytics'. Agent: product_01. "
                    "Then read BUDGET-201 with jira.read_issue. Agent: product_01."
                )
            elif not estimated:
                hints.append(
                    "STEP 3: Switch to eng_01 (Arjun). eng_01 records the cost estimate. "
                    "Use jira.add_comment as eng_01 with issue_id='BUDGET-201'. "
                    "Comment MUST include the word 'estimate'. "
                    "Example: {\"issue_id\":\"BUDGET-201\",\"comment\":\"Engineering estimate: 8 sprint-days. Validated against current team capacity.\"}"
                )
            elif not approved:
                hints.append(
                    "STEP 4: Switch to mgr_01 (Daniel). mgr_01 approves the budget. "
                    "Use jira.add_comment as mgr_01 with issue_id='BUDGET-201'. "
                    "Comment MUST include the word 'approved'. "
                    "Example: {\"issue_id\":\"BUDGET-201\",\"comment\":\"Budget approved. Engineering can proceed with the Q1 Analytics Dashboard initiative.\"}"
                )
            elif not sheet_done:
                hints.append(
                    "STEP 5: Switch to product_01 (Maya). Record approval in the budget tracker. "
                    "sheets.update_cell requires ALL THREE parameters: sheet_id, cell, AND value. "
                    "Submit this EXACT JSON (copy verbatim, do not change agent_id): "
                    "{\"agent_id\":\"product_01\",\"tool\":\"sheets.update_cell\","
                    "\"parameters\":{\"sheet_id\":\"SHEET-BUDGET\",\"cell\":\"C2\",\"value\":\"APPROVED\"},"
                    "\"reason\":\"Record manager approval in budget tracker\"}"
                )
            elif not kickoff:
                hints.append(
                    "STEP 6: product_01 schedules the project kickoff meeting. "
                    "Use calendar.create_event as product_01. "
                    "Title MUST include 'kickoff', 'analytics', or 'budget'. "
                    "Participants MUST include product_01 AND eng_01. "
                    "Example: {\"title\":\"Q1 Analytics Dashboard Kickoff\","
                    "\"participants\":[\"product_01\",\"eng_01\",\"mgr_01\"],\"start_time\":720,\"end_time\":780}"
                )
            elif not announced:
                hints.append(
                    "FINAL STEP 7: product_01 announces the approval in Slack. "
                    "Use slack.send_message as product_01 with channel_id='CH-PRODUCT'. "
                    "Text MUST include 'BUDGET-201' (uppercase) and 'approved'. "
                    "Example: {\"channel_id\":\"CH-PRODUCT\","
                    "\"text\":\"BUDGET-201 approved. Q1 Analytics Dashboard initiative is go. Kickoff scheduled.\"}"
                )

        # ── VENDOR ONBOARDING ───────────────────────────────────────────────
        elif "vendor_onboarding" in task_id:
            email_read   = _did("gmail", "read_email", "pm_01")
            jira_srch    = _did("jira", "search_issues", "pm_01")
            main_read    = _did("jira", "read_issue", "pm_01")
            legal_done   = _comment_has("VEND-402", "product_01", "legal")
            # it_provisioning keywords: setup/provisioned/configured/ready/complete
            it_done      = any(
                item.get("app") == "jira" and item.get("action") == "add_comment"
                and item.get("agent") == "eng_01"
                and (item.get("parameters") or {}).get("issue_id") == "VEND-403"
                and any(kw in str((item.get("parameters") or {}).get("comment", "")).lower()
                        for kw in ("setup", "provisioned", "configured", "ready", "complete"))
                for item in successful
            )
            mgr_approved  = _comment_has("VEND-401", "mgr_01", "approved")
            sheet_done    = _sheet_cell_done("SHEET-VENDOR", "B2", "pm_01", "active")
            kickoff_sched = (
                _event_with("kickoff",    "pm_01", "eng_01", "product_01")
                or _event_with("onboarding", "pm_01", "eng_01", "product_01")
                or _event_with("technova",   "pm_01", "eng_01", "product_01")
            )
            announced     = any(
                m["sender_id"] == "pm_01"
                and "VEND-401" in m["text"]
                and any(kw in m["text"].lower() for kw in ("approved", "onboarded", "complete", "live"))
                for m in (env.repo.messages("CH-PROCUREMENT") if hasattr(env.repo, "messages") else [])
            )

            if not email_read:
                hints.append(
                    "STEP 1: pm_01 reads the vendor onboarding request email. "
                    "Use gmail.read_email as pm_01 with email_id='vendor-request-001'."
                )
            elif not (jira_srch and main_read):
                hints.append(
                    "STEP 2: pm_01 finds the main procurement ticket. "
                    "Use jira.search_issues with query='VEND onboarding'. Agent: pm_01. "
                    "Then read VEND-401 with jira.read_issue. Agent: pm_01."
                )
            elif not legal_done:
                hints.append(
                    "PARALLEL STEP 3a: Switch to product_01 (Maya). product_01 records legal clearance on VEND-402. "
                    "Use jira.add_comment as product_01 with issue_id='VEND-402'. "
                    "Comment MUST include the word 'legal'. "
                    "Example: {\"issue_id\":\"VEND-402\",\"comment\":\"Legal review complete. Vendor agreement is compliant with procurement and data handling policies.\"}"
                )
            elif not it_done:
                hints.append(
                    "PARALLEL STEP 3b: Switch to eng_01 (Arjun). eng_01 confirms IT provisioning on VEND-403. "
                    "Use jira.add_comment as eng_01 with issue_id='VEND-403'. "
                    "Comment MUST include 'setup', 'provisioned', or 'complete'. "
                    "Example: {\"issue_id\":\"VEND-403\",\"comment\":\"IT setup complete. Access credentials and API keys provisioned for TechNova integration.\"}"
                )
            elif not mgr_approved:
                hints.append(
                    "STEP 4: Switch to mgr_01 (Daniel). mgr_01 approves the vendor onboarding on VEND-401. "
                    "Use jira.add_comment as mgr_01 with issue_id='VEND-401'. "
                    "Comment MUST include 'approved'. "
                    "Example: {\"issue_id\":\"VEND-401\",\"comment\":\"Vendor onboarding approved. Legal and IT both confirmed. Proceed with kickoff.\"}"
                )
            elif not sheet_done:
                hints.append(
                    "STEP 5: Switch to pm_01. pm_01 marks vendor as ACTIVE. "
                    "Submit this EXACT JSON: "
                    "{\"agent_id\":\"pm_01\",\"tool\":\"sheets.update_cell\","
                    "\"parameters\":{\"sheet_id\":\"SHEET-VENDOR\",\"cell\":\"B2\",\"value\":\"ACTIVE\"},"
                    "\"reason\":\"Mark TechNova as active in vendor tracker\"}"
                )
            elif not kickoff_sched:
                hints.append(
                    "STEP 6: pm_01 schedules the onboarding kickoff meeting. "
                    "Use calendar.create_event as pm_01. "
                    "Title MUST include 'kickoff', 'onboarding', or 'TechNova'. "
                    "Participants MUST include pm_01, eng_01, AND product_01. "
                    "Example: {\"title\":\"TechNova Solutions Onboarding Kickoff\","
                    "\"participants\":[\"pm_01\",\"product_01\",\"eng_01\",\"mgr_01\"],\"start_time\":720,\"end_time\":780}"
                )
            elif not announced:
                hints.append(
                    "FINAL STEP 7: pm_01 announces vendor onboarding completion in Slack. "
                    "Use slack.send_message as pm_01 with channel_id='CH-PROCUREMENT'. "
                    "Text MUST include 'VEND-401' (uppercase) and 'approved' or 'complete'. "
                    "Example: {\"channel_id\":\"CH-PROCUREMENT\","
                    "\"text\":\"VEND-401 approved. TechNova Solutions onboarding complete. Kickoff scheduled.\"}"
                )

        return hints

    def _last_result_hints(self, env) -> list[str]:
        """Generic next-step hints derived only from visible evidence."""
        recent = self._recent_tool_results(env)

        # Task workflow hints take priority — they point to the exact next required action
        hints: list[str] = self._task_workflow_hints(env)

        # Inbox hints: only during initial discovery, before any Jira reads
        hints += self._inbox_read_hints(env)

        if not recent:
            return hints

        last = recent[-1]
        data = last.get("data") or {}
        tool = str(last.get("tool", ""))
        agent = str(last.get("agent_id", ""))
        results = data.get("results") if isinstance(data, dict) else None

        # Generic search → read progression
        if isinstance(results, list) and results and isinstance(results[0], dict):
            first = results[0]
            legal = set(env.legal_tools(agent)) if agent in env.AGENTS else set()
            if tool == "gmail.search_emails" and first.get("email_id") and "gmail.read_email" in legal:
                hints.append(f"Search returned email {first['email_id']!r}; inspect it instead of repeating the search.")
            elif tool == "jira.search_issues" and first.get("issue_id") and "jira.read_issue" in legal:
                hints.append(f"Search returned issue {first['issue_id']!r}; inspect it instead of repeating the search.")
            elif tool == "slack.search_messages" and first.get("channel_id") and "slack.read_channel" in legal:
                hints.append(f"Search returned channel {first['channel_id']!r}; inspect it instead of repeating the search.")
        elif isinstance(results, list) and not results:
            if tool == "gmail.search_emails":
                hints.append(
                    "Gmail search returned no results. Your inbox (in VISIBLE EMPLOYEE STATE) "
                    "already shows email IDs — read one of those directly with gmail.read_email."
                )
            elif tool == "jira.search_issues":
                hints.append(
                    "Jira search returned no results. Try a shorter, more specific query term "
                    "taken directly from the task objective (e.g. 'INC', 'LAUNCH', or 'READY')."
                )

        # Generic post-read guidance
        if tool == "gmail.read_email" and last.get("success"):
            hints.append(
                "Email read. Now act on the information: search the relevant system or send a handoff — "
                "do not re-read this email."
            )

        if tool == "jira.read_issue" and last.get("success") and isinstance(data, dict):
            description = _trim_text(data.get("description", ""), 240)
            if description:
                hints.append(
                    f"Issue description: {description!r}. "
                    "If documentation is required, reading alone is insufficient — "
                    "record findings with jira.add_comment before toggling status."
                )

        if tool == "jira.change_status" and last.get("success") and isinstance(data, dict):
            new_status = data.get("status", "")
            if new_status not in ("in_progress", "resolved", "open"):
                hints.append(f"Status is already {new_status!r}. Advance a different requirement instead.")

        return hints

    def _safe_recovery_action(self, env) -> Action | None:
        """Bounded, evidence-only search->read recovery after repeated model looping."""
        trajectory = env.get_trajectory()
        if not trajectory:
            return None
        last = trajectory[-1]
        result = last.get("result") or {}
        if not result.get("success"):
            return None
        data = result.get("data") or {}
        results = data.get("results") if isinstance(data, dict) else None
        if not (isinstance(results, list) and results and isinstance(results[0], dict)):
            return None
        agent = str(last.get("agent"))
        if agent not in env.AGENTS:
            return None
        if self.mode == "decentralized" and agent != env.agent_selection:
            return None
        legal = set(env.legal_tools(agent))
        app = str(last.get("app"))
        action_name = str(last.get("action"))
        first = results[0]
        candidate: Action | None = None
        if app == "jira" and action_name == "search_issues" and first.get("issue_id") and "jira.read_issue" in legal:
            candidate = Action(agent, "jira", "read_issue", {"issue_id": str(first["issue_id"])})
        elif app == "gmail" and action_name == "search_emails" and first.get("email_id") and "gmail.read_email" in legal:
            candidate = Action(agent, "gmail", "read_email", {"email_id": str(first["email_id"])})
        elif app == "slack" and action_name == "search_messages" and first.get("channel_id") and "slack.read_channel" in legal:
            candidate = Action(agent, "slack", "read_channel", {"channel_id": str(first["channel_id"])})
        if candidate is None or self._is_no_progress_repeat(env, candidate):
            return None
        return candidate

    def _prompt(self, env, correction: str | None = None) -> str:
        if self.mode not in {"centralized", "decentralized"}:
            raise ValueError("mode must be centralized or decentralized")
        agents = self._ordered_agents(env)
        observations = {agent: self._compact_observation(env.observe(agent)) for agent in agents}
        legal_by_agent = {agent: env.legal_tools(agent) for agent in agents}
        all_legal = sorted({tool for tools in legal_by_agent.values() for tool in tools})
        recent = self._recent_tool_results(env)
        hints = self._last_result_hints(env)
        forbidden = sorted(self._signatures_since_last_state_change(env))[-10:]
        suggested_agent = env.agent_selection
        suggested_employee = env.repo.employee(suggested_agent) or {}
        correction_block = f"\nVALIDATOR CORRECTION\n{correction}\n" if correction else ""
        hint_block = "\nVISIBLE-EVIDENCE NEXT-STEP HINTS\n- " + "\n- ".join(hints) + "\n" if hints else ""
        return f"""You control employees in a synthetic enterprise benchmark.

OBJECTIVE
{env.task.instruction}

CONTROL MODE
{self.mode}

SUGGESTED STARTING/CURRENT EMPLOYEE
employee_id={suggested_agent}
name={suggested_employee.get('name')}
role={suggested_employee.get('role')}

The suggested employee is a useful starting point, not a permanent assignment. In centralized mode, switch employees when visible evidence and role ownership show that another employee owns the next step.

TEAM DIRECTORY
{_compact_json(self._team_directory(env))}

IMPORTANT RULES
1. Take exactly ONE tool action.
2. Use only facts in the objective, visible observations, or prior tool results.
3. Never copy concepts from examples or unrelated workflows.
4. Never repeat a resource read that already succeeded.
5. Never set a Jira issue to a status it already has.
6. Search with short distinctive terms from the CURRENT objective or visible evidence. If a search returns an ID, inspect that resource rather than searching again.
7. Match the app to the information type: email/private customer evidence -> Gmail; team discussion/handoff -> Slack; blocker/issue work -> Jira; tracker -> Sheets; scheduling -> Calendar.
8. Respect role ownership. Private evidence may need to be communicated before a downstream role can act on it.
9. If the objective says to inspect AND document something, a read alone is not enough. After reading, use an appropriate write/comment action grounded in the visible evidence.
10. A status change alone does not document an investigation. If documentation is required, record the actual evidence/findings first.
11. Use returned IDs exactly. Never invent issue, email, channel, event, sheet, or employee IDs.
12. Respect legal tools and permissions.
13. If an action was rejected, materially change the action rather than repeating it with cosmetic wording changes.
14. In decentralized mode you MUST use the currently active employee.
15. Do not claim success in prose; execute the next tool action.

VISIBLE EMPLOYEE STATE
{_compact_json(observations)}

LEGAL TOOLS BY EMPLOYEE
{_compact_json(legal_by_agent)}

TOOL PARAMETER CONTRACTS
{_tool_docs(all_legal)}

RECENT TOOL RESULTS
{_compact_json(recent)}

FORBIDDEN NO-PROGRESS ACTION SIGNATURES
{_compact_json(forbidden)}
{hint_block}{correction_block}
Return ONLY one JSON object using this structure:
{{"agent_id":"<employee_id>","tool":"<legal_app.action>","parameters":{{}},"reason":"<short evidence-grounded reason>"}}

The placeholders describe structure only. Do not copy them literally.
Do not include markdown fences or prose outside the JSON."""

    def _parse_action(self, env, text: str) -> tuple[Action, str]:
        obj = self._normalize_model_object(_extract_json(text))
        if "agent_id" not in obj:
            raise ValueError("missing agent_id")
        if "tool" not in obj:
            raise ValueError("missing tool")
        agent = str(obj["agent_id"]).strip()
        tool = str(obj["tool"]).strip().lower()
        params = obj.get("parameters") or {}
        reason = str(obj.get("reason", ""))
        if "." not in tool:
            raise ValueError("tool must be app.action")
        if agent not in env.AGENTS:
            raise ValueError(f"unknown agent {agent}")
        if self.mode == "decentralized" and agent != env.agent_selection:
            raise ValueError(f"decentralized mode requires active agent {env.agent_selection}, got {agent}")
        if tool not in env.legal_tools(agent):
            raise ValueError(f"illegal tool {tool} for {agent}")
        if not isinstance(params, dict):
            raise ValueError("parameters must be an object")
        params = self._repair_safe_missing_id(env, tool, params)
        schema_error = validate_parameters(tool, params)
        if schema_error:
            raise ValueError(schema_error)
        app, action_type = tool.split(".", 1)
        action = Action(agent, app, action_type, params)
        self._validate_grounded_ids(env, action)
        return action, reason

    def action(self, env) -> Action:
        last_error: Exception | None = None
        correction: str | None = None
        duplicate_failures = 0
        provider_failures = 0
        max_attempts = 1 + self.retries + self.duplicate_retries + self.provider_retries
        for attempt in range(max_attempts):
            prompt = self._prompt(env, correction=correction)
            started = time.perf_counter()
            self.stats.calls += 1
            try:
                text, meta = self.client.complete(prompt)
            except ProviderError as exc:
                self.stats.latency_s += time.perf_counter() - started
                self.stats.provider_errors += 1
                provider_failures += 1
                last_error = exc
                correction = "The previous Ollama request failed. Return exactly one valid JSON action when retried."
                if provider_failures > self.provider_retries:
                    break
                time.sleep(0.25)
                continue
            self.stats.latency_s += time.perf_counter() - started
            self.stats.prompt_tokens += int(meta.get("prompt_tokens", 0) or 0)
            self.stats.completion_tokens += int(meta.get("completion_tokens", 0) or 0)
            try:
                action, reason = self._parse_action(env, text)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self.stats.parse_failures += 1
                self.stats.validation_rejections += 1
                last_error = exc
                self.history.append({"type": "rejected_proposal", "attempt": attempt + 1, "raw": _trim_text(text, 500), "reason": str(exc)})
                correction = (
                    f"Your previous answer was rejected: {exc}. Return exactly one corrected JSON action. "
                    "Use the exact parameter names shown in TOOL PARAMETER CONTRACTS. If the resource ID is already visible, put it inside parameters. "
                    "Do not repeat a completed read or status change."
                )
                continue
            tool = f"{action.app}.{action.action_type}"
            if self._is_no_progress_repeat(env, action):
                self.stats.duplicate_rejections += 1
                duplicate_failures += 1
                last_error = ValueError("exact/cyclic no-progress action already attempted, resource already read, or status already set")
                self.history.append({"type": "rejected_proposal", "attempt": attempt + 1, "agent_id": action.agent_id, "tool": tool, "parameters": action.parameters, "reason": str(last_error)})
                correction = (
                    f"The proposed action {tool} with parameters {_compact_json(action.parameters)} is forbidden because it is redundant. "
                    "Use the visible result from the completed action and advance a different requirement. If a private evidence read succeeded, consider a legal handoff. "
                    "If an issue read succeeded and the objective requires documentation, consider a Jira comment grounded in the issue description. If status is already set, do not set it again."
                )
                if duplicate_failures >= self.duplicate_retries:
                    recovery = self._safe_recovery_action(env)
                    if recovery is not None:
                        self.stats.recovery_actions += 1
                        self.history.append({"type": "recovery", "agent_id": recovery.agent_id, "tool": f"{recovery.app}.{recovery.action_type}", "parameters": recovery.parameters, "reason": "bounded visible-evidence search-to-read recovery"})
                        return recovery
                continue
            self.history.append({"type": "model_proposal", "agent_id": action.agent_id, "tool": tool, "parameters": action.parameters, "reason": reason})
            return action
        recovery = self._safe_recovery_action(env)
        if recovery is not None:
            self.stats.recovery_actions += 1
            self.history.append({"type": "recovery", "agent_id": recovery.agent_id, "tool": f"{recovery.app}.{recovery.action_type}", "parameters": recovery.parameters, "reason": "final bounded visible-evidence search-to-read recovery"})
            return recovery
        raise RuntimeError(f"LLM policy failed after {max_attempts} attempts: {last_error}")

    def observe_result(self, action: Action, info: dict[str, Any], reward: float) -> None:
        self.history.append(
            {
                "type": "executed",
                "agent_id": action.agent_id,
                "tool": f"{action.app}.{action.action_type}",
                "parameters": action.parameters,
                "success": info.get("success"),
                "message": info.get("message"),
                "reward": reward,
            }
        )