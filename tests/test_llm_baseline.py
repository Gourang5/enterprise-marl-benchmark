import json

from enterprise_env.evaluation.llm import LLMPolicy, _extract_json
from enterprise_env.evaluation.runner import run_llm_episode


class QueueClient:
    def __init__(self, actions):
        self.actions = list(actions)
        self.i = 0

    def complete(self, prompt):
        assert "Return ONLY one JSON object" in prompt

        if self.i >= len(self.actions):
            raise AssertionError("fake model ran out of actions")

        action = self.actions[self.i]
        self.i += 1

        return json.dumps(action), {
            "prompt_tokens": 100,
            "completion_tokens": 20,
        }


def test_extract_json_tolerates_fence_and_text():
    assert (
        _extract_json(
            '```json\n{"agent_id":"pm_01"}\n```'
        )["agent_id"]
        == "pm_01"
    )

    assert (
        _extract_json(
            'answer: {"agent_id":"eng_01"}'
        )["agent_id"]
        == "eng_01"
    )


def test_llm_policy_rejects_illegal_tool_and_retries():
    from enterprise_env.factory import make_env

    env = make_env("customer_incident")
    env.reset(seed=1)

    client = QueueClient(
        [
            {
                "agent_id": "eng_01",
                "tool": "jira.assign_issue",
                "parameters": {
                    "issue_id": "INC-421",
                    "assignee_id": "eng_01",
                },
            },
            {
                "agent_id": "pm_01",
                "tool": "gmail.search_emails",
                "parameters": {
                    "query": "authentication outage"
                },
            },
        ]
    )

    policy = LLMPolicy(client, retries=1)
    action = policy.action(env)

    assert action.agent_id == "pm_01"
    assert action.action_type == "search_emails"
    assert policy.stats.parse_failures == 1

    env.close()


