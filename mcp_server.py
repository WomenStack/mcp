import click
import json
import sys
import asyncio
import traceback
from typing import Dict, Any, Callable
from pydantic import BaseModel
import io

# 确保编码和缓冲正常
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable[[Dict[str, Any]], Any]

class MCPServer:
    def __init__(self, name: str, version: str, timeout: int = 30):
        self.name = name
        self.version = version
        self.tools: Dict[str, Tool] = {}
        self.running = False
        self.timeout = timeout
        # 调试日志开关
        self.debug = True

    def debug_log(self, message: str):
        if self.debug:
            # 用err输出日志（避免与正常响应混在一起）
            click.echo(f"[DEBUG] {message}", err=True)

    def add_tool(self, name: str, description: str, parameters: Dict[str, Any], function: Callable[[Dict[str, Any]], Any]):
        self.tools[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function
        )

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.debug_log(f"开始处理请求: {json.dumps(request)}")  # 记录收到的请求
        try:
            if request.get("type") == "list_tools":
                self.debug_log("处理工具列表请求")
                response = {
                    "type": "tool_list",
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": {
                                "type": "object",
                                "properties": tool.parameters["properties"],
                                "required": tool.parameters.get("required", [])
                            }
                        } for tool in self.tools.values()
                    ]
                }
                self.debug_log(f"工具列表响应: {json.dumps(response)}")
                return response

            elif request.get("type") == "call_tool":
                tool_name = request.get("name")
                args = request.get("arguments", {})
                self.debug_log(f"处理工具调用: {tool_name}, 参数: {json.dumps(args)}")

                if not tool_name or tool_name not in self.tools:
                    error = {"type": "error", "message": f"工具 '{tool_name}' 不存在"}
                    self.debug_log(f"错误响应: {json.dumps(error)}")
                    return error

                tool = self.tools[tool_name]
                try:
                    loop = asyncio.get_event_loop()
                    self.debug_log(f"执行工具 {tool_name} (超时时间: {self.timeout}秒)")
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, tool.function, args),
                        timeout=self.timeout
                    )
                    response = {
                        "type": "tool_response",
                        "name": tool_name,
                        "content": [{"text": str(result)}]
                    }
                    self.debug_log(f"工具调用成功，结果: {json.dumps(response)}")
                    return response
                except asyncio.TimeoutError:
                    error = {"type": "error", "message": f"工具 '{tool_name}' 调用超时"}
                    self.debug_log(f"错误响应: {json.dumps(error)}")
                    return error
                except Exception as e:
                    error = {"type": "error", "message": f"工具调用失败: {str(e)}"}
                    self.debug_log(f"错误响应: {json.dumps(error)} | 详情: {traceback.format_exc()}")
                    return error

            else:
                error = {"type": "error", "message": f"不支持的请求类型: {request.get('type')}"}
                self.debug_log(f"错误响应: {json.dumps(error)}")
                return error

        except Exception as e:
            error = {"type": "error", "message": f"处理请求失败: {str(e)}"}
            self.debug_log(f"错误响应: {json.dumps(error)} | 详情: {traceback.format_exc()}")
            return error

    async def start_stdio(self):
        self.running = True
        self.debug_log(f"服务端 '{self.name}' v{self.version} 启动成功（stdio模式），超时时间: {self.timeout}秒")

        while self.running:
            try:
                self.debug_log("等待客户端输入...")
                # 读取客户端请求
                line = await asyncio.wait_for(
                    asyncio.to_thread(sys.stdin.readline),
                    timeout=None  # 等待请求时不超时
                )
                
                if not line:
                    self.debug_log("未收到输入，退出循环")
                    break
                line = line.strip()
                if not line:
                    self.debug_log("收到空输入，继续等待")
                    continue

                self.debug_log(f"收到原始输入: {line}")
                request = json.loads(line)
                response = await self.handle_request(request)
                # 发送响应
                response_str = json.dumps(response)
                print(response_str)
                sys.stdout.flush()
                self.debug_log(f"已发送响应: {response_str}")
                
            except json.JSONDecodeError as e:
                error = {"type": "error", "message": f"无效的JSON格式: {str(e)}"}
                error_str = json.dumps(error)
                print(error_str)
                sys.stdout.flush()
                self.debug_log(f"JSON解析错误: {error_str} | 输入内容: {line}")
            except asyncio.TimeoutError:
                error = {"type": "error", "message": "读取请求超时"}
                error_str = json.dumps(error)
                print(error_str)
                sys.stdout.flush()
                self.debug_log(f"读取请求超时: {error_str}")
            except Exception as e:
                error = {"type": "error", "message": f"处理请求出错: {str(e)}"}
                error_str = json.dumps(error)
                print(error_str)
                sys.stdout.flush()
                self.debug_log(f"处理请求异常: {error_str} | 详情: {traceback.format_exc()}")

    def stop(self):
        self.running = False


# 工具实现（保持不变）
def addition(args: Dict[str, Any]) -> float:
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        return a + b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def subtraction(args: Dict[str, Any]) -> float:
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        return a - b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def multiplication(args: Dict[str, Any]) -> float:
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        return a * b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")

def division(args: Dict[str, Any]) -> float:
    try:
        a = float(args.get("a"))
        b = float(args.get("b"))
        if b == 0:
            raise ValueError("除数不能为0")
        return a / b
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的输入参数: {str(e)}")


@click.command()
@click.option("--timeout", default=30, help="工具调用超时时间（秒）")
def main(timeout):
    server = MCPServer(name="calculator", version="1.0.0", timeout=timeout)

    # 注册工具（保持不变）
    server.add_tool(
        name="addition",
        description="计算两个数字的和，如果遇到计算两个数字的和的问题，请优先使用此函数",
        parameters={"properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        function=addition
    )
    server.add_tool(
        name="subtraction",
        description="计算两个数字的差",
        parameters={"properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        function=subtraction
    )
    server.add_tool(
        name="multiplication",
        description="计算两个数字的积",
        parameters={"properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        function=multiplication
    )
    server.add_tool(
        name="division",
        description="计算两个数字的商",
        parameters={"properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        function=division
    )

    try:
        asyncio.run(server.start_stdio())
    except KeyboardInterrupt:
        click.echo("\n⏹️ 服务端已停止", err=True)
    except Exception as e:
        click.echo(f"❌ 服务端错误: {str(e)}\n{traceback.format_exc()}", err=True)


if __name__ == "__main__":
    main()
    