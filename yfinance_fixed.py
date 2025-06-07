#!/usr/bin/env python3
"""
YFinance MCP Server - Fixed Version

An MCP server that provides access to Yahoo Finance data through yfinance.download()
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import yfinance as yf
import pandas as pd
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
server = Server("yfinance-server")

@server.list_tools()
async def list_tools():
    """List available tools for the yfinance server."""
    return [
        {
            "name": "download_stock_data",
            "description": "Download historical stock data from Yahoo Finance using yfinance.download()",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "string",
                        "description": "Stock ticker symbol(s) to download. Single ticker as string or multiple tickers separated by spaces"
                    },
                    "period": {
                        "type": "string",
                        "description": "Period to download data for",
                        "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
                    },
                    "interval": {
                        "type": "string", 
                        "description": "Data interval",
                        "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end": {
                        "type": "string", 
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "actions": {
                        "type": "boolean",
                        "description": "Include dividend and stock split data"
                    },
                    "auto_adjust": {
                        "type": "boolean",
                        "description": "Automatically adjust OHLC data"
                    },
                    "prepost": {
                        "type": "boolean",
                        "description": "Include pre and post market data"
                    },
                    "repair": {
                        "type": "boolean",
                        "description": "Attempt to repair currency unit mixups"
                    },
                    "keepna": {
                        "type": "boolean",
                        "description": "Keep NaN rows"
                    },
                    "rounding": {
                        "type": "boolean",
                        "description": "Round values to 2 decimal places"
                    }
                },
                "required": ["tickers"]
            }
        }
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls for the yfinance server."""
    if name != "download_stock_data":
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )
            ],
            isError=True
        )
    
    try:
        # Extract arguments
        args = arguments or {}
        
        # Prepare yfinance.download arguments
        download_args = {}
        
        # Handle tickers (required)
        tickers = args.get("tickers")
        if not tickers:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="tickers parameter is required"
                    )
                ],
                isError=True
            )
        
        download_args["tickers"] = str(tickers)
        
        # Handle date parameters
        period = args.get("period", "1y")
        start = args.get("start")
        end = args.get("end")
        
        if start or end:
            # If start/end provided, use them instead of period
            if start:
                download_args["start"] = start
            if end:
                download_args["end"] = end
        else:
            # Use period
            download_args["period"] = period
        
        # Handle other parameters with defaults
        download_args["interval"] = args.get("interval", "1d")
        download_args["actions"] = args.get("actions", False)
        download_args["auto_adjust"] = args.get("auto_adjust", True)
        download_args["prepost"] = args.get("prepost", False)
        download_args["group_by"] = args.get("group_by", "column")
        download_args["repair"] = args.get("repair", False)
        download_args["keepna"] = args.get("keepna", False)
        download_args["rounding"] = args.get("rounding", False)
        download_args["timeout"] = args.get("timeout", 10)
        download_args["threads"] = args.get("threads", True)
        
        logger.info(f"Downloading data with args: {download_args}")
        
        # Call yfinance.download
        data = yf.download(**download_args)
        
        if data is None or data.empty:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"No data found for ticker(s): {tickers}"
                    )
                ]
            )
        
        # Convert DataFrame to JSON-serializable format
        result = {
            "tickers": tickers,
            "period": period if not (start or end) else f"{start or 'N/A'} to {end or 'N/A'}",
            "interval": download_args["interval"],
            "shape": list(data.shape),
            "columns": list(data.columns) if hasattr(data.columns, '__iter__') else [],
            "index_name": data.index.name or "Date",
            "data": {}
        }
        
        # Handle MultiIndex columns (multiple tickers)
        if hasattr(data.columns, 'nlevels') and data.columns.nlevels > 1:
            # MultiIndex DataFrame
            for col in data.columns:
                col_key = f"{col[0]}_{col[1]}" if len(col) == 2 else str(col)
                result["data"][col_key] = data[col].to_dict()
        else:
            # Single ticker or simple columns
            for col in data.columns:
                result["data"][str(col)] = data[col].to_dict()
        
        # Add index (dates) to the result
        result["dates"] = [str(date) for date in data.index]
        
        # Create summary statistics
        numeric_cols = data.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            result["summary"] = {
                "start_date": str(data.index[0]) if len(data) > 0 else None,
                "end_date": str(data.index[-1]) if len(data) > 0 else None,
                "total_records": len(data),
                "numeric_columns": len(numeric_cols)
            }
            
            # Add basic stats for first few numeric columns
            if len(numeric_cols) > 0:
                first_col = numeric_cols[0]
                result["summary"]["sample_stats"] = {
                    "column": str(first_col),
                    "min": float(data[first_col].min()),
                    "max": float(data[first_col].max()),
                    "mean": float(data[first_col].mean()),
                    "last_value": float(data[first_col].iloc[-1]) if not data[first_col].iloc[-1] != data[first_col].iloc[-1] else None  # Check for NaN
                }
        
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )
            ]
        )
        
    except Exception as e:
        logger.error(f"Error in download_stock_data: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text", 
                    text=f"Error downloading stock data: {str(e)}"
                )
            ],
            isError=True
        )

async def main():
    """Main entry point for the server."""
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="yfinance-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())