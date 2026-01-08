"""Tests for OrderBook."""

import pytest
from decimal import Decimal

from simple_clob.order import Order, Side
from simple_clob.orderbook import OrderBook


class TestOrderBook:
    def test_add_order(self):
        book = OrderBook()
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        book.add_order(order)

        assert len(book) == 1
        assert book.get_order(order.order_id) is order

    def test_add_duplicate_order_raises(self):
        book = OrderBook()
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        book.add_order(order)

        with pytest.raises(ValueError, match="already exists"):
            book.add_order(order)

    def test_best_bid_ask(self):
        book = OrderBook()

        # Add bids
        bid1 = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        bid2 = Order(side=Side.BUY, quantity=100, price=Decimal("10.50"))
        book.add_order(bid1)
        book.add_order(bid2)

        # Add asks
        ask1 = Order(side=Side.SELL, quantity=100, price=Decimal("11"))
        ask2 = Order(side=Side.SELL, quantity=100, price=Decimal("11.50"))
        book.add_order(ask1)
        book.add_order(ask2)

        # Best bid is highest
        assert book.get_best_bid() is bid2
        assert book.get_best_bid_price() == Decimal("10.50")

        # Best ask is lowest
        assert book.get_best_ask() is ask1
        assert book.get_best_ask_price() == Decimal("11")

        # Spread
        assert book.get_spread() == Decimal("0.50")

    def test_remove_order(self):
        book = OrderBook()
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        book.add_order(order)

        removed = book.remove_order(order.order_id)
        assert removed is order
        assert len(book) == 0
        assert book.get_order(order.order_id) is None

    def test_remove_nonexistent_order(self):
        book = OrderBook()
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        removed = book.remove_order(order.order_id)
        assert removed is None

    def test_price_time_priority(self):
        book = OrderBook()

        # Add orders at same price - should be FIFO
        order1 = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        order2 = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        book.add_order(order1)
        book.add_order(order2)

        # First order should be best bid (arrived first)
        assert book.get_best_bid() is order1

    def test_book_depth(self):
        book = OrderBook()

        # Add multiple price levels
        book.add_order(Order(side=Side.BUY, quantity=100, price=Decimal("10")))
        book.add_order(Order(side=Side.BUY, quantity=50, price=Decimal("10")))
        book.add_order(Order(side=Side.BUY, quantity=200, price=Decimal("9.50")))

        book.add_order(Order(side=Side.SELL, quantity=75, price=Decimal("11")))
        book.add_order(Order(side=Side.SELL, quantity=150, price=Decimal("11.50")))

        bids, asks = book.get_book_depth(5)

        # Bids aggregated by price level
        assert bids[0] == (Decimal("10"), 150)  # 100 + 50
        assert bids[1] == (Decimal("9.50"), 200)

        # Asks aggregated by price level
        assert asks[0] == (Decimal("11"), 75)
        assert asks[1] == (Decimal("11.50"), 150)

    def test_iter_orders(self):
        book = OrderBook()

        bid1 = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        bid2 = Order(side=Side.BUY, quantity=100, price=Decimal("9.50"))
        ask1 = Order(side=Side.SELL, quantity=100, price=Decimal("11"))

        book.add_order(bid1)
        book.add_order(bid2)
        book.add_order(ask1)

        bids = list(book.iter_bids())
        asks = list(book.iter_asks())

        # Bids in price priority (highest first)
        assert bids[0] is bid1
        assert bids[1] is bid2

        assert asks[0] is ask1
