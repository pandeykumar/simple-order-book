# Simple CLOB (Central Limit Order Book)

An educational implementation of a Central Limit Order Book in Python. Demonstrates price-time priority matching for limit and market orders, with a web frontend for interactive order submission.

## Features

- **Price-Time Priority Matching**: Best price first, then FIFO within price level
- **Order Types**: Limit orders and market orders
- **Decimal Precision**: Uses Python `Decimal` for accurate price handling
- **Web Interface**: FastAPI backend with HTMX-powered frontend
- **CLI Demo**: Command-line demonstration of matching scenarios

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

Start the web server:

```bash
uvicorn simple_clob.web:app --host 127.0.0.1 --port 8000
```

For development with auto-reload:

```bash
uvicorn simple_clob.web:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

### CLI Demo

Run the interactive CLI demo:

```bash
python -m simple_clob.main
```

Or run with sample data:

```bash
python -m simple_clob.sample_data
```

## Architecture

### Core Components

```
Order → MatchingEngine.process_order() → Trade[]
```

| Component | File | Description |
|-----------|------|-------------|
| **Order** | `order.py` | Dataclass with Side (BUY/SELL), OrderType (LIMIT/MARKET), price, quantity |
| **OrderBook** | `orderbook.py` | Maintains bid/ask sides using `SortedDict` with FIFO queues per price level |
| **MatchingEngine** | `matching_engine.py` | Processes incoming orders against the book |
| **Trade** | `trade.py` | Immutable record of executed match |

### Key Design Decisions

- **Decimal prices**: Avoids floating-point precision issues
- **Price-time priority**: Best price matched first, then earliest order at that price
- **Price improvement**: Trades execute at the resting order's price (aggressor may get a better price)
- **Market order behavior**: Unfilled market orders are discarded (no resting)

## Testing

Run all tests:

```bash
pytest tests/ -v
```

Run a specific test file:

```bash
pytest tests/test_matching.py -v
```

## Project Structure

```
simple_clob/
├── __init__.py
├── order.py           # Order and Side/OrderType enums
├── trade.py           # Trade dataclass
├── orderbook.py       # Order book with bid/ask management
├── matching_engine.py # Core matching logic
├── main.py            # CLI demo
├── sample_data.py     # Sample data generator
└── web.py             # FastAPI web application

tests/
├── test_order.py      # Order creation and validation tests
├── test_orderbook.py  # Order book operations tests
└── test_matching.py   # Matching engine tests

templates/             # Jinja2 templates for web frontend
```

## License

Educational use.
