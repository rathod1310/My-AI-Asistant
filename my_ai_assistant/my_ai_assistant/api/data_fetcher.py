"""
Global Keyword-Based Data Fetcher
v2.0.0 - Fetches live ERP data based on natural language queries
"""

import frappe
import re
from frappe.utils import today, get_first_day

from ..config.data_registry import REGISTRY, get_keywords_map, get_config, get_entity_doctypes
from ..utils.safe_db import safe_get_all, safe_get_doc, safe_sql, db_count


# ═══════════════════════════════════════════════════════════════════════════
# DOC ID PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

DOC_ID_PATTERNS = [
    # Sales Invoice - various formats: SINV-001, ACC-SINV-2026-00007, etc.
    (r"[\w-]*SINV-[\w-]+",  "Sales Invoice"),
    (r"[\w-]*SI-[\w-]+",     "Sales Invoice"),
    
    # Purchase Invoice - various formats: PINV-001, ACC-PINV-2026-00001, etc.
    (r"[\w-]*PINV-[\w-]+",  "Purchase Invoice"),
    (r"[\w-]*PI-[\w-]+",     "Purchase Invoice"),
    
    # Sales Order - various formats: SO-001, SAL-ORD-001, etc.
    (r"[\w-]*SO-[\w-]+",     "Sales Order"),
    (r"[\w-]*SAL-ORD-[\w-]+","Sales Order"),
    
    # Purchase Order - various formats: PO-001, PUR-ORD-2026-00003, etc.
    (r"[\w-]*PO-[\w-]+",     "Purchase Order"),
    (r"[\w-]*PUR-ORD-[\w-]+","Purchase Order"),
    (r"[\w-]*PUR-[\w-]+",    "Purchase Order"),
    
    # Quotation - various formats: QTN-001, QUOT-001, etc.
    (r"[\w-]*QUOT-[\w-]+",   "Quotation"),
    (r"[\w-]*QTN-[\w-]+",    "Quotation"),
    (r"[\w-]*QUOTE-[\w-]+",   "Quotation"),
    
    # Delivery Note
    (r"[\w-]*DN-[\w-]+",     "Delivery Note"),
    (r"[\w-]*DEL-[\w-]+",    "Delivery Note"),
    
    # Journal Entry
    (r"[\w-]*JV-[\w-]+",     "Journal Entry"),
    (r"[\w-]*JE-[\w-]+",     "Journal Entry"),
    (r"[\w-]*JOUR-[\w-]+",   "Journal Entry"),
    
    # Employee
    (r"[\w-]*HR-EMP-[\w-]+", "Employee"),
    (r"[\w-]*EMP-[\w-]+",    "Employee"),
    
    # Attendance
    (r"[\w-]*HR-ATT-[\w-]+","Attendance"),
    (r"[\w-]*ATT-[\w-]+",    "Attendance"),
    
    # Customer (if ID format is used)
    (r"[\w-]*CUST-[\w-]+",    "Customer"),
    
    # Supplier (if ID format is used)
    (r"[\w-]*SUP-[\w-]+",     "Supplier"),
    (r"[\w-]*SUPP-[\w-]+",    "Supplier"),
    (r"[\w-]*VEND-[\w-]+",    "Supplier"),
]

GSTIN_PATTERN = r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9]{1})\b"


# ═══════════════════════════════════════════════════════════════════════════
# ENTITY DETECTION
# ═══════════════════════════════════════════════════════════════════════════

ENTITY_DOCTYPES = {
    "Customer":  ("customer_name", "customer"),
    "Supplier":  ("supplier_name", "supplier"),
    "Item":      ("item_name", "item"),
    "Employee":  ("employee_name", "employee"),
}


