"""
AI Helper module - Re-exports API endpoints for client access
"""

from my_ai_assistant.my_ai_assistant.api_endpoints import test_connection, ask_ai, scan_bill_image

__all__ = ["test_connection", "ask_ai", "scan_bill_image"]
