"""
Unit tests for llm.py

All Groq calls are mocked.
No network requests are made.
"""

import llm
import config


# ---------------------------------------------------------------------
# Demo response
# ---------------------------------------------------------------------

def test_demo_response_contains_context():

    prompt = """
CONTEXT:
Security Guide:
Supports SSO and MFA.

REQUIREMENT:
Describe security.
"""

    result = llm._demo_response(prompt)

    assert "Supports SSO" in result


def test_demo_response_without_context():

    result = llm._demo_response("Hello")

    assert "relevant internal material" in result


# ---------------------------------------------------------------------
# last_error / used_demo
# ---------------------------------------------------------------------

def test_last_error_returns_string():

    assert isinstance(llm.last_error(), str)


def test_used_demo_returns_boolean():

    assert isinstance(llm.used_demo(), bool)


# ---------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------

def test_get_client_without_api_key(monkeypatch):

    monkeypatch.setattr(
        config,
        "GROQ_API_KEY",
        "",
    )

    llm._client = None

    client = llm._get_client()

    assert client is None


def test_llm_available_false(monkeypatch):

    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: None,
    )

    assert llm.llm_available() is False


def test_llm_available_true(monkeypatch):

    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: object(),
    )

    assert llm.llm_available() is True


# ---------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------

def test_chat_demo_mode(monkeypatch):

    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: None,
    )

    response = llm.chat(
        "system",
        "user",
    )

    assert isinstance(response, str)

    assert llm.used_demo() is True


def test_chat_success(monkeypatch):

    class FakeChoice:

        class Message:
            content = "Generated proposal"

        message = Message()


    class FakeUsage:
        pass


    class FakeResponse:

        choices = [FakeChoice()]
        usage = FakeUsage()


    class FakeCompletions:

        def create(self, **kwargs):
            return FakeResponse()


    class FakeChat:

        completions = FakeCompletions()


    class FakeClient:

        chat = FakeChat()


    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: FakeClient(),
    )

    result = llm.chat(
        "system",
        "user",
    )

    assert result == "Generated proposal"

    assert llm.used_demo() is False


def test_chat_exception_falls_back(monkeypatch):

    class FakeCompletions:

        def create(self, **kwargs):
            raise RuntimeError("Groq failed")


    class FakeChat:

        completions = FakeCompletions()


    class FakeClient:

        chat = FakeChat()


    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: FakeClient(),
    )

    result = llm.chat(
        "system",
        "user",
    )

    assert isinstance(result, str)

    assert llm.used_demo() is True

    assert "demo mode" in result.lower()


# ---------------------------------------------------------------------
# ping()
# ---------------------------------------------------------------------

def test_ping_without_key(monkeypatch):

    monkeypatch.setattr(
        config,
        "GROQ_API_KEY",
        "",
    )

    result = llm.ping()

    assert result["ok"] is False


def test_ping_client_none(monkeypatch):

    monkeypatch.setattr(
        config,
        "GROQ_API_KEY",
        "abc",
    )

    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: None,
    )

    result = llm.ping()

    assert result["ok"] is False


def test_ping_success(monkeypatch):

    class FakeChoice:

        class Message:
            content = "pong"

        message = Message()


    class FakeResponse:

        choices = [FakeChoice()]


    class FakeCompletions:

        def create(self, **kwargs):
            return FakeResponse()


    class FakeChat:

        completions = FakeCompletions()


    class FakeClient:

        chat = FakeChat()


    monkeypatch.setattr(
        config,
        "GROQ_API_KEY",
        "abc",
    )

    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: FakeClient(),
    )

    result = llm.ping()

    assert result["ok"] is True

    assert "Connected" in result["message"]


def test_ping_exception(monkeypatch):

    class FakeCompletions:

        def create(self, **kwargs):
            raise RuntimeError("Invalid API key")


    class FakeChat:

        completions = FakeCompletions()


    class FakeClient:

        chat = FakeChat()


    monkeypatch.setattr(
        config,
        "GROQ_API_KEY",
        "abc",
    )

    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: FakeClient(),
    )

    result = llm.ping()

    assert result["ok"] is False

    assert "Invalid API key" in result["message"]


# ---------------------------------------------------------------------
# Demo response error message
# ---------------------------------------------------------------------

def test_demo_response_with_error():

    result = llm._demo_response(
        "hello",
        error="Timeout",
    )

    assert "Timeout" not in result

    assert "demo mode" in result.lower()