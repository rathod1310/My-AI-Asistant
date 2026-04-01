"""
Data Registry - ONE place for ALL doctype configurations
v2.0.0 - Centralized configuration for all ERPNext doctypes
"""

# ═══════════════════════════════════════════════════════════════════════════
# MASTER REGISTRY - Add new doctypes here
# ═══════════════════════════════════════════════════════════════════════════

REGISTRY = {

    # ── CUSTOMER ─────────────────────────────────────────────────────────────
    "Customer": {
        "fetch_fields": [
            "name", "customer_name", "customer_group",
            "territory", "gstin", "mobile_no", "email_id", "customer_type"
        ],
        "keywords": [
            "customer", "customers", "client", "buyer", "all customer",
            "consumer", "account", "debtor"
        ],
        "create_defaults": {
            "customer_type": "Individual",
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
        },
        "name_field": "customer_name",
        "label": "Customer",
        "related": {
            "Sales Invoice":  {"filter_field": "customer",   "fields": ["name","customer","customer_name","status","posting_date","due_date","grand_total","outstanding_amount","docstatus"]},
            "Sales Order":    {"filter_field": "customer",   "fields": ["name","customer","customer_name","status","transaction_date","delivery_date","grand_total"]},
            "Payment Entry":  {"filter_field": "party",      "extra_filters": {"party_type": "Customer"}, "fields": ["name","party","party_name","payment_type","paid_amount","posting_date","mode_of_payment"]},
            "Delivery Note":  {"filter_field": "customer",   "fields": ["name","customer","customer_name","status","posting_date","grand_total"]},
            "Quotation":      {"filter_field": "party_name", "fields": ["name","party_name","status","transaction_date","grand_total"]},
        },
    },

    # ── SUPPLIER ─────────────────────────────────────────────────────────────
    "Supplier": {
        "fetch_fields": [
            "name", "supplier_name", "supplier_group", "gstin", "mobile_no", "email_id"
        ],
        "keywords": [
            "supplier", "suppliers", "vendor", "vendors", "all supplier",
            "seller", "provider", "creditor"
        ],
        "create_defaults": {
            "supplier_type": "Individual",
            "supplier_group": "All Supplier Groups",
        },
        "name_field": "supplier_name",
        "label": "Supplier",
        "related": {
            "Purchase Invoice": {"filter_field": "supplier", "fields": ["name","supplier","supplier_name","status","posting_date","grand_total","outstanding_amount","docstatus"]},
            "Purchase Order":   {"filter_field": "supplier", "fields": ["name","supplier","supplier_name","status","transaction_date","grand_total"]},
            "Payment Entry":    {"filter_field": "party",    "extra_filters": {"party_type": "Supplier"}, "fields": ["name","party","party_name","payment_type","paid_amount","posting_date","mode_of_payment"]},
            "Purchase Receipt": {"filter_field": "supplier", "fields": ["name","supplier","supplier_name","status","posting_date","grand_total"]},
        },
    },

    # ── ITEM ─────────────────────────────────────────────────────────────────
    "Item": {
        "fetch_fields": [
            "name", "item_name", "item_code", "item_group",
            "stock_uom", "standard_rate", "is_stock_item", "valuation_rate"
        ],
        "keywords": [
            "item", "items", "product", "products", "stock", "inventory", 
            "all item", "goods", "merchandise", "sku"
        ],
        "create_defaults": {
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 1,
        },
        "name_field": "item_name",
        "label": "Item",
        "related": {},
    },

    # ── EMPLOYEE ─────────────────────────────────────────────────────────────
    "Employee": {
        "fetch_fields": [
            "name", "employee_name", "department", "designation",
            "status", "date_of_joining", "gender", "mobile_no", "branch"
        ],
        "keywords": [
            "employee", "employees", "staff", "worker", "all employee",
            "personnel", "team member", "hr"
        ],
        "create_defaults": {
            "gender": "Male",
            "status": "Active",
        },
        "name_field": "first_name",
        "label": "Employee",
        "related": {
            "Attendance":        {"filter_field": "employee", "fields": ["name","attendance_date","status","employee_name"]},
            "Leave Application": {"filter_field": "employee", "fields": ["name","leave_type","from_date","to_date","status","total_leave_days"]},
            "Salary Slip":       {"filter_field": "employee", "fields": ["name","start_date","end_date","net_pay","gross_pay","total_deduction","status"]},
        },
    },

    # ── LEAD ─────────────────────────────────────────────────────────────────
    "Lead": {
        "fetch_fields": [
            "name", "lead_name", "status", "email_id", "mobile_no", 
            "source", "lead_owner", "company_name"
        ],
        "keywords": [
            "lead", "leads", "prospect", "opportunity", "potential",
            "inquiry", "enquiry"
        ],
        "create_defaults": {"status": "Open"},
        "name_field": "lead_name",
        "label": "Lead",
        "related": {},
    },

    # ── SALES INVOICE ─────────────────────────────────────────────────────────
    "Sales Invoice": {
        "fetch_fields": [
            "name", "customer", "customer_name", "status",
            "posting_date", "due_date", "grand_total",
            "outstanding_amount", "discount_amount", "docstatus", "currency"
        ],
        "keywords": [
            "invoice", "invoices", "sinv", "sales invoice", "revenue", 
            "outstanding", "overdue", "paid", "unpaid", "due", "billing", 
            "amount", "total revenue", "this month", "collection",
            "receivable", "grand total", "earning", "income", "sale", "sales",
            "all invoice", "pending payment"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Sales Invoice",
        "related": {},
    },

    # ── PURCHASE INVOICE ──────────────────────────────────────────────────────
    "Purchase Invoice": {
        "fetch_fields": [
            "name", "supplier", "supplier_name", "status",
            "posting_date", "grand_total", "outstanding_amount", "docstatus"
        ],
        "keywords": [
            "purchase invoice", "pinv", "payable", "purchase bill", "bill",
            "purchase amount", "expense", "vendor bill", "purchase order",
            "bought", "procurement"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Purchase Invoice",
        "related": {},
    },

    # ── SALES ORDER ───────────────────────────────────────────────────────────
    "Sales Order": {
        "fetch_fields": [
            "name", "customer", "customer_name", "status",
            "transaction_date", "delivery_date", "grand_total", "per_delivered"
        ],
        "keywords": [
            "sales order", "so-", "order", "all order", "so", "confirmed order"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Sales Order",
        "related": {},
    },

    # ── PURCHASE ORDER ────────────────────────────────────────────────────────
    "Purchase Order": {
        "fetch_fields": [
            "name", "supplier", "supplier_name", "status",
            "transaction_date", "grand_total", "per_received"
        ],
        "keywords": [
            "purchase order", "po-", "all purchase order", "po", 
            "confirmed purchase"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Purchase Order",
        "related": {},
    },

    # ── PAYMENT ENTRY ─────────────────────────────────────────────────────────
    "Payment Entry": {
        "fetch_fields": [
            "name", "party", "party_name", "party_type", "payment_type",
            "paid_amount", "posting_date", "mode_of_payment", "reference_no"
        ],
        "keywords": [
            "payment", "payments", "receipt", "collection", "received", 
            "paid amount", "money", "cash", "bank", "transaction", "remittance"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Payment Entry",
        "related": {},
    },

    # ── QUOTATION ─────────────────────────────────────────────────────────────
    "Quotation": {
        "fetch_fields": [
            "name", "party_name", "status", "transaction_date", "grand_total", "valid_till"
        ],
        "keywords": [
            "quotation", "quote", "quot-", "all quotation", "proforma", 
            "estimate", "proposal", "bid"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Quotation",
        "related": {},
    },

    # ── DELIVERY NOTE ─────────────────────────────────────────────────────────
    "Delivery Note": {
        "fetch_fields": [
            "name", "customer", "customer_name", "status", "posting_date", "grand_total"
        ],
        "keywords": [
            "delivery", "delivery note", "shipment", "dispatch", "dn-",
            "delivered", "shipping"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Delivery Note",
        "related": {},
    },

    # ── JOURNAL ENTRY ─────────────────────────────────────────────────────────
    "Journal Entry": {
        "fetch_fields": [
            "name", "title", "posting_date", "total_amount", "voucher_type", "docstatus"
        ],
        "keywords": [
            "journal", "journal entry", "jv", "voucher", "jv-",
            "accounting entry", "debit credit"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Journal Entry",
        "related": {},
    },

    # ── ATTENDANCE ────────────────────────────────────────────────────────────
    "Attendance": {
        "fetch_fields": [
            "name", "employee", "employee_name", "attendance_date", "status", "department"
        ],
        "keywords": [
            "attendance", "present", "absent", "leave", "holiday",
            "check in", "check out"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Attendance",
        "related": {},
    },

    # ── SALARY SLIP ───────────────────────────────────────────────────────────
    "Salary Slip": {
        "fetch_fields": [
            "name", "employee", "employee_name", "start_date",
            "end_date", "gross_pay", "net_pay", "total_deduction", "status"
        ],
        "keywords": [
            "salary", "payroll", "payslip", "wage", "ctc", "net pay",
            "gross pay", "monthly salary", "income"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Salary Slip",
        "related": {},
    },

    # ── PROJECT ───────────────────────────────────────────────────────────────
    "Project": {
        "fetch_fields": [
            "name", "project_name", "status", "percent_complete", 
            "expected_end_date", "project_type"
        ],
        "keywords": [
            "project", "projects", "job", "engagement", "assignment"
        ],
        "create_defaults": {},
        "name_field": "project_name",
        "label": "Project",
        "related": {
            "Task": {"filter_field": "project", "fields": ["name","subject","status","priority","exp_end_date"]},
        },
    },

    # ── TASK ──────────────────────────────────────────────────────────────────
    "Task": {
        "fetch_fields": [
            "name", "subject", "status", "priority", "exp_end_date", "project", "owner"
        ],
        "keywords": [
            "task", "tasks", "todo", "to do", "action item", "activity"
        ],
        "create_defaults": {},
        "name_field": "subject",
        "label": "Task",
        "related": {},
    },

    # ── LEAVE APPLICATION ────────────────────────────────────────────────────
    "Leave Application": {
        "fetch_fields": [
            "name", "employee", "employee_name", "leave_type", "from_date", 
            "to_date", "status", "total_leave_days"
        ],
        "keywords": [
            "leave", "vacation", "time off", "absence", "holiday request"
        ],
        "create_defaults": {},
        "name_field": None,
        "label": "Leave Application",
        "related": {},
    },


    # ── Demo APPLICATION ────────────────────────────────────────────────────
    "Demo": {
        "fetch_fields": [
            "name"
        ],
        "keywords": [
            "demo"
        ],
        "create_defaults": {},
        "name_field": "name",
        "label": "Demo",
        "related": {
            "Demo": {"filter_field": "demo", "fields": ["name"]}
        },
    },

}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_all_doctypes():
    """Returns list of all registered doctypes."""
    return list(REGISTRY.keys())

def get_config(doctype):
    """Returns config for specific doctype."""
    return REGISTRY.get(doctype, {})

def get_keywords_map():
    """Returns {keyword: doctype} mapping for all registered doctypes."""
    mapping = {}
    for dt, cfg in REGISTRY.items():
        for kw in cfg.get("keywords", []):
            mapping[kw.lower()] = dt
    return mapping

def get_entity_doctypes():
    """Returns doctypes that have entity-level related data."""
    return {dt: cfg for dt, cfg in REGISTRY.items() if cfg.get("related")}

def get_create_config(doctype):
    """Returns creation configuration for a doctype."""
    cfg = get_config(doctype)
    return {
        "defaults": cfg.get("create_defaults", {}),
        "name_field": cfg.get("name_field"),
        "label": cfg.get("label", doctype)
    }

def search_doctype_by_keyword(keyword):
    """Find doctype by keyword."""
    keyword = keyword.lower()
    kw_map = get_keywords_map()
    return kw_map.get(keyword)
