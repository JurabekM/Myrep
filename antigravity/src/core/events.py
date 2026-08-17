"""Observer-pattern event bus for the Enterprise ERP platform.

Provides a lightweight, synchronous publish-subscribe system that enables
decoupled communication between ERP modules.  Components can emit events
(e.g. ``SALE_CREATED``) without knowing which other components are
listening, and subscribers can react without tight coupling to the emitter.

Usage::

    from src.core.events import event_bus, SALE_CREATED

    def on_sale(order_id: str, total: float, **kwargs):
        print(f'New sale #{order_id} for {total}')

    event_bus.subscribe(SALE_CREATED, on_sale)
    event_bus.emit(SALE_CREATED, order_id='SO-00042', total=150_000.0)

A module-level singleton :data:`event_bus` is provided for convenience.

Standard Event Names:
    This module defines string constants for all well-known events.
    Using constants instead of raw strings prevents typos and enables
    IDE auto-completion.
"""

import logging
from typing import Any, Callable, Dict, List


# ---------------------------------------------------------------------------
# Standard event name constants
# ---------------------------------------------------------------------------

# User lifecycle
USER_LOGIN: str = 'user.login'
"""Emitted when a user successfully logs in."""

USER_LOGOUT: str = 'user.logout'
"""Emitted when a user logs out."""

USER_CREATED: str = 'user.created'
"""Emitted when a new user account is created."""

USER_UPDATED: str = 'user.updated'
"""Emitted when user profile data is modified."""

USER_DELETED: str = 'user.deleted'
"""Emitted when a user account is deleted."""

# Sales
SALE_CREATED: str = 'sale.created'
"""Emitted when a new sale is recorded."""

SALE_UPDATED: str = 'sale.updated'
"""Emitted when a sale record is modified."""

SALE_CANCELLED: str = 'sale.cancelled'
"""Emitted when a sale is cancelled."""

# Inventory / stock
STOCK_UPDATED: str = 'stock.updated'
"""Emitted when inventory quantities change."""

STOCK_LOW: str = 'stock.low'
"""Emitted when a product falls below its reorder threshold."""

# Invoicing
INVOICE_CREATED: str = 'invoice.created'
"""Emitted when a new invoice is generated."""

INVOICE_PAID: str = 'invoice.paid'
"""Emitted when an invoice is fully paid."""

# Payments
PAYMENT_RECEIVED: str = 'payment.received'
"""Emitted when a payment is recorded."""

PAYMENT_REFUNDED: str = 'payment.refunded'
"""Emitted when a payment is refunded."""

# Orders
ORDER_CREATED: str = 'order.created'
"""Emitted when a new order is placed."""

ORDER_STATUS_CHANGED: str = 'order.status_changed'
"""Emitted when an order transitions to a new status."""

# HR / employees
EMPLOYEE_CREATED: str = 'employee.created'
"""Emitted when a new employee record is created."""

EMPLOYEE_UPDATED: str = 'employee.updated'
"""Emitted when an employee record is updated."""

# System operations
BACKUP_CREATED: str = 'backup.created'
"""Emitted after a database backup completes successfully."""

BACKUP_RESTORED: str = 'backup.restored'
"""Emitted after a backup is restored."""

SYSTEM_ERROR: str = 'system.error'
"""Emitted when an unrecoverable system error occurs."""

MODULE_LOADED: str = 'module.loaded'
"""Emitted when an ERP module is successfully loaded."""


# ---------------------------------------------------------------------------
# Events namespace class
# ---------------------------------------------------------------------------

