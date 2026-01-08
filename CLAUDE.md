# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Educational Central Limit Order Book (CLOB) implementation in Python with a web frontend. Demonstrates price-time priority matching for limit and market orders.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run a single test file
pytest tests/test_matching.py -v

# Run CLI demo
python -m simple_clob.main

# Run sample data demo
python -m simple_clob.sample_data

# Start web server
uvicorn simple_clob.web:app --host 127.0.0.1 --port 8000

# Start web server with auto-reload (development)
uvicorn simple_clob.web:app --reload
```

## Architecture

### Core Components (simple_clob package)

**Data Flow:** `Order` → `MatchingEngine.process_order()` → `Trade[]`

- **Order** (`order.py`): Dataclass with Side (BUY/SELL), OrderType (LIMIT/MARKET), price (Decimal), quantity. Has `remaining_quantity` that decrements on fills.

- **OrderBook** (`orderbook.py`): Maintains bid/ask sides using `SortedDict`. Bids use negated price keys for descending order. Each price level holds a deque of orders (FIFO within level).

- **MatchingEngine** (`matching_engine.py`): Processes incoming orders against the book. Limit orders rest if not fully filled; market orders are discarded if unfilled.

- **Trade** (`trade.py`): Immutable record of executed match with buy/sell order IDs, price, and quantity.

### Web Frontend

- **FastAPI app** (`web.py`): Exposes `/order` POST endpoint and `/book` GET for HTMX updates
- **Templates**: Jinja2 templates in `templates/`, HTMX for partial page updates without JS
- **Global state**: Single `OrderBook` + `MatchingEngine` instance initialized with sample data on startup

### Key Design Decisions

- Uses `Decimal` for prices (avoid floating-point issues)
- Price-time priority: best price first, then FIFO within price level
- Trade executes at resting order's price (price improvement for aggressor)
