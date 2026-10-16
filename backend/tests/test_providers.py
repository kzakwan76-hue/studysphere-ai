import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.llm.base import ProviderError
from app.llm.providers import AnthropicProvider, OllamaProvider, build_provider

SECRET = "x" * 40


def ollama(handler) -> OllamaProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    return OllamaProvider("http://ollama.test", "tiny-model", 5.0, client=client)


def test_ollama_reply_is_returned_and_the_request_is_well_formed():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": " Hello [1] "}})

    assert ollama(handler).generate("sys", "usr", 123) == "Hello [1]"
    assert seen["path"] == "/api/chat"
    assert seen["body"]["stream"] is False and seen["body"]["model"] == "tiny-model"
    assert seen["body"]["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert seen["body"]["options"]["num_predict"] == 123


def _connect_error(_request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("boom")


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500),
        lambda request: httpx.Response(200, content=b"not json"),
        lambda request: httpx.Response(200, json={"oops": 1}),
        _connect_error,
    ],
)
def test_ollama_failures_become_provider_errors(handler):
    with pytest.raises(ProviderError):
        ollama(handler).generate("sys", "usr", 100)


class FakeMessages:
    def __init__(self, blocks=None, error: Exception | None = None) -> None:
        self.blocks = blocks or []
        self.error = error
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.blocks)


def anthropic_with(messages: FakeMessages) -> AnthropicProvider:
    return AnthropicProvider("key", "some-model", 5.0, client=SimpleNamespace(messages=messages))


def test_anthropic_text_blocks_are_joined_and_the_request_is_well_formed():
    messages = FakeMessages(
        [SimpleNamespace(type="text", text="Binary "), SimpleNamespace(type="tool_use"), SimpleNamespace(type="text", text="search [1]")]
    )
    assert anthropic_with(messages).generate("sys", "usr", 77) == "Binary search [1]"
    assert messages.kwargs["system"] == "sys" and messages.kwargs["max_tokens"] == 77
    assert messages.kwargs["messages"] == [{"role": "user", "content": "usr"}]


def test_anthropic_errors_become_provider_errors():
    with pytest.raises(ProviderError):
        anthropic_with(FakeMessages(error=RuntimeError("network down"))).generate("s", "u", 10)


def test_an_empty_anthropic_reply_is_an_error():
    with pytest.raises(ProviderError):
        anthropic_with(FakeMessages(blocks=[])).generate("s", "u", 10)


def test_none_means_no_provider():
    assert build_provider(Settings(secret_key=SECRET, llm_provider="none")) is None


def test_anthropic_requires_a_key():
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        build_provider(Settings(secret_key=SECRET, llm_provider="anthropic", anthropic_api_key=""))


def test_ollama_provider_is_built_from_the_settings():
    provider = build_provider(Settings(secret_key=SECRET, llm_provider="ollama"))
    assert isinstance(provider, OllamaProvider) and provider.name == "ollama"


def test_an_unknown_provider_name_is_rejected_at_startup():
    with pytest.raises(ValidationError):
        Settings(secret_key=SECRET, llm_provider="banana")