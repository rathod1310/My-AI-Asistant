"""
Backward compatibility - api package re-export
"""
from my_ai_assistant.my_ai_assistant.api.ai_helper import test_connection, ask_ai, scan_bill_image

__all__ = ["test_connection", "ask_ai", "scan_bill_image"]
