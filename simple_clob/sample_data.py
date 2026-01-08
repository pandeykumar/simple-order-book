"""Sample data generator for testing the CLOB."""

from decimal import Decimal

from .matching_engine import MatchingEngine
from .order import Order, OrderType, Side
from .orderbook import OrderBook


def create_sample_book() -> tuple[OrderBook, MatchingEngine]:
    """
    Create an order book with sample data.

    Returns:
        Tuple of (OrderBook, MatchingEngine) with pre-populated orders
    """
    book = OrderBook()
    engine = MatchingEngine(book)

    # Sell orders (asks) - various price levels
    sell_orders = [
        (100, "100.50"),  # Best ask
        (150, "100.50"),
        (200, "101.00"),
        (75, "101.25"),
        (300, "101.50"),
        (50, "102.00"),
    ]

    # Buy orders (bids) - various price levels
    buy_orders = [
        (120, "100.00"),  # Best bid
        (80, "100.00"),
        (250, "99.75"),
        (100, "99.50"),
        (175, "99.25"),
        (400, "99.00"),
    ]

    for qty, price in sell_orders:
        order = Order(side=Side.SELL, quantity=qty, price=Decimal(price))
        engine.process_order(order)

    for qty, price in buy_orders:
        order = Order(side=Side.BUY, quantity=qty, price=Decimal(price))
        engine.process_order(order)

    return book, engine


def print_full_book(book: OrderBook) -> None:
    """Print detailed order book state."""
    bids, asks = book.get_book_depth(10)

    print("\n" + "=" * 50)
    print("ORDER BOOK - FULL DEPTH")
    print("=" * 50)

    print("\nASKS (Sell Orders):")
    print(f"{'Price':>12} | {'Quantity':>10} | {'Cumulative':>10}")
    print("-" * 38)
    cumulative = 0
    for price, qty in reversed(asks):
        cumulative += qty
        print(f"{price:>12} | {qty:>10} | {cumulative:>10}")

    print("\n" + "-" * 50)
    spread = book.get_spread()
    if spread:
        mid = (book.get_best_bid_price() + book.get_best_ask_price()) / 2
        print(f"  Spread: {spread}  |  Mid: {mid}")
    print("-" * 50 + "\n")

    print("BIDS (Buy Orders):")
    print(f"{'Price':>12} | {'Quantity':>10} | {'Cumulative':>10}")
    print("-" * 38)
    cumulative = 0
    for price, qty in bids:
        cumulative += qty
        print(f"{price:>12} | {qty:>10} | {cumulative:>10}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    book, engine = create_sample_book()
    print_full_book(book)

    print("\nSample trades:")
    print("-" * 30)

    # Execute a market buy that sweeps multiple levels
    print("\n> Market BUY 300 units:")
    order = Order(side=Side.BUY, quantity=300, order_type=OrderType.MARKET)
    trades = engine.process_order(order)
    for t in trades:
        print(f"  Filled {t.quantity} @ {t.price}")

    print("\nBook after market buy:")
    print_full_book(book)
