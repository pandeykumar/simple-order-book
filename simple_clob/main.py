"""CLI demo interface for the CLOB."""

from decimal import Decimal, InvalidOperation

from .matching_engine import MatchingEngine
from .order import Order, OrderType, Side
from .orderbook import OrderBook


def print_book(order_book: OrderBook) -> None:
    """Print the current state of the order book."""
    bids, asks = order_book.get_book_depth(5)

    print("\n" + "=" * 40)
    print("ORDER BOOK")
    print("=" * 40)

    # Print asks in reverse (highest to lowest)
    print("ASKS (Sell Orders):")
    if asks:
        for price, qty in reversed(asks):
            print(f"  {qty:>8} @ {price}")
    else:
        print("  (empty)")

    print("-" * 40)

    # Print bids (highest to lowest)
    print("BIDS (Buy Orders):")
    if bids:
        for price, qty in bids:
            print(f"  {qty:>8} @ {price}")
    else:
        print("  (empty)")

    spread = order_book.get_spread()
    if spread is not None:
        print(f"\nSpread: {spread}")
    print("=" * 40 + "\n")


def print_trades(trades: list) -> None:
    """Print executed trades."""
    if trades:
        print("\nTRADES EXECUTED:")
        for trade in trades:
            print(f"  {trade.quantity} @ {trade.price}")
    else:
        print("\n(No trades executed)")


def print_help() -> None:
    """Print help message."""
    print("""
CLOB Demo - Commands:
  buy <qty> <price>   - Place a limit buy order
  sell <qty> <price>  - Place a limit sell order
  mbuy <qty>          - Place a market buy order
  msell <qty>         - Place a market sell order
  book                - Show order book
  help                - Show this help
  quit                - Exit

Examples:
  buy 100 10.50       - Buy 100 units at $10.50
  sell 50 10.75       - Sell 50 units at $10.75
  mbuy 25             - Market buy 25 units
""")


def run_demo() -> None:
    """Run the interactive demo."""
    order_book = OrderBook()
    engine = MatchingEngine(order_book)

    print("\nCentral Limit Order Book Demo")
    print("Type 'help' for commands\n")

    while True:
        try:
            user_input = input("> ").strip().lower()

            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0]

            if command == "quit":
                print("Goodbye!")
                break

            elif command == "help":
                print_help()

            elif command == "book":
                print_book(order_book)

            elif command == "buy" and len(parts) == 3:
                qty = int(parts[1])
                price = Decimal(parts[2])
                order = Order(side=Side.BUY, quantity=qty, price=price)
                trades = engine.process_order(order)
                print(f"Placed: {order}")
                print_trades(trades)
                print_book(order_book)

            elif command == "sell" and len(parts) == 3:
                qty = int(parts[1])
                price = Decimal(parts[2])
                order = Order(side=Side.SELL, quantity=qty, price=price)
                trades = engine.process_order(order)
                print(f"Placed: {order}")
                print_trades(trades)
                print_book(order_book)

            elif command == "mbuy" and len(parts) == 2:
                qty = int(parts[1])
                order = Order(side=Side.BUY, quantity=qty, order_type=OrderType.MARKET)
                trades = engine.process_order(order)
                print(f"Placed: {order}")
                print_trades(trades)
                print_book(order_book)

            elif command == "msell" and len(parts) == 2:
                qty = int(parts[1])
                order = Order(side=Side.SELL, quantity=qty, order_type=OrderType.MARKET)
                trades = engine.process_order(order)
                print(f"Placed: {order}")
                print_trades(trades)
                print_book(order_book)

            else:
                print("Invalid command. Type 'help' for usage.")

        except (ValueError, InvalidOperation) as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    run_demo()
