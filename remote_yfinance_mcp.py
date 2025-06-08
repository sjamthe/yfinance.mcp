#!/usr/bin/env python3
"""
YFinance HTTP MCP Server - Remote server using FastMCP
Enhanced with better error handling, logging, and timeout management
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import yfinance as yf
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("YFinance Server")

# Rate limiting variables
last_request_time = 0
min_request_interval = 0.5  # Minimum 500ms between requests

def validate_parameters(tickers: str, period: str, interval: str, start: str, end: str) -> Dict[str, Any]:
    """Validate input parameters and return validation result"""
    errors = []
    warnings = []
    
    # Validate tickers
    if not tickers or not tickers.strip():
        errors.append("Tickers parameter is required and cannot be empty")
    else:
        ticker_list = tickers.split()
        if len(ticker_list) > 10:
            warnings.append(f"Requesting {len(ticker_list)} tickers may cause timeouts. Consider smaller batches.")
    
    # Validate period
    valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    if period and period not in valid_periods:
        errors.append(f"Invalid period '{period}'. Valid options: {', '.join(valid_periods)}")
    
    # Validate interval
    valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']
    if interval not in valid_intervals:
        errors.append(f"Invalid interval '{interval}'. Valid options: {', '.join(valid_intervals)}")
    
    # Validate date format if provided
    if start:
        try:
            datetime.strptime(start, '%Y-%m-%d')
        except ValueError:
            errors.append(f"Invalid start date format '{start}'. Use YYYY-MM-DD format.")
    
    if end:
        try:
            datetime.strptime(end, '%Y-%m-%d')
        except ValueError:
            errors.append(f"Invalid end date format '{end}'. Use YYYY-MM-DD format.")
    
    # Check for conflicting parameters
    if (start or end) and period != "1y":
        warnings.append("Both date range and period specified. Date range will take precedence.")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

def rate_limit():
    """Simple rate limiting to avoid overwhelming Yahoo Finance"""
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < min_request_interval:
        sleep_time = min_request_interval - time_since_last
        logger.info(f"Rate limiting: sleeping for {sleep_time:.2f}s")
        time.sleep(sleep_time)
    
    last_request_time = time.time()

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
        JSON string with stock data or detailed error information
    """
    request_start_time = time.time()
    logger.info(f"Processing request: tickers={tickers}, period={period}, interval={interval}")
    
    try:
        # Validate input parameters
        validation = validate_parameters(tickers, period, interval, start, end)
        if not validation["valid"]:
            error_response = {
                "success": False,
                "error_type": "validation_error",
                "errors": validation["errors"],
                "timestamp": datetime.now().isoformat(),
                "request_params": {
                    "tickers": tickers,
                    "period": period,
                    "interval": interval,
                    "start": start,
                    "end": end
                }
            }
            logger.error(f"Validation failed: {validation['errors']}")
            return json.dumps(error_response, indent=2)
        
        # Log warnings if any
        if validation["warnings"]:
            logger.warning(f"Parameter warnings: {validation['warnings']}")
        
        # Apply rate limiting
        rate_limit()
        
        # Prepare download arguments with enhanced timeout handling
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
            "timeout": 30,  # Increased timeout
            "threads": True,
            "progress": False  # Disable progress bar to avoid issues
        }
        
        # Handle date parameters
        if start or end:
            if start:
                download_args["start"] = start
            if end:
                download_args["end"] = end
        else:
            download_args["period"] = period
        
        logger.info(f"Calling yfinance.download with args: {download_args}")
        
        # Download data with timeout protection
        try:
            data = yf.download(**download_args)
        except Exception as download_error:
            logger.error(f"YFinance download error: {str(download_error)}")
            
            # Try with reduced timeout and single-threaded
            logger.info("Retrying with conservative settings...")
            download_args.update({
                "timeout": 15,
                "threads": False
            })
            data = yf.download(**download_args)
        
        # Check if data was retrieved
        if data is None or data.empty:
            error_response = {
                "success": False,
                "error_type": "no_data",
                "message": f"No data found for ticker(s): {tickers}",
                "possible_causes": [
                    "Invalid ticker symbol(s)",
                    "No trading data for the specified period",
                    "Market closed or data not yet available",
                    "Yahoo Finance API temporary issues"
                ],
                "suggestions": [
                    "Verify ticker symbols are correct",
                    "Try a different time period",
                    "Check if markets are open",
                    "Retry the request after a few moments"
                ],
                "timestamp": datetime.now().isoformat(),
                "request_params": {
                    "tickers": tickers,
                    "period": period,
                    "interval": interval,
                    "start": start,
                    "end": end
                }
            }
            logger.warning(f"No data returned for request: {tickers}")
            return json.dumps(error_response, indent=2)
        
        logger.info(f"Successfully retrieved data: shape={data.shape}")
        
        # Convert to simple format
        result = {
            "success": True,
            "tickers": tickers,
            "period": period if not (start or end) else f"{start or 'N/A'} to {end or 'N/A'}",
            "interval": interval,
            "shape": list(data.shape),
            "columns": [str(col) for col in data.columns],
            "data": [],
            "metadata": {
                "request_time": datetime.now().isoformat(),
                "processing_time_seconds": round(time.time() - request_start_time, 3),
                "data_source": "Yahoo Finance",
                "warnings": validation.get("warnings", [])
            }
        }
        
        # Convert to records with better error handling
        records_processed = 0
        for date, row in data.iterrows():
            try:
                record = {"date": str(date)}
                for col in data.columns:
                    val = row[col]
                    if pd.notna(val):
                        # Handle different numeric types
                        if pd.api.types.is_numeric_dtype(type(val)):
                            record[str(col)] = float(val)
                        else:
                            record[str(col)] = str(val)
                    else:
                        record[str(col)] = None
                result["data"].append(record)
                records_processed += 1
            except Exception as record_error:
                logger.warning(f"Error processing record at {date}: {str(record_error)}")
                continue
        
        logger.info(f"Processed {records_processed} records")
        
        # Add summary statistics
        if len(data) > 0:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                first_col = numeric_cols[0]
                try:
                    result["summary"] = {
                        "start_date": str(data.index[0]),
                        "end_date": str(data.index[-1]),
                        "total_records": len(data),
                        "records_processed": records_processed,
                        "first_column_stats": {
                            "column": str(first_col),
                            "min": float(data[first_col].min()) if pd.notna(data[first_col].min()) else None,
                            "max": float(data[first_col].max()) if pd.notna(data[first_col].max()) else None,
                            "mean": float(data[first_col].mean()) if pd.notna(data[first_col].mean()) else None,
                            "last_value": float(data[first_col].iloc[-1]) if pd.notna(data[first_col].iloc[-1]) else None
                        }
                    }
                except Exception as summary_error:
                    logger.warning(f"Error generating summary: {str(summary_error)}")
                    result["summary"] = {"error": "Could not generate summary statistics"}
        
        logger.info(f"Request completed successfully in {time.time() - request_start_time:.3f}s")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_response = {
            "success": False,
            "error_type": "unexpected_error",
            "error_message": str(e),
            "error_class": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(time.time() - request_start_time, 3),
            "request_params": {
                "tickers": tickers,
                "period": period,
                "interval": interval,
                "start": start,
                "end": end
            },
            "troubleshooting": {
                "common_solutions": [
                    "Check internet connectivity",
                    "Verify Yahoo Finance is accessible",
                    "Try reducing the number of tickers",
                    "Use a shorter time period",
                    "Retry after a few minutes"
                ],
                "contact_info": "Check yfinance library documentation for known issues"
            }
        }
        logger.error(f"Unexpected error in download_stock_data: {str(e)}", exc_info=True)
        return json.dumps(error_response, indent=2)

@mcp.tool()
def get_server_status() -> str:
    """
    Get server status and health information
    
    Returns:
        JSON string with server status
    """
    try:
        # Test basic yfinance connectivity
        test_ticker = "AAPL"
        test_data = yf.download(test_ticker, period="1d", interval="1d", timeout=10, progress=False)
        
        status = {
            "server": "healthy",
            "yfinance_connection": "ok" if not test_data.empty else "degraded",
            "last_test": datetime.now().isoformat(),
            "version": {
                "yfinance": yf.__version__ if hasattr(yf, '__version__') else "unknown",
                "pandas": pd.__version__
            }
        }
        
        return json.dumps(status, indent=2)
        
    except Exception as e:
        status = {
            "server": "degraded",
            "yfinance_connection": "error",
            "error": str(e),
            "last_test": datetime.now().isoformat()
        }
        return json.dumps(status, indent=2)

if __name__ == "__main__":
    logger.info("Starting YFinance MCP Server...")
    try:
        # Run as HTTP server with SSE transport
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise