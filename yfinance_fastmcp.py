#!/usr/bin/env python3
"""
YFinance FastMCP Server - Using the newer FastMCP approach
"""

import json
import pandas as pd
import yfinance as yf
from fastmcp import FastMCP

# Create FastMCP server
mcp = FastMCP("YFinance Server")

@mcp.tool()
def download_stock_data(
    tickers: str,
    period: str = "1y",
    interval: str = "1d",
    start: str = None,
    end: str = None,
    actions: bool = False,
    auto_adjust: bool = True,
    prepost: bool = False,
    repair: bool = False,
    keepna: bool = False,
    rounding: bool = False
) -> str:
    """
    Download historical stock data from Yahoo Finance.
    
    Args:
        tickers: Stock ticker symbol(s) (e.g., 'AAPL' or 'AAPL MSFT')
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        start: Start date (YYYY-MM-DD format)
        end: End date (YYYY-MM-DD format)
        actions: Include dividend and stock split data
        auto_adjust: Automatically adjust OHLC data
        prepost: Include pre and post market data
        repair: Attempt to repair currency unit mixups
        keepna: Keep NaN rows
        rounding: Round values to 2 decimal places
    
    Returns:
        JSON string with stock data
    """
    try:
        # Prepare download arguments
        download_args = {
            "tickers": tickers,
            "interval": interval,
            "actions": actions,
            "auto_adjust": auto_adjust,
            "prepost": prepost,
            "group_by": "column",
            "repair": repair,
            "keepna": keepna,
            "rounding": rounding,
            "timeout": 10,
            "threads": True
        }
        
        # Handle date parameters
        if start or end:
            if start:
                download_args["start"] = start
            if end:
                download_args["end"] = end
        else:
            download_args["period"] = period
        
        # Download data
        data = yf.download(**download_args)
        
        if data is None or data.empty:
            return json.dumps({"error": f"No data found for ticker(s): {tickers}"})
        
        # Convert to simple format
        result = {
            "tickers": tickers,
            "period": period if not (start or end) else f"{start or 'N/A'} to {end or 'N/A'}",
            "interval": interval,
            "shape": list(data.shape),
            "columns": [str(col) for col in data.columns],
            "data": []
        }
        
        # Convert to records
        for date, row in data.iterrows():
            record = {"date": str(date)}
            for col in data.columns:
                val = row[col]
                record[str(col)] = float(val) if pd.notna(val) else None
            result["data"].append(record)
        
        # Add summary
        if len(data) > 0:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                first_col = numeric_cols[0]
                result["summary"] = {
                    "start_date": str(data.index[0]),
                    "end_date": str(data.index[-1]),
                    "total_records": len(data),
                    "first_column_stats": {
                        "column": str(first_col),
                        "min": float(data[first_col].min()),
                        "max": float(data[first_col].max()),
                        "mean": float(data[first_col].mean()),
                        "last_value": float(data[first_col].iloc[-1]) if pd.notna(data[first_col].iloc[-1]) else None
                    }
                }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Error downloading stock data: {str(e)}"})

if __name__ == "__main__":
    mcp.run()
