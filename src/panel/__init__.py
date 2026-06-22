"""SakaiBot local web control panel (additive, read-only, ban-safe).

This package adds a premium localhost web dashboard for SakaiBot. It is a NEW
consumer of the existing AI core and Telegram client — it READS from Telegram
and RETURNS AI values; it NEVER sends/edits/forwards/deletes Telegram messages
and never opens a second Telegram session.

Nothing in this package is imported by the live bot path unless the operator
runs ``sakaibot panel``.
"""
