"""FastAPI web application for the CLOB."""

import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .matching_engine import MatchingEngine
from .order import Order, OrderType, Side
from .orderbook import OrderBook
from .sample_data import create_sample_book

# Initialize app
app = FastAPI(title="CLOB Trading Interface")

# Setup templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Global order book instance with thread-safe access
# Lock for replacing global state (reset endpoint)
_state_lock = threading.Lock()
order_book: OrderBook
engine: MatchingEngine


@app.on_event("startup")
async def startup_event():
    """Initialize the order book with sample data on startup."""
    global order_book, engine
    order_book, engine = create_sample_book()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main trading interface."""
    bids, asks = order_book.get_book_depth(10)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "bids": bids,
            "asks": asks,
            "spread": order_book.get_spread(),
            "best_bid": order_book.get_best_bid_price(),
            "best_ask": order_book.get_best_ask_price(),
        },
    )


@app.get("/book", response_class=HTMLResponse)
async def get_book(request: Request):
    """Return just the order book partial (for HTMX updates)."""
    bids, asks = order_book.get_book_depth(10)
    return templates.TemplateResponse(
        "partials/orderbook.html",
        {
            "request": request,
            "bids": bids,
            "asks": asks,
            "spread": order_book.get_spread(),
            "best_bid": order_book.get_best_bid_price(),
            "best_ask": order_book.get_best_ask_price(),
        },
    )


@app.post("/order", response_class=HTMLResponse)
async def submit_order(
    request: Request,
    side: str = Form(...),
    quantity: int = Form(...),
    price: Optional[str] = Form(None),
    order_type: str = Form("limit"),
):
    """Submit a new order."""
    trades = []
    error = None

    try:
        order_side = Side.BUY if side == "buy" else Side.SELL

        if order_type == "market":
            order = Order(
                side=order_side,
                quantity=quantity,
                order_type=OrderType.MARKET,
            )
        else:
            if not price:
                raise ValueError("Price required for limit orders")
            order = Order(
                side=order_side,
                quantity=quantity,
                price=Decimal(price),
                order_type=OrderType.LIMIT,
            )

        trades = engine.process_order(order)

    except (ValueError, InvalidOperation) as e:
        error = str(e)

    bids, asks = order_book.get_book_depth(10)

    return templates.TemplateResponse(
        "partials/trading_result.html",
        {
            "request": request,
            "trades": trades,
            "error": error,
            "bids": bids,
            "asks": asks,
            "spread": order_book.get_spread(),
            "best_bid": order_book.get_best_bid_price(),
            "best_ask": order_book.get_best_ask_price(),
        },
    )


@app.post("/reset", response_class=HTMLResponse)
async def reset_book(request: Request):
    """Reset the order book to initial sample data (thread-safe)."""
    global order_book, engine

    with _state_lock:
        new_book, new_engine = create_sample_book()
        order_book = new_book
        engine = new_engine

    # Read operations are safe after assignment
    bids, asks = order_book.get_book_depth(10)
    return templates.TemplateResponse(
        "partials/orderbook.html",
        {
            "request": request,
            "bids": bids,
            "asks": asks,
            "spread": order_book.get_spread(),
            "best_bid": order_book.get_best_bid_price(),
            "best_ask": order_book.get_best_ask_price(),
        },
    )


def run():
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
