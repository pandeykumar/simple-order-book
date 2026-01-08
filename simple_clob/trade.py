"""Trade data model for the CLOB."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Trade:
    """
    Represents an executed trade between two orders.

    Attributes:
        buy_order_id: ID of the buy order
        sell_order_id: ID of the sell order
        price: Execution price
        quantity: Number of units traded
        trade_id: Unique identifier (auto-generated)
        timestamp: Execution time (auto-generated)
    """
    buy_order_id: UUID
    sell_order_id: UUID
    price: Decimal
    quantity: int
    trade_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)

    def __repr__(self) -> str:
        return (
            f"Trade({self.quantity} @ {self.price}, "
            f"buy={str(self.buy_order_id)[:8]}, "
            f"sell={str(self.sell_order_id)[:8]})"
        )