def extract_entities(question):
    """
    Extract entity names mentioned in the question.
    Returns dict with entity keys and document IDs.
    """
    q_lower = question.lower()
    result = {}
    
    for doctype, (name_field, key) in ENTITY_DOCTYPES.items():
        try:
            rows = safe_get_all(
                doctype, 
                fields=["name", name_field],
                limit=2000
            )
            for r in rows:
                name_val = (r.get(name_field) or r.get("name") or "").strip()
                if name_val and len(name_val) > 1 and name_val.lower() in q_lower:
                    result[key] = r.get("name")
                    result[f"{key}_display"] = name_val
                    break
        except:
            pass
    
    return result


def detect_doc_id(question):
    """Detect specific document IDs in question."""
    # Check GSTIN
    gstin_match = re.search(GSTIN_PATTERN, question, re.IGNORECASE)
    if gstin_match:
        return "GSTIN", gstin_match.group(1).upper()
    
    # Check doc ID patterns
    for pattern, doctype in DOC_ID_PATTERNS:
        m = re.search(pattern, question, re.IGNORECASE)
        if m:
            return doctype, m.group(0)
    
    # SMART FALLBACK: Try to detect ANY potential doc ID and verify it exists
    # Pattern: look for sequences like XXX-YYYY-ZZZZ with numbers and dashes
    # Common in ERPNext: ABC-123, ABC-2024-00001, etc.
    generic_patterns = [
        r"\b([A-Z]{2,5}-\d{4}-\d{3,})\b",      # ABC-2024-00001
        r"\b([A-Z]{2,5}-[A-Z]{2,5}-\d{4}-\d{3,})\b",  # ACC-SINV-2024-00001
        r"\b([A-Z]{3,}-\d{3,})\b",             # ABC-001
        r"\b([A-Z]+-[A-Z]+-\d{4}-\d{3,})\b",  # PUR-ORD-2024-00001
    ]
    
    for pattern in generic_patterns:
        m = re.search(pattern, question, re.IGNORECASE)
        if m:
            potential_id = m.group(1)
            # Try to find which doctype this belongs to
            for dt in ["Sales Invoice", "Purchase Invoice", "Sales Order", 
                      "Purchase Order", "Quotation", "Delivery Note", 
                      "Journal Entry", "Payment Entry", "Customer", 
                      "Supplier", "Item", "Employee"]:
                if frappe.db.exists(dt, potential_id):
                    return dt, potential_id
    
    return None, None


# ═══════════════════════════════════════════════════════════════════════════
# RELATED DATA FETCHERS
# ═══════════════════════════════════════════════════════════════════════════

def fetch_entity_related(doctype, doc_id, data, prefix):
    """
    Fetch related documents for an entity.
    Uses REGISTRY "related" configuration.
    """
    cfg = get_config(doctype)
    for related_dt, rel_cfg in cfg.get("related", {}).items():
        try:
            filter_field = rel_cfg["filter_field"]
            extra_filters = rel_cfg.get("extra_filters", {})
            fields = rel_cfg.get("fields", ["name"])
            filters = {filter_field: doc_id, **extra_filters}
            
            rows = safe_get_all(related_dt, fields, filters, limit=1000)
            key = prefix + related_dt.lower().replace(" ", "_") + "s"
            data[key] = rows
            data[f"{key}_count"] = len(rows)
        except Exception as e:
            frappe.log_error(f"fetch_entity_related [{related_dt}]: {e}")


def fetch_item_sales_data(item_code, data):
    """Fetch sales data for an item."""
    try:
        rows = safe_sql("""
            SELECT si.name, si.customer_name, si.status, si.posting_date,
                   sii.qty, sii.rate, sii.amount
            FROM `tabSales Invoice` si
            JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
            WHERE sii.item_code = %s AND si.docstatus = 1
            ORDER BY si.posting_date DESC LIMIT 200
        """, item_code)
        
        data["entity_item_sales"] = rows
        data["entity_item_total_sold_qty"] = sum(float(r.get("qty") or 0) for r in rows)
        data["entity_item_total_revenue"] = sum(float(r.get("amount") or 0) for r in rows)
    except Exception as e:
        frappe.log_error(f"fetch_item_sales_data: {e}")


