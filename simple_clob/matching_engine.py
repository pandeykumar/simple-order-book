"""Matching engine for the CLOB."""

from typing import List

from .order import Order, OrderType, Side
from .orderbook import OrderBook
from .trade import Trade


class MatchingEngine:
    """
    Matching engine that processes orders against the order book.

    Implements price-time priority matching:
    - Buy orders match against the lowest asks
    - Sell orders match against the highest bids
    - Within a price level, older orders are matched first (FIFO)
    """

    def __init__(self, order_book: OrderBook):
        """
        Initialize the matching engine.

        Args:
            order_book: The order book to match against
        """
        self.order_book = order_book

    def process_order(self, order: Order) -> List[Trade]:
        """
        Process an incoming order.

        For limit orders: match against the book, then add remainder to book.
        For market orders: match against the book, discard remainder.

        Args:
            order: The order to process

        Returns:
            List of trades generated
        """
        if order.order_type == OrderType.MARKET:
            return self._match_market_order(order)
        else:
            return self._match_limit_order(order)

    def _match_limit_order(self, order: Order) -> List[Trade]:
        """
        Match a limit order against the book.

        Args:
            order: The limit order to match

        Returns:
            List of trades generated
        """
        trades = self._match_order(order)

        # Add remaining quantity to the book
        if not order.is_filled:
            self.order_book.add_order(order)

        return trades

    def _match_market_order(self, order: Order) -> List[Trade]:
        """
        Match a market order against the book.

        Market orders execute immediately at best available prices.
        Any unfilled quantity is discarded (no resting market orders).

        Args:
            order: The market order to match

        Returns:
            List of trades generated
        """
        return self._match_order(order)

    def _match_order(self, order: Order) -> List[Trade]:
        """
        Core matching logic.

        Args:
            order: The order to match

        Returns:
            List of trades generated
        """
        trades: List[Trade] = []

        while not order.is_filled:
            # Get the best opposing order
            if order.side == Side.BUY:
                best_opposing = self.order_book.get_best_ask()
            else:
                best_opposing = self.order_book.get_best_bid()

            # No more liquidity
            if best_opposing is None:
                break

            # Check if prices cross (for limit orders)
            if order.order_type == OrderType.LIMIT:
                if order.side == Side.BUY:
                    # Buy order: must be >= ask price to match
                    if order.price < best_opposing.price:
                        break
                else:
                    # Sell order: must be <= bid price to match
                    if order.price > best_opposing.price:
                        break

            # Execute the trade
            trade = self._execute_match(order, best_opposing)
            trades.append(trade)

        return trades

    def _execute_match(self, incoming: Order, resting: Order) -> Trade:
        """
        Execute a match between two orders.

        Args:
            incoming: The incoming (aggressor) order
            resting: The resting (passive) order in the book

        Returns:
            The resulting trade
        """
        # Trade quantity is the minimum of both orders' remaining quantities
        trade_qty = min(incoming.remaining_quantity, resting.remaining_quantity)

        # Trade price is the resting order's price (price improvement for aggressor)
        trade_price = resting.price

        # Determine buy and sell order IDs
        if incoming.side == Side.BUY:
            buy_order_id = incoming.order_id
            sell_order_id = resting.order_id
        else:
            buy_order_id = resting.order_id
            sell_order_id = incoming.order_id

        # Create the trade
        trade = Trade(
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
            price=trade_price,
            quantity=trade_qty,
        )

        # Update order quantities
        incoming.fill(trade_qty)
        resting.fill(trade_qty)

        # Remove filled resting order from book
        if resting.is_filled:
            self.order_book._remove_filled_order(resting)

        return trade
