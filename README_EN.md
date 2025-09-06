# MCP (Model Context Protocol) Calculator Tool

<div align="center">

**English** | [中文](README.md)

</div>

## Project Introduction

This is an intelligent calculator tool based on MCP (Model Context Protocol) that uses Large Language Models (LLM) to call local computational tools for mathematical operations. The project consists of client and server components, supporting asynchronous communication and tool invocation.

## Features

- 🤖 **Intelligent Chat**: Interact with LLM through natural language, automatically identifying computational needs
- 🔧 **Tool Invocation**: Supports four basic operations: addition, subtraction, multiplication, and division
- ⚡ **Async Processing**: High-performance asynchronous communication based on asyncio
- 🛡️ **Error Handling**: Comprehensive exception handling and timeout mechanisms
- 📝 **Debug Support**: Detailed debug logs and error tracking
- 🔌 **Flexible Configuration**: Supports various LLM API configurations

## Project Structure

```
mcp/
├── mcp_client.py    # MCP client, responsible for LLM communication and tool invocation
├── mcp_server.py    # MCP server, provides computational tool services
├── README.md        # Chinese documentation
└── README_EN.md     # English documentation
```

## Installation

```bash
pip install click aiohttp pydantic
```

## Usage

### 1. Start Server

```bash
python mcp_server.py
```

### 2. Start Client

```bash
python mcp_client.py --api-key "your_api_key" --base-url "your_base_url" --model-name "your_model_name"
```

### Environment Variables

```bash
export LLM_API_KEY="your_api_key"
export LLM_BASE_URL="your_base_url"
```

## Configuration

### Client Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--api-key` | LLM API Key | Required |
| `--base-url` | LLM API Base URL | Required |
| `--model-name` | Model Name | `deepseek-chat` |
| `server_path` | Server Script Path | `mcp_server.py` |

### Server Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--timeout` | Tool Call Timeout (seconds) | `30` |

## Supported Tools

- **addition**: Calculate the sum of two numbers
- **subtraction**: Calculate the difference of two numbers
- **multiplication**: Calculate the product of two numbers
- **division**: Calculate the quotient of two numbers

## Examples

```
Please enter your query (type 'exit' to quit): What is 88 plus 22?
❓ Query: What is 88 plus 22?
💡 Result: 88 plus 22 equals 110
```

## Technical Architecture

1. **Client (mcp_client.py)**:
   - Manages LLM connections and configurations
   - Parses user queries and generates tool calls
   - Processes tool responses and generates final answers
   - Asynchronous communication management

2. **Server (mcp_server.py)**:
   - Provides computational tool services
   - Handles tool invocation requests
   - Returns calculation results
   - Error handling and timeout management

## Development Notes

- The project uses Python 3.7+ and asyncio for asynchronous programming
- Supports JSON format request/response communication
- Uses Pydantic for data validation
- Supports debug mode and detailed log output

## License

MIT License

## Contributing

Welcome to submit Issues and Pull Requests to improve this project!
