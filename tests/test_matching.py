"""Tests for MatchingEngine."""

import pytest
from decimal import Decimal

from simple_clob.order import Order, OrderType, Side
from simple_clob.orderbook import OrderBook
from simple_clob.matching_engine import MatchingEngine


class TestMatchingEngine:
    def setup_method(self):
        self.book = OrderBook()
        self.engine = MatchingEngine(self.book)

    def test_no_match_adds_to_book(self):
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        trades = self.engine.process_order(order)

        assert len(trades) == 0
        assert len(self.book) == 1
        assert self.book.get_best_bid() is order

    def test_full_match(self):
        # Add a sell order
        sell = Order(side=Side.SELL, quantity=100, price=Decimal("10"))
        self.engine.process_order(sell)

        # Buy order should fully match
        buy = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 1
        assert trades[0].quantity == 100
        assert trades[0].price == Decimal("10")
        assert len(self.book) == 0  # Both orders fully filled

    def test_partial_match_incoming(self):
        # Add a small sell order
        sell = Order(side=Side.SELL, quantity=50, price=Decimal("10"))
        self.engine.process_order(sell)

        # Buy order partially matches, remainder rests
        buy = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 1
        assert trades[0].quantity == 50
        assert len(self.book) == 1
        assert self.book.get_best_bid().remaining_quantity == 50

    def test_partial_match_resting(self):
        # Add a large sell order
        sell = Order(side=Side.SELL, quantity=100, price=Decimal("10"))
        self.engine.process_order(sell)

        # Buy order fully fills, sell order partially remains
        buy = Order(side=Side.BUY, quantity=50, price=Decimal("10"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 1
        assert trades[0].quantity == 50
        assert len(self.book) == 1
        assert self.book.get_best_ask().remaining_quantity == 50

    def test_no_match_price_too_low(self):
        # Add a sell order at $11
        sell = Order(side=Side.SELL, quantity=100, price=Decimal("11"))
        self.engine.process_order(sell)

        # Buy order at $10 should not match
        buy = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 0
        assert len(self.book) == 2

    def test_price_improvement(self):
        # Add a sell order at $10
        sell = Order(side=Side.SELL, quantity=100, price=Decimal("10"))
        self.engine.process_order(sell)

        # Buy order at $11 should get price improvement at $10
        buy = Order(side=Side.BUY, quantity=100, price=Decimal("11"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 1
        assert trades[0].price == Decimal("10")  # Executed at resting order price

    def test_multiple_price_levels(self):
        # Add multiple sell orders
        self.engine.process_order(Order(side=Side.SELL, quantity=100, price=Decimal("10")))
        self.engine.process_order(Order(side=Side.SELL, quantity=50, price=Decimal("10.50")))

        # Large buy order sweeps multiple levels
        buy = Order(side=Side.BUY, quantity=120, price=Decimal("10.50"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 2
        assert trades[0].quantity == 100
        assert trades[0].price == Decimal("10")
        assert trades[1].quantity == 20
        assert trades[1].price == Decimal("10.50")

        # Remaining ask at 10.50
        assert self.book.get_best_ask_price() == Decimal("10.50")
        assert self.book.get_best_ask().remaining_quantity == 30

    def test_market_order_buy(self):
        # Add sell orders
        self.engine.process_order(Order(side=Side.SELL, quantity=100, price=Decimal("10")))
        self.engine.process_order(Order(side=Side.SELL, quantity=100, price=Decimal("11")))

        # Market buy sweeps available liquidity
        buy = Order(side=Side.BUY, quantity=150, order_type=OrderType.MARKET)
        trades = self.engine.process_order(buy)

        assert len(trades) == 2
        assert trades[0].quantity == 100
        assert trades[0].price == Decimal("10")
        assert trades[1].quantity == 50
        assert trades[1].price == Decimal("11")

        # Remaining ask at 11
        assert self.book.get_best_ask().remaining_quantity == 50

    def test_market_order_no_liquidity(self):
        # Market buy with no liquidity
        buy = Order(side=Side.BUY, quantity=100, order_type=OrderType.MARKET)
        trades = self.engine.process_order(buy)

        assert len(trades) == 0
        assert len(self.book) == 0  # Market orders don't rest

    def test_time_priority(self):
        # Add two sell orders at same price
        sell1 = Order(side=Side.SELL, quantity=50, price=Decimal("10"))
        sell2 = Order(side=Side.SELL, quantity=50, price=Decimal("10"))
        self.engine.process_order(sell1)
        self.engine.process_order(sell2)

        # Buy should match with first order
        buy = Order(side=Side.BUY, quantity=50, price=Decimal("10"))
        trades = self.engine.process_order(buy)

        assert len(trades) == 1
        assert trades[0].sell_order_id == sell1.order_id

    def test_sell_order_matching(self):
        # Add a buy order
        buy = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        self.engine.process_order(buy)

        # Sell order should match
        sell = Order(side=Side.SELL, quantity=100, price=Decimal("10"))
        trades = self.engine.process_order(sell)

        assert len(trades) == 1
        assert trades[0].quantity == 100
        assert len(self.book) == 0


class TestExampleScenario:
    """Test the example scenario from the plan."""

    def test_example_scenario(self):
        book = OrderBook()
        engine = MatchingEngine(book)

        # 1. Add SELL 100 @ $10.00
        sell1 = Order(side=Side.SELL, quantity=100, price=Decimal("10.00"))
        trades = engine.process_order(sell1)
        assert len(trades) == 0

        # 2. Add SELL 50 @ $10.50
        sell2 = Order(side=Side.SELL, quantity=50, price=Decimal("10.50"))
        trades = engine.process_order(sell2)
        assert len(trades) == 0

        # 3. Add BUY 120 @ $10.00
        buy = Order(side=Side.BUY, quantity=120, price=Decimal("10.00"))
        trades = engine.process_order(buy)

        # -> Trade: 100 @ $10.00
        assert len(trades) == 1
        assert trades[0].quantity == 100
        assert trades[0].price == Decimal("10.00")

        # -> BUY order with 20 remaining added to book
        # 4. Book state: Bids: 20 @ $10.00, Asks: 50 @ $10.50
        bids, asks = book.get_book_depth(5)

        assert len(bids) == 1
        assert bids[0] == (Decimal("10.00"), 20)

        assert len(asks) == 1
        assert asks[0] == (Decimal("10.50"), 50)