def fetch_item_purchase_data(item_code, data):
    """Fetch purchase data for an item."""
    try:
        rows = safe_sql("""
            SELECT pi.name, pi.supplier_name, pi.status, pi.posting_date,
                   pii.qty, pii.rate, pii.amount
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
            WHERE pii.item_code = %s AND pi.docstatus = 1
            ORDER BY pi.posting_date DESC LIMIT 200
        """, item_code)
        
        data["entity_item_purchases"] = rows
        data["entity_item_total_purchased_qty"] = sum(float(r.get("qty") or 0) for r in rows)
    except Exception as e:
        frappe.log_error(f"fetch_item_purchase_data: {e}")


def fetch_item_stock_data(item_code, data):
    """Fetch stock data for an item."""
    try:
        rows = safe_sql(
            "SELECT warehouse, actual_qty, valuation_rate FROM `tabBin` WHERE item_code = %s",
            item_code
        )
        data["entity_item_stock"] = rows
        data["entity_item_total_stock"] = sum(float(r.get("actual_qty") or 0) for r in rows)
    except:
        pass


def fetch_item_complete_data(item_code, data):
    """Fetch all data for an item (sales + purchases + stock)."""
    fetch_item_sales_data(item_code, data)
    fetch_item_purchase_data(item_code, data)
    fetch_item_stock_data(item_code, data)


# ═══════════════════════════════════════════════════════════════════════════
# COMPUTED DATA BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def get_overview_counts():
    """Get counts of all registered doctypes."""
    return {dt: db_count(dt) for dt in REGISTRY}


def get_sales_invoice_summary(data):
    """Build comprehensive Sales Invoice summary."""
    cfg = get_config("Sales Invoice")
    sinv = safe_get_all("Sales Invoice", cfg["fetch_fields"], limit=2000)
    
    submitted = [i for i in sinv if str(i.get("docstatus")) == "1"]
    today_str = today()
    month_start = str(get_first_day(today_str))
    year_start = f"{today_str[:4]}-01-01"
    
    month_sinv = [i for i in submitted if str(i.get("posting_date", "")) >= month_start]
    year_sinv = [i for i in submitted if str(i.get("posting_date", "")) >= year_start]
    
    data.update({
        "sales_invoices": sinv,
        "total_revenue": sum(float(i.get("grand_total") or 0) for i in submitted),
        "revenue_this_month": sum(float(i.get("grand_total") or 0) for i in month_sinv),
        "revenue_this_year": sum(float(i.get("grand_total") or 0) for i in year_sinv),
        "total_outstanding": sum(float(i.get("outstanding_amount") or 0) for i in submitted),
        "overdue_invoices": [i for i in sinv if i.get("status") == "Overdue"],
        "overdue_count": len([i for i in sinv if i.get("status") == "Overdue"]),
        "paid_count": len([i for i in sinv if i.get("status") == "Paid"]),
        "unpaid_count": len([i for i in sinv if i.get("status") == "Unpaid"]),
        "invoices_this_month": len(month_sinv),
        "invoices_this_year": len(year_sinv),
    })


def get_purchase_invoice_summary(data):
    """Build comprehensive Purchase Invoice summary."""
    cfg = get_config("Purchase Invoice")
    pinv = safe_get_all("Purchase Invoice", cfg["fetch_fields"], limit=2000)
    
    submitted = [i for i in pinv if str(i.get("docstatus")) == "1"]
    today_str = today()
    month_start = str(get_first_day(today_str))
    year_start = f"{today_str[:4]}-01-01"
    
    month_pinv = [i for i in submitted if str(i.get("posting_date", "")) >= month_start]
    year_pinv = [i for i in submitted if str(i.get("posting_date", "")) >= year_start]
    
    data.update({
        "purchase_invoices": pinv,
        "total_purchases": sum(float(i.get("grand_total") or 0) for i in submitted),
        "purchases_this_month": sum(float(i.get("grand_total") or 0) for i in month_pinv),
        "purchases_this_year": sum(float(i.get("grand_total") or 0) for i in year_pinv),
        "total_payable": sum(float(i.get("outstanding_amount") or 0) for i in submitted),
        "overdue_purchases": len([i for i in pinv if i.get("status") == "Overdue"]),
    })


