import asyncio
import json
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp import types as mcp_types
from google.adk.tools.function_tool import FunctionTool
from mcp_server.tools.create_lead import create_lead_tool
from mcp_server.tools.check_duplicate import check_duplicate_tool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

app = Server("leadsurge-mcp-server")

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        adk_to_mcp_tool_type(create_lead_tool),
        adk_to_mcp_tool_type(check_duplicate_tool),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    if name == "create_lead":
        result = await create_lead_tool.run_async(arguments, tool_context=None)
    elif name == "check_duplicate":
        result = await check_duplicate_tool.run_async(arguments, tool_context=None)
    else:
        return [mcp_types.TextContent(type="text", text="Tool not found.")]

    return [mcp_types.TextContent(type="text", text=json.dumps(result))]

async def run_server():
    async with mcp.server.stdio.stdio_server() as (reader, writer):
        await app.run(
            reader,
            writer,
            InitializationOptions(
                server_name="leadsurge-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(run_server())
