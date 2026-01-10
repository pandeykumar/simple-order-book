"""Order book implementation with price-time priority."""

from collections import deque
from contextlib import contextmanager
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sortedcontainers import SortedDict

from .order import Order, Side
from .rwlock import RWLock


class OrderBook:
    """
    Central Limit Order Book with price-time priority.

    Bids (buy orders) are sorted by price descending (highest first).
    Asks (sell orders) are sorted by price ascending (lowest first).
    Within each price level, orders are sorted by time (FIFO).

    Thread-safe via read-write locking.
    """

    def __init__(self):
        # Bids: price -> deque of orders (negated keys for descending order)
        self._bids: SortedDict[Decimal, deque[Order]] = SortedDict()
        # Asks: price -> deque of orders (ascending order)
        self._asks: SortedDict[Decimal, deque[Order]] = SortedDict()
        # Order ID -> Order lookup for O(1) cancellation
        self._orders: Dict[UUID, Order] = {}
        # Read-write lock for thread safety
        self._rwlock = RWLock()

    @contextmanager
    def read_lock(self):
        """Acquire read lock for external use."""
        with self._rwlock.read():
            yield

    @contextmanager
    def write_lock(self):
        """Acquire write lock for external use."""
        with self._rwlock.write():
            yield

    def add_order(self, order: Order) -> None:
        """
        Add an order to the book (thread-safe).

        Args:
            order: The order to add
        """
        with self._rwlock.write():
            self._unlocked_add_order(order)

    def _unlocked_add_order(self, order: Order) -> None:
        """Add an order without acquiring lock (caller must hold write lock)."""
        if order.order_id in self._orders:
            raise ValueError(f"Order {order.order_id} already exists")

        book = self._bids if order.side == Side.BUY else self._asks
        price = order.price

        # For bids, negate the price to get descending order
        key = -price if order.side == Side.BUY else price

        if key not in book:
            book[key] = deque()

        book[key].append(order)
        self._orders[order.order_id] = order

    def remove_order(self, order_id: UUID) -> Optional[Order]:
        """
        Remove an order from the book (cancel) (thread-safe).

        Args:
            order_id: ID of the order to remove

        Returns:
            The removed order, or None if not found
        """
        with self._rwlock.write():
            return self._unlocked_remove_order(order_id)

    def _unlocked_remove_order(self, order_id: UUID) -> Optional[Order]:
        """Remove an order without acquiring lock (caller must hold write lock)."""
        order = self._orders.pop(order_id, None)
        if order is None:
            return None

        book = self._bids if order.side == Side.BUY else self._asks
        key = -order.price if order.side == Side.BUY else order.price

        if key in book:
            try:
                book[key].remove(order)
                if not book[key]:
                    del book[key]
            except ValueError:
                pass  # Order not in deque (shouldn't happen)

        return order

    def get_best_bid(self) -> Optional[Order]:
        """Get the highest bid order (thread-safe)."""
        with self._rwlock.read():
            return self._unlocked_get_best_bid()

    def _unlocked_get_best_bid(self) -> Optional[Order]:
        """Get best bid without acquiring lock (caller must hold lock)."""
        if not self._bids:
            return None
        return self._bids.peekitem(0)[1][0]

    def get_best_ask(self) -> Optional[Order]:
        """Get the lowest ask order (thread-safe)."""
        with self._rwlock.read():
            return self._unlocked_get_best_ask()

    def _unlocked_get_best_ask(self) -> Optional[Order]:
        """Get best ask without acquiring lock (caller must hold lock)."""
        if not self._asks:
            return None
        return self._asks.peekitem(0)[1][0]

    def get_best_bid_price(self) -> Optional[Decimal]:
        """Get the highest bid price (thread-safe)."""
        with self._rwlock.read():
            bid = self._unlocked_get_best_bid()
            return bid.price if bid else None

    def get_best_ask_price(self) -> Optional[Decimal]:
        """Get the lowest ask price (thread-safe)."""
        with self._rwlock.read():
            ask = self._unlocked_get_best_ask()
            return ask.price if ask else None

    def get_spread(self) -> Optional[Decimal]:
        """Get the bid-ask spread (thread-safe)."""
        with self._rwlock.read():
            bid = self._unlocked_get_best_bid()
            ask = self._unlocked_get_best_ask()
            if bid is None or ask is None:
                return None
            return ask.price - bid.price

    def get_order(self, order_id: UUID) -> Optional[Order]:
        """Look up an order by ID (thread-safe)."""
        with self._rwlock.read():
            return self._orders.get(order_id)

    def iter_bids(self) -> List[Order]:
        """Return a snapshot of all bids in price-time priority order (thread-safe)."""
        with self._rwlock.read():
            result = []
            for orders in self._bids.values():
                result.extend(orders)
            return result

    def iter_asks(self) -> List[Order]:
        """Return a snapshot of all asks in price-time priority order (thread-safe)."""
        with self._rwlock.read():
            result = []
            for orders in self._asks.values():
                result.extend(orders)
            return result

    def get_book_depth(self, levels: int = 5) -> Tuple[List[Tuple[Decimal, int]], List[Tuple[Decimal, int]]]:
        """
        Get aggregated book depth (thread-safe).

        Args:
            levels: Number of price levels to return

        Returns:
            Tuple of (bids, asks) where each is a list of (price, total_quantity)
        """
        with self._rwlock.read():
            return self._unlocked_get_book_depth(levels)

    def _unlocked_get_book_depth(self, levels: int = 5) -> Tuple[List[Tuple[Decimal, int]], List[Tuple[Decimal, int]]]:
        """Get book depth without acquiring lock (caller must hold lock)."""
        bids = []
        for i, (neg_price, orders) in enumerate(self._bids.items()):
            if i >= levels:
                break
            total_qty = sum(o.remaining_quantity for o in orders)
            bids.append((-neg_price, total_qty))

        asks = []
        for i, (price, orders) in enumerate(self._asks.items()):
            if i >= levels:
                break
            total_qty = sum(o.remaining_quantity for o in orders)
            asks.append((price, total_qty))

        return bids, asks

    def _remove_filled_order(self, order: Order) -> None:
        """Remove a completely filled order from the book (thread-safe)."""
        with self._rwlock.write():
            self._unlocked_remove_filled_order(order)

    def _unlocked_remove_filled_order(self, order: Order) -> None:
        """Remove filled order without acquiring lock (caller must hold write lock)."""
        if order.order_id in self._orders:
            del self._orders[order.order_id]

        book = self._bids if order.side == Side.BUY else self._asks
        key = -order.price if order.side == Side.BUY else order.price

        if key in book and book[key] and book[key][0] is order:
            book[key].popleft()
            if not book[key]:
                del book[key]

    def reset(self) -> None:
        """Clear all orders from the book (thread-safe)."""
        with self._rwlock.write():
            self._bids.clear()
            self._asks.clear()
            self._orders.clear()

    def __len__(self) -> int:
        """Return total number of orders in the book (thread-safe)."""
        with self._rwlock.read():
            return len(self._orders)

    def __repr__(self) -> str:
        with self._rwlock.read():
            bids, asks = self._unlocked_get_book_depth(3)
            bid_str = ", ".join(f"{qty}@{price}" for price, qty in bids) or "empty"
            ask_str = ", ".join(f"{qty}@{price}" for price, qty in asks) or "empty"
            return f"OrderBook(bids=[{bid_str}], asks=[{ask_str}])"
