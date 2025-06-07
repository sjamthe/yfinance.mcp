#!/usr/bin/env python3
"""
Test client for MCP HTTP server using FastMCP client
"""

import asyncio
from fastmcp import Client

async def test_mcp_server():
    print("Testing MCP HTTP Server...")
    
    # Connect to SSE server
    async with Client("http://localhost:8000/sse") as client:
        
        # Test 1: List tools
        print("\n1. Testing tools/list")
        try:
            tools = await client.list_tools()
            print(f"Available tools: {len(tools)} found")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
        except Exception as e:
            print(f"Error listing tools: {e}")
        
        # Test 2: Call download_stock_data tool
        print("\n2. Testing tools/call with AAPL")
        try:
            result = await client.call_tool("download_stock_data", {"tickers": "AAPL"})
            print(f"Tool call successful!")
            print(f"Result preview (first 500 chars): {result[0].text[:500]}...")
        except Exception as e:
            print(f"Error calling tool: {e}")
        
        # Test 3: Call with custom parameters
        print("\n3. Testing tools/call with custom parameters")
        try:
            result = await client.call_tool("download_stock_data", {
                "tickers": "MSFT",
                "period": "1mo", 
                "interval": "1d"
            })
            print(f"Custom call successful!")
            print(f"Result preview (first 500 chars): {result[0].text[:500]}...")
        except Exception as e:
            print(f"Error with custom call: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())