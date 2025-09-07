#!/usr/bin/env python3
"""
支持Cline的MCP服务器
支持JSON-RPC 2.0协议
"""

import json
import sys

def addition(args):
    """计算两个数字的和"""
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        return a + b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def subtraction(args):
    """计算两个数字的差"""
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        return a - b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def multiplication(args):
    """计算两个数字的积"""
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        return a * b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def division(args):
    """计算两个数字的商"""
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        if b == 0:
            raise ValueError("除数不能为0")
        return a / b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def handle_jsonrpc_request(request):
    """处理JSON-RPC请求"""
    try:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        print(f"处理JSON-RPC方法: {method}", file=sys.stderr)
        
        if method == "initialize":
            # 响应initialize请求
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "calculator",
                        "version": "1.0.0"
                    }
                }
            }
            return response
        
        elif method == "tools/list":
            # 返回工具列表
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "addition",
                            "description": "计算两个数字的和，如果遇到计算两个数字的和的问题，请优先使用此函数",
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
                            "description": "计算两个数字的商",
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
            return response
        
        elif method == "tools/call":
            # 调用工具
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            print(f"调用工具: {tool_name}, 参数: {arguments}", file=sys.stderr)
            
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
                    raise ValueError(f"工具 '{tool_name}' 不存在")
                
                response = {
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
                return response
                
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32000,
                        "message": f"工具调用失败: {str(e)}"
                    }
                }
                return response
        
        else:
            # 不支持的方法
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"不支持的方法: {method}"
                }
            }
            return response
    
    except Exception as e:
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": f"内部错误: {str(e)}"
            }
        }
        return response

def main():
    print("Cline MCP计算器服务器启动", file=sys.stderr)
    
    try:
        # 读取输入
        line = sys.stdin.readline()
        print(f"收到输入: {line.strip()}", file=sys.stderr)
        
        if line:
            try:
                request = json.loads(line.strip())
                print(f"解析请求: {request}", file=sys.stderr)
                
                response = handle_jsonrpc_request(request)
                print(f"生成响应: {response}", file=sys.stderr)
                
                print(json.dumps(response))
                sys.stdout.flush()
                print("发送响应完成", file=sys.stderr)
                
            except json.JSONDecodeError as e:
                error = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"JSON解析错误: {str(e)}"
                    }
                }
                print(json.dumps(error))
                sys.stdout.flush()
                print(f"JSON解析错误: {e}", file=sys.stderr)
        else:
            print("没有收到输入", file=sys.stderr)
            
    except Exception as e:
        error = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"服务器错误: {str(e)}"
            }
        }
        print(json.dumps(error))
        sys.stdout.flush()
        print(f"服务器异常: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
