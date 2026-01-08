# Central Limit Order Book (CLOB) - Implementation Plan

## Project Overview
A Python-based educational central limit order book with basic matching functionality. Focus on clarity and understanding core concepts.

## Core Concepts to Implement
- **Price-Time Priority**: Orders matched by best price first, then by arrival time
- **Order Types**: Limit orders (specify price) and Market orders (execute immediately at best available)
- **Two-sided book**: Bids (buy orders) and Asks (sell orders)

## Project Structure

```
clob/
├── __init__.py
├── order.py          # Order dataclass
├── orderbook.py      # OrderBook with bid/ask management
├── matching_engine.py # Matching logic
├── trade.py          # Trade record dataclass
└── main.py           # Demo/CLI interface

tests/
├── __init__.py
├── test_order.py
├── test_orderbook.py
└── test_matching.py
```

## Implementation Steps

### Step 1: Data Models (`order.py`, `trade.py`)

**Order dataclass:**
- `order_id`: Unique identifier
- `side`: BUY or SELL (use Enum)
- `price`: Decimal (use `Decimal` for precision)
- `quantity`: int
- `timestamp`: datetime
- `order_type`: LIMIT or MARKET (use Enum)

**Trade dataclass:**
- `trade_id`: Unique identifier
- `buy_order_id`, `sell_order_id`: Matched order IDs
- `price`: Execution price
- `quantity`: Executed quantity
- `timestamp`: Execution time

### Step 2: Order Book (`orderbook.py`)

**Data structures:**
- Bids: Max-heap by price (highest bid first), sorted by time within price level
- Asks: Min-heap by price (lowest ask first), sorted by time within price level
- Use `sortedcontainers.SortedDict` for efficient price level management

**Methods:**
- `add_order(order)` - Add order to appropriate side
- `remove_order(order_id)` - Cancel an order
- `get_best_bid()` / `get_best_ask()` - Top of book
- `get_book_depth(levels)` - Return L2 market data

### Step 3: Matching Engine (`matching_engine.py`)

**Core matching logic:**
```
For incoming BUY order:
  While order has remaining quantity AND best_ask <= order.price (or market order):
    Match against best ask
    Generate trade
    Update/remove matched orders
  If remaining quantity, add to book (limit orders only)
```

**Methods:**
- `process_order(order) -> List[Trade]` - Main entry point
- `match_limit_order(order) -> List[Trade]`
- `match_market_order(order) -> List[Trade]`

### Step 4: Demo Interface (`main.py`)

Simple CLI to demonstrate:
- Submit orders
- View order book state
- See trade executions
- Cancel orders

## Key Design Decisions

1. **Use `Decimal` for prices** - Avoid floating-point precision issues
2. **Immutable order IDs** - Use UUID for simplicity
3. **No persistence** - In-memory only for educational clarity
4. **Single-threaded** - Avoid concurrency complexity for learning
5. **Clear separation** - OrderBook manages state, MatchingEngine handles logic

## Dependencies

```
sortedcontainers  # Efficient sorted data structures
```

## Verification

1. **Unit tests** for each component:
   - Order creation and validation
   - OrderBook add/remove/query operations
   - Matching engine scenarios (full fill, partial fill, no match)

2. **Integration test scenarios:**
   - Place multiple limit orders, verify book state
   - Market order sweeping multiple price levels
   - Partial fills leaving residual orders

3. **Manual verification via CLI:**
   - Run `python -m clob.main`
   - Submit orders and observe matching behavior

## Example Test Scenario

```
1. Add SELL 100 @ $10.00
2. Add SELL 50 @ $10.50
3. Add BUY 120 @ $10.00
   -> Trade: 100 @ $10.00
   -> BUY order with 20 remaining added to book
4. Book state: Bids: 20 @ $10.00, Asks: 50 @ $10.50
```
