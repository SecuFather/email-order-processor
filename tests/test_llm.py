from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import config
import llm


def _assert_no_description(obj):
    if isinstance(obj, dict):
        assert "description" not in obj, f"Found description in {obj}"
        for v in obj.values():
            _assert_no_description(v)
    elif isinstance(obj, list):
        for item in obj:
            _assert_no_description(item)


def test_get_order_maker_tools_structure_and_no_descriptions():
    tools = llm.get_order_maker_tools(
        search_tool="search_catalog",
        set_request_tool="record_text",
        set_product_tool="record_product",
        resolve_ambiguity_tool="pick_product",
    )
    assert len(tools) == 4
    names = [t["function"]["name"] for t in tools]
    assert names == [
        "search_catalog",
        "record_text",
        "record_product",
        "pick_product",
    ]

    # Verify no description in any tool or property
    _assert_no_description(tools)

    # Check search tool parameters
    search_params = tools[0]["function"]["parameters"]
    assert search_params["type"] == "object"
    assert search_params["required"] == ["phrase", "limit", "page"]
    assert search_params["properties"]["phrase"] == {"type": "string"}
    assert search_params["properties"]["limit"] == {"type": "integer"}
    assert search_params["properties"]["page"] == {"type": "integer"}

    # Check resolve ambiguity tool parameters
    ambiguity_params = tools[3]["function"]["parameters"]
    assert ambiguity_params["required"] == ["ids"]
    assert ambiguity_params["properties"]["ids"] == {
        "type": "array",
        "items": {"type": "integer"},
    }


def test_get_company_tools_structure_and_no_descriptions():
    tools = llm.get_company_tools("save_company")
    assert len(tools) == 1
    tool = tools[0]
    assert tool["function"]["name"] == "save_company"

    # Verify no description in tool or properties
    _assert_no_description(tools)

    params = tool["function"]["parameters"]
    assert params["required"] == ["nip", "name", "adress", "zip_code", "city"]
    for field in ["nip", "name", "adress", "zip_code", "city"]:
        assert params["properties"][field] == {"type": "string"}


def test_parse_tools_no_descriptions():
    sys_msg = """
def lookup_item(item_id: int, tags: list, dry_run: bool = False):
    pass
"""
    tools = llm.parse_tools(sys_msg, "lookup_item")
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "lookup_item"
    _assert_no_description(tools)

    props = tools[0]["function"]["parameters"]["properties"]
    assert props["item_id"] == {"type": "integer"}
    assert props["tags"] == {"type": "array"}
    assert props["dry_run"] == {"type": "boolean"}
    assert tools[0]["function"]["parameters"]["required"] == ["item_id", "tags"]


@pytest.mark.anyio
async def test_list_models():
    fake_model_1 = MagicMock(model="qwen2.5:14b")
    fake_model_2 = MagicMock(model="llama3.2:latest")
    fake_res = MagicMock(models=[fake_model_1, fake_model_2])

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.list = AsyncMock(return_value=fake_res)

        models = await llm.list_models()
        assert models == ["qwen2.5:14b", "llama3.2:latest"]
        mock_client_cls.assert_called_once_with(host=config.OLLAMA_HOST)


@pytest.mark.anyio
async def test_chat():
    fake_res = MagicMock(message=MagicMock(content="Hello!"))

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(return_value=fake_res)

        res = await llm.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert res.message.content == "Hello!"
        mock_instance.chat.assert_called_once_with(
            model="llama3.2",
            messages=[{"role": "user", "content": "Hi"}],
            tools=None,
        )


@pytest.mark.anyio
async def test_chat_stream():
    fake_stream = MagicMock()

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(return_value=fake_stream)

        res = await llm.chat_stream(
            model="llama3.2",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert res == fake_stream
        mock_instance.chat.assert_called_once_with(
            model="llama3.2",
            messages=[{"role": "user", "content": "Hi"}],
            tools=None,
            stream=True,
        )


@pytest.mark.anyio
async def test_run_ollama():
    fake_msg = MagicMock()
    fake_msg.model_dump.return_value = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "test_tool", "arguments": {"x": 1}}}
        ],
    }
    fake_res = MagicMock(
        message=fake_msg,
        prompt_eval_count=20,
        eval_count=10,
    )

    with patch("llm.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.chat = AsyncMock(return_value=fake_res)

        sys_msg = "def test_tool(x: int): pass"
        messages = [{"role": "user", "content": "Run tool"}]
        result = await llm.run_ollama("llama3.2", sys_msg, "test_tool", messages)

        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "Run tool"}
        assert result[1]["role"] == "assistant"
        assert result[1]["stats"] == {"prompt_tokens": 20, "eval_tokens": 10}
        assert result[2] == {"role": "tool", "tool_name": "test_tool", "content": ""}