def get_business_summary(data):
    """Build complete business summary."""
    overview = get_overview_counts()
    
    # Sales summary
    cfg_si = get_config("Sales Invoice")
    sinv_all = safe_get_all("Sales Invoice", ["grand_total","outstanding_amount","docstatus","status","posting_date"], limit=2000)
    sub_sinv = [i for i in sinv_all if str(i.get("docstatus")) == "1"]
    
    # Purchase summary
    pinv_all = safe_get_all("Purchase Invoice", ["grand_total","outstanding_amount","docstatus"], limit=2000)
    sub_pinv = [i for i in pinv_all if str(i.get("docstatus")) == "1"]
    
    month_start = str(get_first_day(today()))
    
    data["business_summary"] = {
        **{f"total_{dt.lower().replace(' ','_')}s": count for dt, count in overview.items()},
        "total_revenue": sum(float(i.get("grand_total") or 0) for i in sub_sinv),
        "revenue_this_month": sum(float(i.get("grand_total") or 0) for i in sub_sinv if str(i.get("posting_date","")) >= month_start),
        "total_outstanding": sum(float(i.get("outstanding_amount") or 0) for i in sub_sinv),
        "total_payable": sum(float(i.get("outstanding_amount") or 0) for i in sub_pinv),
        "overdue_count": len([i for i in sinv_all if i.get("status") == "Overdue"]),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FETCH FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def get_live_data(question):
    """
    Main entry point - fetch all relevant live data based on question.
    Returns dict with all relevant ERP data.
    """
    q = question.lower()
    data = {}
    today_str = today()
    
    # 1. Check for specific doc ID
    detected_dt, doc_id = detect_doc_id(question)
    if detected_dt == "GSTIN" and doc_id:
        # GSTIN handling - placeholder for now
        data["gstin_details"] = {"gstin": doc_id, "status": "Active"}
        return data
    
    if detected_dt and doc_id:
        if not any(w in q for w in ["create", "add", "new"]):
            # Fetch the main document
            data["specific_document"] = safe_get_doc(detected_dt, doc_id)
            
            # Fetch child tables for detailed queries
            if detected_dt == "Sales Invoice":
                items = safe_get_all("Sales Invoice Item", 
                    ["item_code", "item_name", "qty", "rate", "amount", "description"],
                    {"parent": doc_id},
                    limit=100
                )
                data["specific_document_items"] = items
                data["specific_document_item_count"] = len(items)
            
            elif detected_dt == "Purchase Invoice":
                items = safe_get_all("Purchase Invoice Item",
                    ["item_code", "item_name", "qty", "rate", "amount", "description"],
                    {"parent": doc_id},
                    limit=100
                )
                data["specific_document_items"] = items
                data["specific_document_item_count"] = len(items)
            
            elif detected_dt == "Sales Order":
                items = safe_get_all("Sales Order Item",
                    ["item_code", "item_name", "qty", "rate", "amount"],
                    {"parent": doc_id},
                    limit=100
                )
                data["specific_document_items"] = items
                data["specific_document_item_count"] = len(items)
            
            elif detected_dt == "Purchase Order":
                items = safe_get_all("Purchase Order Item",
                    ["item_code", "item_name", "qty", "rate", "amount"],
                    {"parent": doc_id},
                    limit=100
                )
                data["specific_document_items"] = items
                data["specific_document_item_count"] = len(items)
            
            elif detected_dt == "Quotation":
                items = safe_get_all("Quotation Item",
                    ["item_code", "item_name", "qty", "rate", "amount"],
                    {"parent": doc_id},
                    limit=100
                )
                data["specific_document_items"] = items
                data["specific_document_item_count"] = len(items)
            
            return data
    
    # 2. Always include overview
    data["overview"] = get_overview_counts()
    
    # 3. Extract and fetch entity data
    entities = extract_entities(question)
    
    # Customer entity
    if entities.get("customer"):
        cid = entities["customer"]
        data["entity_customer"] = safe_get_doc("Customer", cid)
        data["entity_customer_name"] = entities.get("customer_display", cid)
        fetch_entity_related("Customer", cid, data, "entity_customer_")
        
        # Computed fields for customer
        sinvs = data.get("entity_customer_sales_invoices", [])
        submitted = [i for i in sinvs if str(i.get("docstatus")) == "1"]
        data["entity_customer_total_billing"] = sum(float(i.get("grand_total") or 0) for i in submitted)
        data["entity_customer_outstanding"] = sum(float(i.get("outstanding_amount") or 0) for i in submitted)
        data["entity_customer_paid_count"] = len([i for i in sinvs if i.get("status") == "Paid"])
        data["entity_customer_overdue_count"] = len([i for i in sinvs if i.get("status") == "Overdue"])
    
    # Supplier entity
    if entities.get("supplier"):
        sid = entities["supplier"]
        data["entity_supplier"] = safe_get_doc("Supplier", sid)
        data["entity_supplier_name"] = entities.get("supplier_display", sid)
        fetch_entity_related("Supplier", sid, data, "entity_supplier_")
        
        pinvs = data.get("entity_supplier_purchase_invoices", [])
        submitted = [i for i in pinvs if str(i.get("docstatus")) == "1"]
        data["entity_supplier_total_billing"] = sum(float(i.get("grand_total") or 0) for i in submitted)
        data["entity_supplier_outstanding"] = sum(float(i.get("outstanding_amount") or 0) for i in submitted)
    
    # Item entity
    if entities.get("item"):
        iid = entities["item"]
        data["entity_item"] = safe_get_doc("Item", iid)
        data["entity_item_name"] = entities.get("item_display", iid)
        fetch_item_complete_data(iid, data)
    
    # Employee entity
    if entities.get("employee"):
        eid = entities["employee"]
        data["entity_employee"] = safe_get_doc("Employee", eid)
        data["entity_employee_name"] = entities.get("employee_display", eid)
        fetch_entity_related("Employee", eid, data, "entity_employee_")
        
        slips = data.get("entity_employee_salary_slips", [])
        submitted_slips = [s for s in slips if s.get("status") == "Submitted"]
        data["entity_employee_latest_net_pay"] = submitted_slips[0].get("net_pay") if submitted_slips else None
    
    # 4. Keyword-based data fetching (ALL matching keywords)
    kw_map = get_keywords_map()
    fetched_doctypes = set()
    
    for keyword, doctype in kw_map.items():
        if keyword in q and doctype not in fetched_doctypes:
            cfg = get_config(doctype)
            fields = cfg.get("fetch_fields", ["name"])
            rows = safe_get_all(doctype, fields, limit=1000)
            key = doctype.lower().replace(" ", "_") + "s"
            data[key] = rows
            data[f"total_{key}"] = len(rows)
            fetched_doctypes.add(doctype)
    
    # 5. Sales Invoice detailed data
    sinv_kw = ["invoice", "invoices", "revenue", "outstanding", "overdue", "paid",
               "billing", "amount", "total revenue", "this month", "collection",
               "receivable", "earning", "income", "sale", "sales", "collection"]
    if any(w in q for w in sinv_kw):
        get_sales_invoice_summary(data)
    
    # 5b. Purchase Invoice detailed data
    pinv_kw = ["purchase", "payable", "expense", "bought", "vendor bill",
               "purchase amount", "payment to supplier", "purchase this month"]
    if any(w in q for w in pinv_kw):
        get_purchase_invoice_summary(data)
    
    # 6. Business summary
    summary_kw = ["summary", "business", "overview", "dashboard", "report", "analytics",
                "how is business", "company status", "financial summary"]
    if any(w in q for w in summary_kw):
        get_business_summary(data)
    
    return data