class Events:
    """Namespace grouping all standard event constants.

    Provides an alternative import style::

        from src.core.events import Events
        event_bus.emit(Events.USER_LOGIN, user_id='...')
    """

    USER_LOGIN = USER_LOGIN
    USER_LOGOUT = USER_LOGOUT
    USER_CREATED = USER_CREATED
    USER_UPDATED = USER_UPDATED
    USER_DELETED = USER_DELETED
    SALE_CREATED = SALE_CREATED
    SALE_UPDATED = SALE_UPDATED
    SALE_CANCELLED = SALE_CANCELLED
    STOCK_UPDATED = STOCK_UPDATED
    STOCK_LOW = STOCK_LOW
    INVOICE_CREATED = INVOICE_CREATED
    INVOICE_PAID = INVOICE_PAID
    PAYMENT_RECEIVED = PAYMENT_RECEIVED
    PAYMENT_REFUNDED = PAYMENT_REFUNDED
    ORDER_CREATED = ORDER_CREATED
    ORDER_STATUS_CHANGED = ORDER_STATUS_CHANGED
    EMPLOYEE_CREATED = EMPLOYEE_CREATED
    EMPLOYEE_UPDATED = EMPLOYEE_UPDATED
    BACKUP_CREATED = BACKUP_CREATED
    BACKUP_RESTORED = BACKUP_RESTORED
    SYSTEM_ERROR = SYSTEM_ERROR
    MODULE_LOADED = MODULE_LOADED


# ---------------------------------------------------------------------------
# EventBus implementation
# ---------------------------------------------------------------------------

class EventBus:
    """Synchronous observer-pattern event bus.

    Manages subscriptions and dispatches events to registered callbacks.
    Exceptions raised by individual subscribers are caught and logged so
    that one faulty handler cannot break the entire event chain.

    Attributes:
        _subscribers: Mapping of event names to lists of callback functions.
    """

    def __init__(self) -> None:
        """Initialise the event bus with an empty subscriber registry."""
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}
        self._logger = logging.getLogger(__name__)

    def subscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        """Register *callback* to be invoked when *event_name* is emitted.

        Duplicate registrations of the same callback for the same event
        are silently ignored.

        Args:
            event_name: The event identifier string (use module constants).
            callback: A callable accepting ``**kwargs``.
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)
            self._logger.debug(
                'Subscribed %s to event "%s"',
                getattr(callback, '__name__', repr(callback)),
                event_name,
            )

    def unsubscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        """Remove *callback* from *event_name* subscribers.

        Silently does nothing if the callback was not subscribed.

        Args:
            event_name: The event identifier string.
            callback: The previously registered callable.
        """
        if event_name in self._subscribers:
            try:
                self._subscribers[event_name].remove(callback)
                self._logger.debug(
                    'Unsubscribed %s from event "%s"',
                    getattr(callback, '__name__', repr(callback)),
                    event_name,
                )
            except ValueError:
                pass

    def emit(self, event_name: str, **kwargs: Any) -> None:
        """Emit an event, invoking all registered callbacks.

        Each callback receives the keyword arguments passed to this method.
        Exceptions in individual callbacks are caught and logged; remaining
        callbacks are still executed.

        Args:
            event_name: The event identifier string.
            **kwargs: Arbitrary keyword arguments forwarded to each callback.
        """
        self._logger.debug('Emitting event: %s', event_name)
        for callback in self._subscribers.get(event_name, []):
            try:
                callback(**kwargs)
            except Exception:
                self._logger.exception(
                    'Error in event handler %s for event "%s"',
                    getattr(callback, '__name__', repr(callback)),
                    event_name,
                )

    def clear(self) -> None:
        """Remove all subscribers from all events.

        Typically called during application shutdown.
        """
        self._subscribers.clear()
        self._logger.debug('All event subscriptions cleared')

    @property
    def subscriber_count(self) -> int:
        """Return the total number of active subscriptions across all events.

        Returns:
            Sum of subscriber lists across every event name.
        """
        return sum(len(cbs) for cbs in self._subscribers.values())

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        event_count = len(self._subscribers)
        return (
            f'EventBus(events={event_count}, '
            f'subscribers={self.subscriber_count})'
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

event_bus: EventBus = EventBus()
"""Global event bus instance shared across the application.

Import this singleton rather than creating new :class:`EventBus` instances
to ensure all modules communicate through a single channel.
"""
