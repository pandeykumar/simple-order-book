"""Concurrent stress tests for thread-safe order book."""

import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import List

import pytest

from simple_clob.order import Order, OrderType, Side
from simple_clob.orderbook import OrderBook
from simple_clob.matching_engine import MatchingEngine
from simple_clob.trade import Trade
from simple_clob.rwlock import RWLock


class TestConcurrentReads:
    """Test concurrent read operations."""

    def test_concurrent_get_book_depth(self):
        """Multiple threads can read book depth simultaneously."""
        book = OrderBook()
        engine = MatchingEngine(book)

        # Add some orders
        for i in range(10):
            engine.process_order(Order(
                side=Side.BUY, quantity=100, price=Decimal(f"{100 - i}")
            ))
            engine.process_order(Order(
                side=Side.SELL, quantity=100, price=Decimal(f"{101 + i}")
            ))

        results = []
        errors = []

        def read_depth():
            try:
                for _ in range(100):
                    bids, asks = book.get_book_depth(5)
                    results.append((len(bids), len(asks)))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_depth) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 1000  # 10 threads * 100 reads

    def test_concurrent_get_spread(self):
        """Multiple threads can read spread simultaneously."""
        book = OrderBook()
        book.add_order(Order(side=Side.BUY, quantity=100, price=Decimal("100")))
        book.add_order(Order(side=Side.SELL, quantity=100, price=Decimal("101")))

        results = []

        def read_spread():
            for _ in range(100):
                spread = book.get_spread()
                results.append(spread)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_spread) for _ in range(10)]
            for f in as_completed(futures):
                f.result()

        assert all(s == Decimal("1") for s in results)


class TestConcurrentWrites:
    """Test concurrent write operations."""

    def test_concurrent_order_submission(self):
        """Multiple threads submitting orders simultaneously."""
        book = OrderBook()
        engine = MatchingEngine(book)

        trades: List[Trade] = []
        trade_lock = threading.Lock()
        errors = []

        def submit_orders(side: Side, base_price: int):
            try:
                for i in range(50):
                    price = Decimal(f"{base_price + random.randint(-5, 5)}")
                    qty = random.randint(10, 100)
                    order = Order(side=side, quantity=qty, price=price)
                    result = engine.process_order(order)
                    with trade_lock:
                        trades.extend(result)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=submit_orders, args=(Side.BUY, 100)),
            threading.Thread(target=submit_orders, args=(Side.BUY, 100)),
            threading.Thread(target=submit_orders, args=(Side.SELL, 100)),
            threading.Thread(target=submit_orders, args=(Side.SELL, 100)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        # Verify book invariants
        assert len(book) >= 0

        # Verify no duplicate order IDs
        order_ids = set()
        for order in book.iter_bids() + book.iter_asks():
            assert order.order_id not in order_ids
            order_ids.add(order.order_id)

    def test_no_double_fill(self):
        """Ensure orders are not filled more than their quantity."""
        book = OrderBook()
        engine = MatchingEngine(book)

        # Add a single sell order
        sell = Order(side=Side.SELL, quantity=100, price=Decimal("100"))
        engine.process_order(sell)

        total_filled = []
        fill_lock = threading.Lock()

        def aggressive_buy():
            for _ in range(10):
                order = Order(side=Side.BUY, quantity=20, price=Decimal("100"))
                trades = engine.process_order(order)
                with fill_lock:
                    for t in trades:
                        total_filled.append(t.quantity)

        threads = [threading.Thread(target=aggressive_buy) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total filled should not exceed the sell order quantity
        assert sum(total_filled) <= 100
        assert sell.remaining_quantity >= 0


class TestConcurrentReadWrite:
    """Test concurrent read and write operations."""

    def test_read_while_writing(self):
        """Reads should see consistent state while writes occur."""
        book = OrderBook()
        engine = MatchingEngine(book)

        stop_flag = threading.Event()
        errors = []

        def writer():
            try:
                for i in range(100):
                    if stop_flag.is_set():
                        break
                    side = Side.BUY if i % 2 == 0 else Side.SELL
                    price = Decimal(f"{100 + (i % 10)}")
                    order = Order(side=side, quantity=10, price=price)
                    engine.process_order(order)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(200):
                    if stop_flag.is_set():
                        break
                    bids, asks = book.get_book_depth(10)
                    # Verify consistency: quantities should be positive
                    for price, qty in bids:
                        assert qty > 0, f"Invalid bid quantity: {qty}"
                    for price, qty in asks:
                        assert qty > 0, f"Invalid ask quantity: {qty}"
            except AssertionError as e:
                errors.append(e)
                stop_flag.set()
            except Exception as e:
                errors.append(e)

        writer_threads = [threading.Thread(target=writer) for _ in range(3)]
        reader_threads = [threading.Thread(target=reader) for _ in range(5)]

        all_threads = writer_threads + reader_threads
        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestStressLoad:
    """High-load stress tests."""

    def test_high_throughput(self):
        """Test system under high throughput."""
        book = OrderBook()
        engine = MatchingEngine(book)

        num_threads = 8
        orders_per_thread = 500

        trade_count = [0]
        count_lock = threading.Lock()
        errors = []

        def submit_random_orders():
            try:
                local_trades = 0
                for _ in range(orders_per_thread):
                    side = random.choice([Side.BUY, Side.SELL])
                    order_type = random.choice([OrderType.LIMIT, OrderType.MARKET])
                    qty = random.randint(1, 100)

                    if order_type == OrderType.MARKET:
                        order = Order(side=side, quantity=qty, order_type=OrderType.MARKET)
                    else:
                        price = Decimal(f"{random.randint(95, 105)}.{random.randint(0, 99):02d}")
                        order = Order(side=side, quantity=qty, price=price)

                    trades = engine.process_order(order)
                    local_trades += len(trades)

                with count_lock:
                    trade_count[0] += local_trades
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(submit_random_orders) for _ in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify book invariants
        bids, asks = book.get_book_depth(100)
        for price, qty in bids:
            assert qty > 0
            assert price > 0
        for price, qty in asks:
            assert qty > 0
            assert price > 0


class TestRWLockBasics:
    """Test RWLock behavior directly."""

    def test_multiple_readers(self):
        """Multiple readers can hold lock simultaneously."""
        rwlock = RWLock()
        reader_count = [0]
        max_readers = [0]
        count_lock = threading.Lock()

        def reader():
            with rwlock.read():
                with count_lock:
                    reader_count[0] += 1
                    max_readers[0] = max(max_readers[0], reader_count[0])

                import time
                time.sleep(0.01)  # Simulate work

                with count_lock:
                    reader_count[0] -= 1

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Multiple readers should have been active simultaneously
        assert max_readers[0] > 1

    def test_writer_exclusion(self):
        """Writer excludes all other access."""
        rwlock = RWLock()
        active_writers = [0]
        active_readers = [0]
        errors = []

        def writer():
            with rwlock.write():
                active_writers[0] += 1
                if active_writers[0] > 1 or active_readers[0] > 0:
                    errors.append("Multiple writers or readers during write")
                import time
                time.sleep(0.01)
                active_writers[0] -= 1

        def reader():
            with rwlock.read():
                active_readers[0] += 1
                if active_writers[0] > 0:
                    errors.append("Reader during write")
                import time
                time.sleep(0.005)
                active_readers[0] -= 1

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=reader))

        random.shuffle(threads)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
