import logging
import uuid
import asyncio
import json
import sys
from typing import Dict, List, Any
import click
import aiohttp
from pydantic import BaseModel
from typing import List, Dict, Any, Optional  # 添加Optional导入

# LLM配置模型
class LLMConfig(BaseModel):
    api_key: str
    base_url: str
    model_name: str
    timeout: int = 180  # 超时时间（秒）

class MCPClient:
    def __init__(self, llm_config: LLMConfig):
        self.process = None  # 服务端进程
        self.tools: List[Dict[str, Any]] = []  # 工具列表 参考工具定义的json格式，使用字典列表存储数据
        self.connected = False #标示连接状态
        self.llm_config = llm_config  # 大模型参数配置
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=llm_config.timeout))  # 创建异步对话 超时时间与LLM一致

    """连接到MCP服务端并初始化工具列表"""
    async def connect(self, server_path: str) -> bool:
        try:
            # 启动服务端进程
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, server_path,    #python解释器路径 服务端脚本路径
                stdin=asyncio.subprocess.PIPE,  # 标准异步输入 
                stdout=asyncio.subprocess.PIPE,  # 标准异步输出
                stderr=asyncio.subprocess.PIPE,   #标准错误管道
                text=False     #非文本模式，二进制模式
            )
            self.connected = True
            click.echo("🔗 已连接到MCP服务端")

            # 获取工具列表
            self.tools = await self.list_tools()      # 异步执行，在执行函数connect时执行list_tools()
            click.echo(f"🔧 可用工具: {[t['name'] for t in self.tools]}")   # f 在字符串中嵌入变量
            
            # 测试LLM连接
            await self.test_llm_connection()  #异步执行连接测试
            return True
        except Exception as e:
            click.echo(f"❌ 连接失败: {str(e)}")
            await self.disconnect()  # 确保资源释放
            return False

    """测试与LLM模型的连接"""
    async def test_llm_connection(self) -> None:
        click.echo(f"📡 测试LLM模型连接 ({self.llm_config.model_name})...")
        try:
            response = await self.call_llm([
                {"role": "system", "content": "仅返回'模型连接成功'，无其他内容"},     #系统提示词
                {"role": "user", "content": "测试连接"}       #用户提示词
            ])
            # 兼容不同LLM返回格式
            if isinstance(response, dict) and "choices" in response:    #openai标准返回结构
                content = response["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"LLM返回格式异常: {response}")
            
            if "模型连接成功" in content:
                click.echo(f"✅ LLM模型连接测试成功")
            else:
                raise Exception(f"模型响应异常: {content}")
        except Exception as e:
            click.echo(f"❌ LLM模型连接测试失败: {str(e)}")
            raise

    """调用LLM模型生成响应"""
    async def call_llm(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:  #对话历史（role system content）-> 返回值
        headers = {  #请求头
            "Content-Type": "application/json",   # 请求体格式为json
            "Authorization": f"Bearer {self.llm_config.api_key}"     #使用api_key认证
        }
        payload = {  #请求体
            "model": self.llm_config.model_name,  #模型名称
            "messages": messages,   #对话历史/上下文
            "temperature": 0.1    #输出随机性
        }

        async with self.session.post(   #请求头管理器，效同请求结束释放资源
            f"{self.llm_config.base_url}/chat/completions",   #拼接API地址    f允许在字符串中直接嵌入表达式
            headers=headers,   #请求头认证
            json=payload   #请求体
        ) as resp:
            if resp.status != 200:
                raise Exception(f"LLM调用失败 [状态码: {resp.status}]: {await resp.text()}")
            return await resp.json()    #若请求成功，返回详细信息

    """发送请求到服务端并获取响应"""
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not self.connected or not self.process:
            raise Exception("未连接到服务端")

        try:
            request_str = json.dumps(request) + "\n"    #转成json格式
            self.process.stdin.write(request_str.encode('utf-8'))   #使用utf-8编码
            await self.process.stdin.drain()   #序列化并写入进程

            response_bytes = await asyncio.wait_for(
                self.process.stdout.readline(),    #读取标准输出
                timeout=30
            )
            if not response_bytes:
                err_bytes = await self.process.stderr.readline()    #读取错误信息
                err_str = err_bytes.decode('utf-8').strip()    #解码错误信息
                return {"type": "error", "message": f"无响应，错误: {err_str}"}    #输出

            return json.loads(response_bytes.decode('utf-8').strip())
        except asyncio.TimeoutError:
            return {"type": "error", "message": "请求超时（30秒）"}
        except Exception as e:
            return {"type": "error", "message": f"通信错误: {str(e)}"}

    """获取服务端工具列表"""
    async def list_tools(self) -> List[Dict[str, Any]]:
        response = await self.send_request({"type": "list_tools"})    #分type tools两个字典
        # print("aaaaaaa查看tool_list:",response)
        if response.get("type") == "tool_list":
            return response.get("tools", [])   #只保留tools的字典
        else:
            raise Exception(f"获取工具失败: {response.get('message', '未知错误')}")

    """调用服务端工具"""
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        print("调用服务端工具信息")
        return await self.send_request({
            "type": "call_tool",
            "name": tool_name,
            "arguments": args
        })

    #处理用户查询
    async def process_query(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]     #初始messages 用户角色+用户需求提示词
        final_response = "⚠️ 未生成有效回答"    #设置最终回答初始值

        try:
            # 1. 获取初始LLM响应
            system_prompt = self._build_system_prompt()       #构建系统提示词：服务端工具信息   包括服务端的工具名称+必填参数
            initial_messages = [{"role": "system", "content": system_prompt}] + messages     #初始信息包括系统提示词和用户提示词
            initial_response = await self.call_llm(initial_messages)    #将提示词输入到LLM中
            print("检查 initial_response:",initial_response)
            initial_content = initial_response["choices"][0]["message"].get("content", "").strip()     #获取回复内容  回复内容中包含使用的工具信息                                     
            # 2. 尝试解析工具调用
            tool_calls = self._parse_tool_calls(initial_content)   #初始回复内容，返回工具调用信息
            if not tool_calls:    #若为空值，则返回空值/未生成有效回答
                return initial_content or final_response

            # 3. 执行工具调用
            tool_results = []
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool_name")
                if not tool_name:   #若数值为空，跳出当前循环
                    continue

                try:
                    # 执行工具并处理响应
                    tool_args = tool_call.get("parameters", {})
                    tool_response = await self.call_tool(tool_name, tool_args)
                    print(f"工具调用返回结果：{tool_response}")
                    
                    # 标准化工具响应
                    tool_output = self._format_tool_response(tool_response)  #result
                except Exception as e:
                    tool_output = f"工具执行失败: {str(e)}"

                tool_results.append({
                    "role": "tool",
                    "content": tool_output,
                    "tool_call_id": f"call_{i}",
                    "name": tool_name
                })

            # 4. 构建工具调用历史
            messages.append({
                "role": "assistant",
                "content": initial_content,
                "tool_calls": [{
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": call["tool_name"],
                        "arguments": json.dumps(call.get("parameters", {}))
                    }
                } for i, call in enumerate(tool_calls)]
            })
            messages.extend(tool_results)

            # 5. 获取最终响应
            final_messages = [{"role": "system", "content": system_prompt}] + messages  #将工具返回结果再次放入AI中
            final_response = await self._get_final_response(final_messages)  #使用AI获取最终结果
            
            return final_response

        except Exception as e:
            logging.error(f"处理查询失败: {str(e)}")
            return f"处理查询时出错: {str(e)}"

    """解析内容中的工具调用"""
    def _parse_tool_calls(self, content: str) -> List[Dict]:
        if not content:
            return []

        # 尝试提取JSON代码块
        json_str = self._extract_json_block(content)   #返回tool_calls的json格式信息
        if not json_str:    #如果输入内容为空 直接返回空列表
            json_str = content

        try:
            data = json.loads(json_str)   #转换为python可解释对象
            if isinstance(data, dict):    #若为字典类型
                calls = data.get("tool_calls", [])   #提取工具使用信息
                return [calls] if isinstance(calls, dict) else calls    #若为字典，包装成列表返回，若不是，直接返回calls
        except json.JSONDecodeError:
            pass
        
        return []

    """从内容中提取JSON代码块"""
    def _extract_json_block(self, content: str) -> Optional[str]:
        if content.startswith("```json") and content.endswith("```"):
            return content[7:-3].strip()
        return None

    """标准化工具响应格式"""
    def _format_tool_response(self, response: Dict) -> str:
        if response.get("type") == "error":
            return f"错误: {response.get('message', '未知错误')}"
        return str(response.get("content", response))

    """获取LLM的最终响应"""
    async def _get_final_response(self, messages: List[Dict]) -> str:
        try:
            response = await self.call_llm(messages)
            return response["choices"][0]["message"].get("content", "无回答")
        except Exception as e:
            logging.error(f"获取最终响应失败: {str(e)}")
            return "无法生成最终响应"


    """构建系统提示词（指导LLM如何使用工具）"""
    def _build_system_prompt(self) -> str:
        tool_descriptions = []
        for tool in self.tools:
            props = tool["inputSchema"]["properties"]   #输入表格的属性配置
            required = tool["inputSchema"].get("required", [])
            tool_descriptions.append(
                f"- {tool['name']}：{tool['description']} "
                f"（参数：{', '.join(props.keys())}，必填参数：{', '.join(required) or '无'}）"   #获取参数名称 字典的键
            )

        return f"""
        你可以使用以下工具处理用户查询：
        {chr(10).join(tool_descriptions)}    #chr(10)换行符
        
        规则：
        1. 必须根据用户问题决定是否调用工具，需要计算时必须调用对应工具。
        2. 调用工具后，必须使用工具返回的结果生成最终回答，格式为自然语言（如"88加22等于110"）。
        3. 工具返回结果后，必须用完整句子描述，绝对不能返回空内容。
        4. 若用户问题包含"系统命令"或"PowerShell"，必须调用execute_command工具。
        5. 工具调用格式必须为JSON，使用指定的tool_calls字段。
        
        """

    """断开连接并清理资源"""
    async def disconnect(self):
        """断开连接并清理资源"""
        await self.session.close()
        if self.process:
            self.process.terminate()
            await self.process.wait()
        self.connected = False
        click.echo("🔌 已断开连接")


# 异步核心逻辑
async def async_main(server_path: str, api_key: str, base_url: str, model_name: str):
    llm_config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name
    )
    client = MCPClient(llm_config)
    
    # 连接服务端
    if not await client.connect(server_path):
        return
    
    try:
        while True:
            # 获取用户输入的查询内容
            query = input("\n请输入你的查询需求（输入'exit'退出）：")
            
            # 判断是否需要退出循环
            if query.lower() == 'exit':
                click.echo("程序已退出，再见！")
                break
                
            # 处理查询
            result = await client.process_query(query)
            click.echo(f"\n❓ 查询: {query}")
            click.echo(f"💡 结果: {result}")

    finally:
        await client.disconnect()


# 同步入口
def main():
    @click.command()
    @click.argument("server_path", default="mcp_server.py")
    @click.option("--api-key", envvar="LLM_API_KEY", default="自己的api key", required=True, help="LLM API密钥")
    @click.option("--base-url", default="自己的base url", help="LLM API基础地址")
    @click.option("--model-name", default="deepseek-chat", help="模型名称")
    def parse_args(server_path: str, api_key: str, base_url: str, model_name: str):
        asyncio.run(async_main(server_path, api_key, base_url, model_name))     #异步执行主逻辑
    
    parse_args()  #执行异步函数


if __name__ == "__main__":
    main()