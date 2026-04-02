"""
Safe Database Helpers - Never crash live site
v2.0.0 - Defensive database operations
"""

import frappe
from functools import wraps


def safe_db_call(default_return=None, log_errors=True):
    """Decorator to safely wrap database calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    frappe.log_error(f"Safe DB Error in {func.__name__}: {str(e)}")
                return default_return
        return wrapper
    return decorator


@safe_db_call(default_return=0)
def db_count(doctype):
    """Safely count records in a doctype."""
    return frappe.db.count(doctype)


@safe_db_call(default_return=[])
def safe_get_all(doctype, fields=None, filters=None, limit=500, order_by="modified desc"):
    """
    Safely get records from a doctype.
    Never crashes - returns empty list on error.
    """
    return frappe.get_all(
        doctype, 
        fields=fields or ["name"],
        filters=filters or {},
        limit=limit,
        ignore_permissions=True,
        order_by=order_by
    )


@safe_db_call(default_return=None)
def safe_get_all_with_error(doctype, fields=None, filters=None, limit=500, order_by="modified desc"):
    """
    Get records and return None on error (to distinguish from empty result).
    """
    return frappe.get_all(
        doctype,
        fields=fields or ["name"],
        filters=filters or {},
        limit=limit,
        ignore_permissions=True,
        order_by=order_by
    )


@safe_db_call(default_return=None)
def safe_get_doc(doctype, doc_name):
    """
    Safely get full document with child tables.
    Returns dict or None on error.
    """
    doc = frappe.get_doc(doctype, doc_name)
    data = doc.as_dict()
    
    # Include child table data
    for f in doc.meta.get_table_fields():
        if hasattr(doc, f.fieldname):
            data[f.fieldname] = [i.as_dict() for i in getattr(doc, f.fieldname)]
    
    return data


@safe_db_call(default_return=[])
def safe_sql(query, values=None, as_dict=True):
    """
    Safely execute SQL query.
    Returns empty list on error.
    """
    return frappe.db.sql(query, values or (), as_dict=as_dict)


@safe_db_call(default_return=False)
def safe_exists(doctype, name):
    """Check if document exists."""
    return frappe.db.exists(doctype, name)


@safe_db_call(default_return=None)
def safe_get_value(doctype, name, fieldname):
    """Safely get a single field value."""
    return frappe.db.get_value(doctype, name, fieldname)


def safe_get_single(doctype):
    """Safely get single doctype settings."""
    try:
        return frappe.get_doc(doctype)
    except:
        return None


class SafeDBTransaction:
    """Context manager for safe database transactions."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            frappe.db.rollback()
            return True  # Suppress exception
        else:
            frappe.db.commit()
            return False
