# YFinance MCP Server

This MCP server provides access to Yahoo Finance data through the `yfinance.download()` function.

## Requirements

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
python remote_yfinance_mcp.py
```

### Tool: `download_stock_data`

Downloads historical stock data from Yahoo Finance.

**Parameters:**
- `tickers` (required): Stock ticker symbol(s) - string or array
- `period` (optional): Time period - "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max" (default: "1y")
- `interval` (optional): Data interval - "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo" (default: "1d")
- `start` (optional): Start date (YYYY-MM-DD format, inclusive)
- `end` (optional): End date (YYYY-MM-DD format, exclusive)
- `actions` (optional): Include dividend/split data (default: false)
- `auto_adjust` (optional): Auto-adjust OHLC data (default: true)
- `prepost` (optional): Include pre/post market data (default: false)
- `group_by` (optional): Group by "ticker" or "column" (default: "column")
- `repair` (optional): Attempt to repair currency mixups (default: false)
- `keepna` (optional): Keep NaN rows (default: false)
- `rounding` (optional): Round to 2 decimal places (default: false)
- `timeout` (optional): Request timeout in seconds (default: 10)
- `threads` (optional): Threading for mass downloads (default: true)

**Examples:**

Single ticker for 1 year:
```json
{
  "tickers": "AAPL",
  "period": "1y",
  "interval": "1d"
}
```

Multiple tickers with date range:
```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT"],
  "start": "2023-01-01",
  "end": "2024-01-01",
  "interval": "1d"
}
```

Intraday data (last 60 days max):
```json
{
  "tickers": "TSLA",
  "period": "5d",
  "interval": "1h"
}
```

## Configuration for MCP Clients

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "yfinance": {
      "command": "python",
      "args": ["/path/to/yfinance_mcp_server.py"],
      "env": {}
    }
  }
}
```

## Features

- Full support for all yfinance.download() parameters
- Handles both single and multiple tickers
- Returns structured JSON data with:
  - Raw OHLC data
  - Summary statistics
  - Metadata (shape, columns, date range)
- Error handling and logging
- Type validation for all parameters

## Notes

- Intraday data (intervals < 1d) cannot extend beyond the last 60 days
- Use either `period` OR `start`/`end` parameters, not both
- For multiple tickers, data is returned with MultiIndex columns
- Large datasets are automatically handled with threading
