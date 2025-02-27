from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from .models import Order, Transaction, OrderBook, PriceHistory, Notification


def attempt_to_match_order(new_order):
    """
    Enhanced matching engine:
    1. If new_order is a buy, look for active sell orders
       with the same product, price <= new_order.price
    2. If new_order is a sell, look for active buy orders
       with price >= new_order.price, same product
    3. Match with best price first (lowest for sells, highest for buys)
    4. Allow partial fills
    5. Continue matching until order is filled or no matches remain
    6. Update order status and create transactions for matches
    """
    if new_order.status != "active" or new_order.remaining_quantity == 0:
        return False  # Only match if new_order is active and has remaining quantity

    # Initialize variables
    matched = False
    remaining_quantity = new_order.remaining_quantity

    # Opposite order_type
    opposite_type = "sell" if new_order.order_type == "buy" else "buy"

    # Construct a query for potential matches
    qs = Order.objects.filter(
        product=new_order.product,
        order_type=opposite_type,
        status__in=["active", "partially_filled"],
        remaining_quantity__gt=0,
    )

    # Price condition:
    if new_order.order_type == "buy":
        # Looking for sells with price <= new_order.price
        qs = qs.filter(price__lte=new_order.price)
        # We'll pick the "best" price (lowest) => order_by('price', 'created_at')
        qs = qs.order_by("price", "created_at")
    else:
        # new_order is sell => look for buys with price >= sell price
        qs = qs.filter(price__gte=new_order.price)
        # We'll pick the "best" price (highest) => order_by('-price', 'created_at')
        qs = qs.order_by("-price", "created_at")

    # Continue matching until the order is filled or no matches remain
    for match in qs:
        if remaining_quantity <= 0:
            break  # Order is fully filled

        with transaction.atomic():
            # Determine the executed price (use match's price for simplicity)
            executed_price = match.price

            # Determine quantity to execute (minimum of remaining quantities)
            execute_quantity = min(remaining_quantity, match.remaining_quantity)

            # Create a transaction for new_order
            transaction1 = Transaction.objects.create(
                order=new_order,
                counter_order=match,
                executed_price=executed_price,
                quantity=execute_quantity,
            )

            # Create a transaction for the matched order
            transaction2 = Transaction.objects.create(
                order=match,
                counter_order=new_order,
                executed_price=executed_price,
                quantity=execute_quantity,
            )

            # Update the match order
            match.update_after_transaction(execute_quantity)

            # Update remaining quantity for current iteration
            remaining_quantity -= execute_quantity
            matched = True

            # Create notifications for both parties
            create_transaction_notifications(transaction1)

    # Update the new order status
    if matched:
        executed_quantity = new_order.remaining_quantity - remaining_quantity
        new_order.update_after_transaction(executed_quantity)
        update_price_history(new_order.product, executed_price, executed_quantity)
        update_order_book(new_order.product)

    return matched


def update_order_book(product):
    """
    Update the order book for a product
    """
    # Get all active buy orders
    buy_orders = Order.objects.filter(
        product=product,
        order_type="buy",
        status__in=["active", "partially_filled"],
        remaining_quantity__gt=0,
    ).order_by("-price")

    # Get all active sell orders
    sell_orders = Order.objects.filter(
        product=product,
        order_type="sell",
        status__in=["active", "partially_filled"],
        remaining_quantity__gt=0,
    ).order_by("price")

    # Aggregate bid levels
    bid_levels = {}
    total_bid_quantity = 0
    for order in buy_orders:
        price_str = str(order.price)
        if price_str in bid_levels:
            bid_levels[price_str] += order.remaining_quantity
        else:
            bid_levels[price_str] = order.remaining_quantity
        total_bid_quantity += order.remaining_quantity

    # Aggregate ask levels
    ask_levels = {}
    total_ask_quantity = 0
    for order in sell_orders:
        price_str = str(order.price)
        if price_str in ask_levels:
            ask_levels[price_str] += order.remaining_quantity
        else:
            ask_levels[price_str] = order.remaining_quantity
        total_ask_quantity += order.remaining_quantity

    # Get best bid/ask
    best_bid = buy_orders.first().price if buy_orders.exists() else None
    best_ask = sell_orders.first().price if sell_orders.exists() else None

    # Create or update order book
    OrderBook.objects.create(
        product=product,
        best_bid=best_bid,
        best_ask=best_ask,
        total_bid_quantity=total_bid_quantity,
        total_ask_quantity=total_ask_quantity,
        bid_levels=bid_levels,
        ask_levels=ask_levels,
    )

    # Update cache for quick access
    cache_key = f"order_book_{product.id}"
    cache.set(cache_key, {
        'best_bid': best_bid,
        'best_ask': best_ask,
        'bid_levels': bid_levels,
        'ask_levels': ask_levels,
    }, 60)  # Cache for 60 seconds

    return best_bid, best_ask


def update_price_history(product, executed_price, quantity):
    """
    Update the price history when a trade occurs
    """
    # Get the current date (for daily bars)
    today = timezone.now().date()

    # Try to get the current day's price history
    try:
        price_history = PriceHistory.objects.filter(
            product=product,
            timestamp__date=today
        ).latest('timestamp')

        # Update the high, low, close prices
        price_history.high_price = max(price_history.high_price, executed_price)
        price_history.low_price = min(price_history.low_price, executed_price)
        price_history.close_price = executed_price
        price_history.volume += quantity
        price_history.save()

    except PriceHistory.DoesNotExist:
        # Create a new price history record
        PriceHistory.objects.create(
            product=product,
            open_price=executed_price,
            high_price=executed_price,
            low_price=executed_price,
            close_price=executed_price,
            volume=quantity
        )


def create_transaction_notifications(transaction):
    """
    Create notifications for users involved in a transaction
    """
    # Notify the order owner
    Notification.objects.create(
        user=transaction.order.user,
        notification_type='order_executed',
        message=f"Your {transaction.order.order_type} order for {transaction.quantity} units of {transaction.order.product.name} was executed at {transaction.executed_price}",
        related_order=transaction.order
    )

    # Notify the counter-order owner if it exists
    if transaction.counter_order:
        Notification.objects.create(
            user=transaction.counter_order.user,
            notification_type='order_executed',
            message=f"Your {transaction.counter_order.order_type} order for {transaction.quantity} units of {transaction.counter_order.product.name} was executed at {transaction.executed_price}",
            related_order=transaction.counter_order
        )


def check_expired_orders():
    """
    Check for expired orders and mark them as expired
    """
    now = timezone.now()

    # Get active orders that have passed their expiration date
    expired_orders = Order.objects.filter(
        status__in=['active', 'partially_filled', 'pending'],
        expires_at__lte=now
    )

    for order in expired_orders:
        with transaction.atomic():
            old_status = order.status
            order.status = 'expired'
            order.save()

            # Create notification
            Notification.objects.create(
                user=order.user,
                notification_type='order_expired',
                message=f"Your {order.order_type} order for {order.product.name} has expired",
                related_order=order
            )

    return expired_orders.count()


def cancel_all_user_orders(user, reason=None):
    """
    Cancel all active orders for a user
    """
    active_orders = Order.objects.filter(
        user=user,
        status__in=['active', 'partially_filled', 'pending']
    )

    cancelled_count = 0
    for order in active_orders:
        if order.cancel(reason):
            cancelled_count += 1

            # Create notification
            Notification.objects.create(
                user=order.user,
                notification_type='order_cancelled',
                message=f"Your {order.order_type} order for {order.product.name} was cancelled: {reason or 'No reason provided'}",
                related_order=order
            )

    return cancelled_count
