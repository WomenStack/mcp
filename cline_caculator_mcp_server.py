#!/usr/bin/env python3
"""
Cline MCP 计算器服务器（JSON-RPC 2.0）
支持四则运算：addition, subtraction, multiplication, division
适合直接在 Cline 中启动
"""

import sys
import json
import asyncio
import traceback
from typing import Dict, Any, Callable

# ---------- 工具函数 ----------

def addition(args: Dict[str, Any]) -> float:
    a = float(args.get("a"))
    b = float(args.get("b"))
    return a + b

def subtraction(args: Dict[str, Any]) -> float:
    a = float(args.get("a"))
    b = float(args.get("b"))
    return a - b

def multiplication(args: Dict[str, Any]) -> float:
    a = float(args.get("a"))
    b = float(args.get("b"))
    return a * b

def division(args: Dict[str, Any]) -> float:
    a = float(args.get("a"))
    b = float(args.get("b"))
    if b == 0:
        raise ValueError("除数不能为0")
    return a / b

TOOLS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "addition": addition,
    "subtraction": subtraction,
    "multiplication": multiplication,
    "division": division
}

# ---------- JSON-RPC 处理 ----------

async def handle_request(request: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "tools": {}  # 必须是对象
                    },
                    "serverInfo": {
                        "name": "calculator",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": name,
                            "description": f"计算两个数字的{name}操作",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                                "required": ["a", "b"]
                            }
                        } for name in TOOLS.keys()
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name not in TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"未知工具: {tool_name}"}
                }

            loop = asyncio.get_event_loop()
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, TOOLS[tool_name], args),
                    timeout=timeout
                )
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": str(result)}
                        ]
                    }
                }
            except asyncio.TimeoutError:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": f"工具 '{tool_name}' 调用超时"}
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": f"工具调用失败: {str(e)}"}
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"不支持的方法: {method}"}
            }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": f"服务器内部错误: {str(e)}\n{traceback.format_exc()}"}
        }

# ---------- 主循环 ----------

async def main(timeout: int = 30):
    print("✅ Cline MCP Calculator Server 已启动", file=sys.stderr)

    while True:
        try:
            # 异步读取 stdin
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                error = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"JSON解析错误: {str(e)}"}}
                print(json.dumps(error))
                sys.stdout.flush()
                continue

            response = await handle_request(request, timeout)
            print(json.dumps(response))
            sys.stdout.flush()

        except Exception as e:
            error = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": f"服务器异常: {str(e)}\n{traceback.format_exc()}"}}
            print(json.dumps(error))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main(timeout=30))
