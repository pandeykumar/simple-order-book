"""Tests for Order and Trade dataclasses."""

import pytest
from decimal import Decimal

from simple_clob.order import Order, Side, OrderType
from simple_clob.trade import Trade


class TestOrder:
    def test_create_limit_order(self):
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10.50"))
        assert order.side == Side.BUY
        assert order.quantity == 100
        assert order.remaining_quantity == 100
        assert order.price == Decimal("10.50")
        assert order.order_type == OrderType.LIMIT
        assert not order.is_filled

    def test_create_market_order(self):
        order = Order(side=Side.SELL, quantity=50, order_type=OrderType.MARKET)
        assert order.side == Side.SELL
        assert order.quantity == 50
        assert order.price is None
        assert order.order_type == OrderType.MARKET

    def test_limit_order_requires_price(self):
        with pytest.raises(ValueError, match="Limit orders must have a price"):
            Order(side=Side.BUY, quantity=100)

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Order(side=Side.BUY, quantity=0, price=Decimal("10"))

    def test_price_must_be_positive(self):
        with pytest.raises(ValueError, match="Price must be positive"):
            Order(side=Side.BUY, quantity=100, price=Decimal("-10"))

    def test_fill_order(self):
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        order.fill(40)
        assert order.remaining_quantity == 60
        assert not order.is_filled

        order.fill(60)
        assert order.remaining_quantity == 0
        assert order.is_filled

    def test_fill_exceeds_remaining(self):
        order = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        with pytest.raises(ValueError, match="Cannot fill"):
            order.fill(150)


class TestTrade:
    def test_create_trade(self):
        order1 = Order(side=Side.BUY, quantity=100, price=Decimal("10"))
        order2 = Order(side=Side.SELL, quantity=100, price=Decimal("10"))

        trade = Trade(
            buy_order_id=order1.order_id,
            sell_order_id=order2.order_id,
            price=Decimal("10"),
            quantity=100,
        )

        assert trade.buy_order_id == order1.order_id
        assert trade.sell_order_id == order2.order_id
        assert trade.price == Decimal("10")
        assert trade.quantity == 100
