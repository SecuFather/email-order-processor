import ast
import re
from typing import Any

from ollama import AsyncClient

import config

TYPE_MAP = {
    "int": "integer",
    "str": "string",
    "list": "array",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
}


def parse_tools(system_message: str, tool_names_raw: str) -> list[dict[str, Any]]:
    wanted = [t for t in re.split(r"[,\s]+", tool_names_raw) if t]
    signatures = dict(re.findall(r"def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)", system_message))
    tools = []
    for name in wanted:
        if name not in signatures:
            continue
        fn_ast: Any = ast.parse(f"def {name}({signatures[name]}): pass").body[0]
        args = fn_ast.args.args
        num_required = len(args) - len(fn_ast.args.defaults)
        props = {}
        required = []
        for i, arg in enumerate(args):
            ann = arg.annotation
            t_name = (
                ann.value.id
                if isinstance(ann, ast.Subscript)
                else (ann.id if isinstance(ann, ast.Name) else "str")
            )
            props[arg.arg] = {"type": TYPE_MAP.get(t_name, "string")}
            if i < num_required:
                required.append(arg.arg)
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
            }
        )
    return tools


def get_order_maker_tools(
    search_tool: str,
    set_request_tool: str,
    set_product_tool: str,
    resolve_ambiguity_tool: str,
) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": search_tool,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phrase": {"type": "string"},
                        "limit": {"type": "integer"},
                        "page": {"type": "integer"},
                    },
                    "required": ["phrase", "limit", "page"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": set_request_tool,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "at": {"type": "integer"},
                        "text": {"type": "string"},
                    },
                    "required": ["at", "text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": set_product_tool,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "at": {"type": "integer"},
                        "product_id": {"type": "integer"},
                        "amount": {"type": "number"},
                    },
                    "required": ["at", "product_id", "amount"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": resolve_ambiguity_tool,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": ["ids"],
                },
            },
        },
    ]


def get_company_tools(tool_name: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nip": {"type": "string"},
                        "name": {"type": "string"},
                        "adress": {"type": "string"},
                        "zip_code": {"type": "string"},
                        "city": {"type": "string"},
                    },
                    "required": ["nip", "name", "adress", "zip_code", "city"],
                },
            },
        }
    ]


def get_shipping_tools(tool_name: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nip": {"type": "string"},
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "zip_code": {"type": "string"},
                        "city": {"type": "string"},
                        "phone": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["name", "address", "zip_code", "city"],
                },
            },
        }
    ]


async def list_models() -> list[str]:
    client = AsyncClient(host=config.OLLAMA_HOST)
    res = await client.list()
    return [m.model for m in res.models]


async def chat(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    format: str | dict[str, Any] | None = None,
):
    client = AsyncClient(host=config.OLLAMA_HOST)
    kwargs: dict[str, Any] = {"format": format} if format is not None else {}
    return await client.chat(model=model, messages=messages, tools=tools, **kwargs)


async def chat_stream(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    format: str | dict[str, Any] | None = None,
):
    client = AsyncClient(host=config.OLLAMA_HOST)
    kwargs: dict[str, Any] = {"format": format} if format is not None else {}
    return await client.chat(
        model=model, messages=messages, tools=tools, stream=True, **kwargs
    )


async def run_ollama(
    model: str,
    system_message: str,
    tools_str: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chat_messages = [{"role": "system", "content": system_message}, *messages]
    res = await chat(
        model=model,
        messages=chat_messages,
        tools=parse_tools(system_message, tools_str),
    )
    msg = res.message.model_dump()
    msg["stats"] = {
        "prompt_tokens": res.prompt_eval_count or 0,
        "eval_tokens": res.eval_count or 0,
    }
    next_messages = [*messages, msg]
    for tc in msg.get("tool_calls") or []:
        next_messages.append(
            {"role": "tool", "tool_name": tc["function"]["name"], "content": ""}
        )
    return next_messages
