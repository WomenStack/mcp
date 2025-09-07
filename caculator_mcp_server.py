#!/usr/bin/env python3
"""
Cline MCP 计算器服务器
支持 JSON-RPC 2.0 协议
实现四则运算工具：addition, subtraction, multiplication, division
"""

import sys
import json

# ---------- 工具函数 ----------

def addition(args):
    a = float(args.get("a"))
    b = float(args.get("b"))
    return a + b

def subtraction(args):
    a = float(args.get("a"))
    b = float(args.get("b"))
    return a - b

def multiplication(args):
    a = float(args.get("a"))
    b = float(args.get("b"))
    return a * b

def division(args):
    a = float(args.get("a"))
    b = float(args.get("b"))
    if b == 0:
        raise ValueError("除数不能为0")
    return a / b


# ---------- JSON-RPC 请求处理 ----------

def handle_jsonrpc_request(request):
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        # ⚠ 修复：capabilities.tools 必须是对象
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {}  # 必须是对象，不能是布尔值
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
                        "name": "addition",
                        "description": "计算两个数字的和",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["a", "b"]
                        }
                    },
                    {
                        "name": "subtraction",
                        "description": "计算两个数字的差",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["a", "b"]
                        }
                    },
                    {
                        "name": "multiplication",
                        "description": "计算两个数字的积",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["a", "b"]
                        }
                    },
                    {
                        "name": "division",
                        "description": "计算两个数字的商（除数不能为0）",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["a", "b"]
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "addition":
                result = addition(arguments)
            elif tool_name == "subtraction":
                result = subtraction(arguments)
            elif tool_name == "multiplication":
                result = multiplication(arguments)
            elif tool_name == "division":
                result = division(arguments)
            else:
                raise ValueError(f"未知工具: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": f"工具调用失败: {str(e)}"
                }
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"不支持的方法: {method}"
            }
        }


# ---------- 主循环 ----------

def main():
    print("✅ Cline MCP Calculator Server 已启动", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_jsonrpc_request(request)
        except json.JSONDecodeError as e:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"JSON解析错误: {str(e)}"
                }
            }
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"服务器错误: {str(e)}"
                }
            }

        # 输出到 stdout，供 Cline 读取
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