def test_full_llm_harness_with_deterministic_fake_model():
    actions = [
        {
            "agent_id": "pm_01",
            "tool": "gmail.search_emails",
            "parameters": {
                "query": "authentication outage"
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "gmail.read_email",
            "parameters": {
                "email_id": "seed-email-001"
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "jira.search_issues",
            "parameters": {
                "query": "authentication failures"
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "jira.read_issue",
            "parameters": {
                "issue_id": "INC-421"
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "jira.assign_issue",
            "parameters": {
                "issue_id": "INC-421",
                "assignee_id": "eng_01",
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "slack.send_message",
            "parameters": {
                "channel_id": "CH-INCIDENTS",
                "text": (
                    "INC-421 assigned to Arjun. "
                    "Please investigate the auth gateway regression."
                ),
                "mentions": ["eng_01"],
            },
        },
        {
            "agent_id": "eng_01",
            "tool": "jira.add_comment",
            "parameters": {
                "issue_id": "INC-421",
                "comment": (
                    "Investigating auth gateway rollout regression "
                    "and token validation path."
                ),
            },
        },
        {
            "agent_id": "eng_01",
            "tool": "jira.change_status",
            "parameters": {
                "issue_id": "INC-421",
                "status": "in_progress",
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "calendar.create_event",
            "parameters": {
                "event_id": "INC-EVENT",
                "title": "INC-421 Incident Review",
                "participants": ["eng_01"],
                "start_time": 780,
                "end_time": 810,
            },
        },
        {
            "agent_id": "eng_01",
            "tool": "jira.change_status",
            "parameters": {
                "issue_id": "INC-421",
                "status": "resolved",
            },
        },
        {
            "agent_id": "pm_01",
            "tool": "gmail.send_email",
            "parameters": {
                "email_id": "resolution-email",
                "recipient_id": "cs_01",
                "subject": "INC-421 resolved",
                "body": (
                    "INC-421 is resolved after investigation "
                    "of the authentication gateway regression."
                ),
            },
        },
    ]

    result = run_llm_episode(
        "customer_incident",
        QueueClient(actions),
        seed=42,
    )

    assert result["success"] is True
    assert result["steps"] == 11
    assert result["llm"]["calls"] == 11
    assert result["llm"]["prompt_tokens"] == 1100
    assert result["policy_error"] is None


def test_inbox_hints_appear_when_inbox_has_unread_email():
    """When inbox has unread email, _inbox_read_hints suggests reading by ID."""
    from enterprise_env.factory import make_env
    from enterprise_env.evaluation.llm import LLMPolicy

    env = make_env("customer_incident")
    env.reset(seed=42)

    policy = LLMPolicy(client=None)  # type: ignore[arg-type]
    hints = policy._inbox_read_hints(env)

    # pm_01 starts with unread emails — hint must mention gmail.read_email and at least one email ID
    inbox_hint = " ".join(hints)
    assert hints, "Expected at least one inbox hint"
    assert "gmail.read_email" in inbox_hint
    assert "pm_01" in inbox_hint

    env.close()


def test_empty_search_result_hint_appears():
    """After an empty Gmail search, prompt contains a hint about inbox IDs."""
    from enterprise_env.factory import make_env
    from enterprise_env.evaluation.llm import LLMPolicy

    env = make_env("customer_incident")
    env.reset(seed=42)

    policy = LLMPolicy(client=None)  # type: ignore[arg-type]

    # Inject a fake trajectory step with empty results
    env.trajectory.append({
        "step": 0,
        "agent": "pm_01",
        "app": "gmail",
        "action": "search_emails",
        "parameters": {"query": "xyz_no_match_xyz"},
        "result": {"success": True, "data": {"results": []}, "changed": False},
        "reward": 0.0,
        "progress": 0.0,
        "reward_components": {},
        "subgoals": {},
    })

    hints = policy._last_result_hints(env)
    hint_text = " ".join(hints)
    assert "inbox" in hint_text.lower() or "gmail.read_email" in hint_text, (
        f"Expected inbox guidance after empty search. Got: {hints}"
    )

    env.close()


def test_ollama_response_parser(monkeypatch):
    import enterprise_env.evaluation.llm as mod

    def fake_post(
        url,
        headers,
        payload,
        timeout=300,
    ):
        assert url.endswith("/api/chat")
        assert payload["stream"] is False
        assert payload["format"] == "json"
        assert payload["model"] == "qwen2.5:3b"

        return {
            "message": {
                "role": "assistant",
                "content": '{"agent_id":"pm_01"}',
            },
            "prompt_eval_count": 17,
            "eval_count": 6,
        }

    monkeypatch.setattr(
        mod,
        "_post_json",
        fake_post,
    )

    client = mod.OllamaChatClient(
        "qwen2.5:3b"
    )

    text, meta = client.complete("hello")

    assert "pm_01" in text

    assert meta == {
        "prompt_tokens": 17,
        "completion_tokens": 6,
    }


def test_gemini_response_parser(monkeypatch):
    """Gemini returns a candidates list; verify client extracts the text correctly."""
    import enterprise_env.evaluation.llm as mod

    def fake_post(url, headers, payload, timeout=60):
        assert "generateContent" in url
        assert "key=" in url
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": '{"agent_id":"pm_01","tool":"gmail.search_emails","parameters":{"query":"auth"},"reason":"test"}'}],
                        "role": "model",
                    }
                }
            ],
            "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 20},
        }

    monkeypatch.setattr(mod, "_post_json", fake_post)
    client = mod.GeminiChatClient(mod.GEMINI_DEFAULT_MODEL, api_key="AQ.FakeKeyForTesting")
    text, meta = client.complete("hello")
    assert "pm_01" in text
    assert meta == {"prompt_tokens": 50, "completion_tokens": 20}


def test_qwen_response_parser(monkeypatch):
    """Qwen/DashScope uses OpenAI-compatible response; verify client extracts it."""
    import enterprise_env.evaluation.llm as mod

    def fake_post(url, headers, payload, timeout=60):
        assert "dashscope" in url
        assert "Bearer" in headers.get("Authorization", "")
        return {
            "choices": [
                {"message": {"role": "assistant", "content": '{"agent_id":"eng_01","tool":"jira.read_issue","parameters":{"issue_id":"INC-421"},"reason":"test"}'}}
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15},
        }

    monkeypatch.setattr(mod, "_post_json", fake_post)
    client = mod.QwenChatClient("qwen-turbo", api_key="fake-key")
    text, meta = client.complete("hello")
    assert "eng_01" in text
    assert meta == {"prompt_tokens": 30, "completion_tokens": 15}


def test_make_client_ollama_instantiates():
    import enterprise_env.evaluation.llm as mod

    client = mod.make_client("ollama")

    assert isinstance(client, mod.OllamaChatClient)
    assert client.model == mod.OLLAMA_DEFAULT_MODEL
    assert client.base_url == "http://localhost:11434"


def test_make_client_allows_custom_ollama_model():
    import enterprise_env.evaluation.llm as mod

    client = mod.make_client("ollama", model="qwen2.5:7b")
    assert isinstance(client, mod.OllamaChatClient)
    assert client.model == "qwen2.5:7b"


def test_make_client_rejects_unknown_providers():
    import enterprise_env.evaluation.llm as mod

    unknown_providers = [
        "huggingface",
        "openai",
        "bedrock",
        "vertex",
        "cohere",
    ]

    for provider in unknown_providers:
        try:
            mod.make_client(provider)
            assert False, f"{provider} should not be supported"
        except ValueError as exc:
            assert "Unsupported provider" in str(exc), (
                f"Expected 'Unsupported provider' in error for {provider}, got: {exc}"
            )


def test_make_client_supports_all_providers():
    import enterprise_env.evaluation.llm as mod

    # Each provider instantiates when given a dummy key (no network call yet)
    groq = mod.make_client("groq", api_key="test-key")
    assert isinstance(groq, mod.GroqChatClient)
    assert groq.model == mod.GROQ_DEFAULT_MODEL

    anthropic = mod.make_client("anthropic", api_key="test-key")
    assert isinstance(anthropic, mod.AnthropicChatClient)
    assert anthropic.model == mod.ANTHROPIC_DEFAULT_MODEL

    gemini = mod.make_client("gemini", api_key="AQ.FakeKeyForTesting")
    assert isinstance(gemini, mod.GeminiChatClient)
    assert gemini.model == mod.GEMINI_DEFAULT_MODEL

    qwen = mod.make_client("qwen", api_key="test-key")
    assert isinstance(qwen, mod.QwenChatClient)
    assert qwen.model == mod.QWEN_DEFAULT_MODEL


def test_all_hosted_clients_raise_without_api_key(monkeypatch):
    import enterprise_env.evaluation.llm as mod

    checks = [
        ("GroqChatClient",      "GROQ_API_KEY",      "GROQ_API_KEY"),
        ("AnthropicChatClient", "ANTHROPIC_API_KEY",  "ANTHROPIC_API_KEY"),
        ("QwenChatClient",      "DASHSCOPE_API_KEY",  "DASHSCOPE_API_KEY"),
    ]

    for cls_name, env_var, expected_hint in checks:
        monkeypatch.delenv(env_var, raising=False)
        cls = getattr(mod, cls_name)
        try:
            cls(api_key=None)
            assert False, f"{cls_name} should raise ProviderError without API key"
        except mod.ProviderError as exc:
            assert expected_hint in str(exc), (
                f"{cls_name}: expected hint about {expected_hint}, got: {exc}"
            )

    # Gemini: no key at all → must raise with helpful message
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    try:
        mod.GeminiChatClient(api_key=None)
        assert False, "GeminiChatClient should raise without key"
    except mod.ProviderError as exc:
        assert "aistudio.google.com" in str(exc)

    # Gemini: AQ. prefix key is also accepted (newer Google key format)
    client = mod.GeminiChatClient(api_key="AQ.some_new_format_key")
    assert client.api_key.startswith("AQ.")


def test_make_client_supports_all_providers_with_any_key():
    """make_client accepts any non-empty string as Gemini key (format validated by API)."""
    import enterprise_env.evaluation.llm as mod

    for key in ("AIzaFakeKey", "AQ.NewFormatKey"):
        gemini = mod.make_client("gemini", api_key=key)
        assert isinstance(gemini, mod.GeminiChatClient)