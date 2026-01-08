"""Order data model for the CLOB."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class Side(Enum):
    """Order side: buy or sell."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type: limit or market."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"


@dataclass
class Order:
    """
    Represents an order in the order book.

    Attributes:
        side: BUY or SELL
        quantity: Number of units to trade
        price: Limit price (required for LIMIT orders, None for MARKET)
        order_type: LIMIT or MARKET
        order_id: Unique identifier (auto-generated)
        timestamp: Order creation time (auto-generated)
        remaining_quantity: Quantity not yet filled (starts equal to quantity)
    """
    side: Side
    quantity: int
    price: Optional[Decimal] = None
    order_type: OrderType = OrderType.LIMIT
    order_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    remaining_quantity: int = field(init=False)

    def __post_init__(self):
        self.remaining_quantity = self.quantity

        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("Limit orders must have a price")

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")

    @property
    def is_filled(self) -> bool:
        """Check if the order is completely filled."""
        return self.remaining_quantity == 0

    def fill(self, quantity: int) -> None:
        """
        Fill part or all of the order.

        Args:
            quantity: Amount to fill

        Raises:
            ValueError: If fill quantity exceeds remaining quantity
        """
        if quantity > self.remaining_quantity:
            raise ValueError(
                f"Cannot fill {quantity}, only {self.remaining_quantity} remaining"
            )
        self.remaining_quantity -= quantity

    def __repr__(self) -> str:
        price_str = f"@ {self.price}" if self.price else "@ MARKET"
        return (
            f"Order({self.side.value} {self.remaining_quantity}/{self.quantity} "
            f"{price_str}, id={str(self.order_id)[:8]})"
        )
