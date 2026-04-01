"""
Document Processor - OCR and Document Creation
v2.0.0 - Creates SI, PI, SO, PO from AI/OCR data
"""

import frappe
from frappe.model.mapper import get_mapped_doc
from ..utils.safe_db import safe_get_doc, safe_exists
from ..config.data_registry import get_create_config


# ═══════════════════════════════════════════════════════════════════════════
# AI DOCUMENT CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_from_ai(doctype, data):
    """
    Create document from AI-parsed data.
    Main entry for AI-powered document creation.
    """
    if not doctype or not data:
        return {"type": "error", "message": "Missing doctype or data for creation."}
    
    try:
        # Normalize doctype name
        doctype = doctype.strip()
        
        # Route to specific creators
        creators = {
            "Customer": create_customer,
            "Supplier": create_supplier,
            "Item": create_item,
            "Lead": create_lead,
            "Employee": create_employee,
            "Sales Order": create_sales_order,
            "Purchase Order": create_purchase_order,
        }
        
        creator = creators.get(doctype)
        if creator:
            return creator(data)
        
        # Generic document creation
        return create_generic_doc(doctype, data)
    
    except Exception as e:
        frappe.log_error(f"create_from_ai [{doctype}]: {e}")
        return {"type": "error", "message": f"Could not create {doctype}: {str(e)[:100]}"}


def create_customer(data):
    """Create Customer from AI data."""
    name = data.get("customer_name") or data.get("name") or data.get("company_name")
    if not name:
        return {"type": "error", "message": "Customer name required."}
    
    # Check if exists
    existing = frappe.db.exists("Customer", {"customer_name": name})
    if existing:
        return {
            "type": "info",
            "message": f"Customer '{name}' already exists.",
            "link": f"/app/customer/{existing}",
            "doctype": "Customer"
        }
    
    # Create
    doc = frappe.new_doc("Customer")
    doc.customer_name = name
    doc.customer_type = data.get("customer_type", "Individual")
    doc.customer_group = data.get("customer_group", "All Customer Groups")
    doc.territory = data.get("territory", "All Territories")
    doc.gstin = data.get("gstin", "")
    doc.mobile_no = data.get("mobile_no", "")
    doc.email_id = data.get("email_id", "")
    
    try:
        doc.insert(ignore_permissions=True)
        return {
            "type": "success",
            "message": f"✅ Customer '{name}' created successfully!",
            "link": f"/app/customer/{doc.name}",
            "doctype": "Customer",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create customer: {str(e)[:100]}"}


def create_supplier(data):
    """Create Supplier from AI data."""
    name = data.get("supplier_name") or data.get("name") or data.get("company_name")
    if not name:
        return {"type": "error", "message": "Supplier name required."}
    
    existing = frappe.db.exists("Supplier", {"supplier_name": name})
    if existing:
        return {
            "type": "info",
            "message": f"Supplier '{name}' already exists.",
            "link": f"/app/supplier/{existing}",
            "doctype": "Supplier"
        }
    
    doc = frappe.new_doc("Supplier")
    doc.supplier_name = name
    doc.supplier_type = data.get("supplier_type", "Individual")
    doc.supplier_group = data.get("supplier_group", "All Supplier Groups")
    doc.gstin = data.get("gstin", "")
    doc.mobile_no = data.get("mobile_no", "")
    doc.email_id = data.get("email_id", "")
    
    try:
        doc.insert(ignore_permissions=True)
        return {
            "type": "success",
            "message": f"✅ Supplier '{name}' created successfully!",
            "link": f"/app/supplier/{doc.name}",
            "doctype": "Supplier",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create supplier: {str(e)[:100]}"}


def create_item(data):
    """Create Item from AI data."""
    name = data.get("item_name") or data.get("name")
    if not name:
        return {"type": "error", "message": "Item name required."}
    
    item_code = data.get("item_code") or name[:50]
    
    if frappe.db.exists("Item", item_code):
        return {
            "type": "info",
            "message": f"Item '{item_code}' already exists.",
            "link": f"/app/item/{item_code}",
            "doctype": "Item"
        }
    
    doc = frappe.new_doc("Item")
    doc.item_code = item_code
    doc.item_name = name
    doc.item_group = data.get("item_group", "All Item Groups")
    doc.stock_uom = data.get("stock_uom", "Nos")
    doc.is_stock_item = data.get("is_stock_item", 1)
    doc.standard_rate = data.get("standard_rate", 0)
    
    try:
        doc.insert(ignore_permissions=True)
        return {
            "type": "success",
            "message": f"✅ Item '{name}' created successfully!",
            "link": f"/app/item/{doc.name}",
            "doctype": "Item",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create item: {str(e)[:100]}"}


def create_lead(data):
    """Create Lead from AI data."""
    name = data.get("lead_name") or data.get("name")
    if not name:
        return {"type": "error", "message": "Lead name required."}
    
    doc = frappe.new_doc("Lead")
    doc.lead_name = name
    doc.status = data.get("status", "Open")
    doc.email_id = data.get("email_id", "")
    doc.mobile_no = data.get("mobile_no", "")
    doc.source = data.get("source", "Website")
    doc.company_name = data.get("company_name", "")
    
    try:
        doc.insert(ignore_permissions=True)
        return {
            "type": "success",
            "message": f"✅ Lead '{name}' created successfully!",
            "link": f"/app/Lead/{doc.name}",
            "doctype": "Lead",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create lead: {str(e)[:100]}"}


def create_employee(data):
    """Create Employee from AI data."""
    first_name = data.get("first_name") or data.get("employee_name")
    if not first_name:
        return {"type": "error", "message": "Employee name required."}
    
    doc = frappe.new_doc("Employee")
    doc.first_name = first_name
    doc.gender = data.get("gender", "Male")
    doc.status = data.get("status", "Active")
    doc.department = data.get("department", "")
    doc.designation = data.get("designation", "")
    doc.date_of_joining = data.get("date_of_joining", frappe.utils.today())
    doc.mobile_no = data.get("mobile_no", "")
    
    try:
        doc.insert(ignore_permissions=True)
        return {
            "type": "success",
            "message": f"✅ Employee '{first_name}' created successfully!",
            "link": f"/app/Employee/{doc.name}",
            "doctype": "Employee",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create employee: {str(e)[:100]}"}


def create_sales_order(data):
    """Create Sales Order from AI data."""
    customer = data.get("customer")
    if not customer:
        return {"type": "error", "message": "Customer required for Sales Order."}
    
    if not frappe.db.exists("Customer", customer):
        # Create customer first
        cust_result = create_customer({"customer_name": customer})
        if cust_result["type"] == "error":
            return cust_result
    
    doc = frappe.new_doc("Sales Order")
    doc.customer = customer
    doc.transaction_date = data.get("transaction_date", frappe.utils.today())
    doc.delivery_date = data.get("delivery_date", "")
    
    # Add items
    items = data.get("items", [])
    if not items:
        items = [{"item_code": "Services", "qty": 1, "rate": data.get("grand_total", 0)}]
    
    for item in items:
        doc.append("items", {
            "item_code": item.get("item_code", item.get("item_name", "Services")),
            "qty": item.get("qty", 1),
            "rate": item.get("rate", 0),
            "amount": item.get("amount", item.get("qty", 1) * item.get("rate", 0))
        })
    
    try:
        doc.insert(ignore_permissions=True)
        doc.save()
        return {
            "type": "success",
            "message": f"✅ Sales Order '{doc.name}' created successfully!",
            "link": f"/app/Sales-Order/{doc.name}",
            "doctype": "Sales Order",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create sales order: {str(e)[:100]}"}


def create_purchase_order(data):
    """Create Purchase Order from AI data."""
    supplier = data.get("supplier")
    if not supplier:
        return {"type": "error", "message": "Supplier required for Purchase Order."}
    
    if not frappe.db.exists("Supplier", supplier):
        supp_result = create_supplier({"supplier_name": supplier})
        if supp_result["type"] == "error":
            return supp_result
    
    doc = frappe.new_doc("Purchase Order")
    doc.supplier = supplier
    doc.transaction_date = data.get("transaction_date", frappe.utils.today())
    
    items = data.get("items", [])
    if not items:
        items = [{"item_code": "Services", "qty": 1, "rate": data.get("grand_total", 0)}]
    
    for item in items:
        doc.append("items", {
            "item_code": item.get("item_code", item.get("item_name", "Services")),
            "qty": item.get("qty", 1),
            "rate": item.get("rate", 0),
            "amount": item.get("amount", item.get("qty", 1) * item.get("rate", 0))
        })
    
    try:
        doc.insert(ignore_permissions=True)
        doc.save()
        return {
            "type": "success",
            "message": f"✅ Purchase Order '{doc.name}' created successfully!",
            "link": f"/app/Purchase-Order/{doc.name}",
            "doctype": "Purchase Order",
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create purchase order: {str(e)[:100]}"}


def create_generic_doc(doctype, data):
    """Create any document type generically."""
    cfg = get_create_config(doctype)
    
    doc = frappe.new_doc(doctype)
    
    # Apply defaults from registry
    for key, value in cfg.get("defaults", {}).items():
        if hasattr(doc, key) and not data.get(key):
            setattr(doc, key, value)
    
    # Apply provided data
    for key, value in data.items():
        if hasattr(doc, key):
            setattr(doc, key, value)
    
    try:
        doc.insert(ignore_permissions=True)
        return {
            "type": "success",
            "message": f"✅ {doctype} '{doc.name}' created successfully!",
            "link": f"/app/{doctype.lower().replace(' ', '-')}/{doc.name}",
            "doctype": doctype,
            "name": doc.name
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to create {doctype}: {str(e)[:100]}"}


# ═══════════════════════════════════════════════════════════════════════════
# OCR INVOICE CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_invoice_from_extracted(invoice_type, extracted_data):
    """
    Create Sales or Purchase Invoice from OCR-extracted data.
    invoice_type: "sales" or "purchase"
    """
    party_name = extracted_data.get("party_name", "")
    
    if invoice_type == "sales":
        return create_sales_invoice_from_ocr(extracted_data, party_name)
    else:
        return create_purchase_invoice_from_ocr(extracted_data, party_name)


def get_or_create_item(item_name, item_code=None):
    """Get existing item or create new one."""
    if not item_name:
        return None
    
    # Try to find by item_code first
    if item_code and frappe.db.exists("Item", item_code):
        return item_code
    
    # Try to find by item_name
    existing = frappe.db.get_value("Item", {"item_name": item_name}, "name")
    if existing:
        return existing
    
    # Create new item
    result = create_item({
        "item_name": item_name,
        "item_code": item_code or item_name[:50],
        "item_group": "All Item Groups",
        "is_stock_item": 0  # Non-stock item for services/one-off items
    })
    
    if result["type"] in ["success", "info"]:
        return result.get("name") or frappe.db.exists("Item", {"item_name": item_name})
    return None


def get_or_create_customer(customer_name):
    """Get existing customer or create new one."""
    if not customer_name:
        return "Cash Customer"
    
    existing = frappe.db.exists("Customer", {"customer_name": customer_name})
    if existing:
        return existing
    
    result = create_customer({"customer_name": customer_name})
    if result["type"] in ["success", "info"]:
        return result.get("name") or frappe.db.exists("Customer", {"customer_name": customer_name})
    return "Cash Customer"


def get_or_create_supplier(supplier_name):
    """Get existing supplier or create new one."""
    if not supplier_name:
        return None
    
    existing = frappe.db.exists("Supplier", {"supplier_name": supplier_name})
    if existing:
        return existing
    
    result = create_supplier({"supplier_name": supplier_name})
    if result["type"] in ["success", "info"]:
        return result.get("name") or frappe.db.exists("Supplier", {"supplier_name": supplier_name})
    return None


def create_sales_invoice_from_ocr(data, customer_name):
    """Create Sales Invoice from OCR data with auto-creation of missing entities."""
    # Get or create customer
    customer = get_or_create_customer(customer_name)
    
    # Track auto-created items for message
    auto_created_items = []
    
    # Create invoice
    doc = frappe.new_doc("Sales Invoice")
    doc.customer = customer
    doc.posting_date = data.get("posting_date") or frappe.utils.today()
    doc.due_date = data.get("due_date") or ""
    
    # Add items with auto-creation
    items = data.get("items", [])
    for item_data in items:
        item_name = item_data.get("item_name", "Item")
        item_code = item_data.get("item_code") or item_name[:50]
        
        # Get or create the item
        actual_item_code = get_or_create_item(item_name, item_code)
        if actual_item_code and actual_item_code not in auto_created_items:
            auto_created_items.append(actual_item_code)
        
        doc.append("items", {
            "item_code": actual_item_code or item_code,
            "item_name": item_name,
            "description": item_data.get("description", item_name),
            "qty": item_data.get("qty", 1),
            "rate": item_data.get("rate", 0),
            "uom": item_data.get("uom", "Nos"),
            "amount": item_data.get("amount", item_data.get("qty", 1) * item_data.get("rate", 0))
        })
    
    # Add taxes if present
    taxes = data.get("taxes", [])
    for tax in taxes:
        doc.append("taxes", {
            "charge_type": "Actual",
            "account_head": get_tax_account(tax.get("tax_type", "CGST")),
            "description": tax.get("description", tax.get("tax_type", "Tax")),
            "tax_amount": tax.get("amount", 0)
        })
    
    try:
        doc.insert(ignore_permissions=True)
        doc.save()
        
        # Build success message with auto-created info
        msg = f"✅ Draft Sales Invoice '{doc.name}' created from bill!"
        if auto_created_items:
            msg += f"<br><small>Auto-created items: {', '.join(auto_created_items[:3])}{'...' if len(auto_created_items) > 3 else ''}</small>"
        
        return {
            "type": "success",
            "message": msg,
            "link": f"/app/sales-invoice/{doc.name}",
            "doctype": "Sales Invoice",
            "name": doc.name,
            "auto_created_items": auto_created_items
        }
    except Exception as e:
        frappe.log_error(f"OCR SI creation error: {e}")
        return {"type": "error", "message": f"Failed to create invoice: {str(e)[:100]}"}


def create_purchase_invoice_from_ocr(data, supplier_name):
    """Create Purchase Invoice from OCR data with auto-creation of missing entities."""
    # Get or create supplier
    supplier = get_or_create_supplier(supplier_name)
    if not supplier:
        return {"type": "error", "message": "Could not determine supplier for purchase invoice."}
    
    # Track auto-created items
    auto_created_items = []
    
    doc = frappe.new_doc("Purchase Invoice")
    doc.supplier = supplier
    doc.bill_no = data.get("invoice_number", "")
    doc.posting_date = data.get("posting_date") or frappe.utils.today()
    doc.bill_date = data.get("posting_date") or frappe.utils.today()
    doc.due_date = data.get("due_date") or ""
    
    # Add items with auto-creation
    items = data.get("items", [])
    for item_data in items:
        item_name = item_data.get("item_name", "Item")
        item_code = item_data.get("item_code") or item_name[:50]
        
        actual_item_code = get_or_create_item(item_name, item_code)
        if actual_item_code and actual_item_code not in auto_created_items:
            auto_created_items.append(actual_item_code)
        
        doc.append("items", {
            "item_code": actual_item_code or item_code,
            "item_name": item_name,
            "description": item_data.get("description", item_name),
            "qty": item_data.get("qty", 1),
            "rate": item_data.get("rate", 0),
            "uom": item_data.get("uom", "Nos"),
            "amount": item_data.get("amount", item_data.get("qty", 1) * item_data.get("rate", 0))
        })
    
    # Add taxes
    taxes = data.get("taxes", [])
    for tax in taxes:
        doc.append("taxes", {
            "charge_type": "Actual",
            "account_head": get_tax_account(tax.get("tax_type", "CGST"), purchase=True),
            "description": tax.get("description", tax.get("tax_type", "Tax")),
            "tax_amount": tax.get("amount", 0)
        })
    
    try:
        doc.insert(ignore_permissions=True)
        doc.save()
        
        # Build success message
        msg = f"✅ Draft Purchase Invoice '{doc.name}' created from bill!"
        if auto_created_items:
            msg += f"<br><small>Auto-created items: {', '.join(auto_created_items[:3])}{'...' if len(auto_created_items) > 3 else ''}</small>"
        
        return {
            "type": "success",
            "message": msg,
            "link": f"/app/purchase-invoice/{doc.name}",
            "doctype": "Purchase Invoice",
            "name": doc.name,
            "auto_created_items": auto_created_items
        }
    except Exception as e:
        frappe.log_error(f"OCR PI creation error: {e}")
        return {"type": "error", "message": f"Failed to create purchase invoice: {str(e)[:100]}"}


def get_tax_account(tax_type, purchase=False):
    """Get default tax account head."""
    prefix = "Input" if purchase else "Output"
    
    tax_accounts = {
        "CGST": f"{prefix} CGST - _TC",
        "SGST": f"{prefix} SGST - _TC",
        "IGST": f"{prefix} IGST - _TC",
        "VAT": f"{prefix} VAT - _TC",
    }
    
    # Try to find in system
    for key, account in tax_accounts.items():
        if key in str(tax_type).upper():
            if frappe.db.exists("Account", account):
                return account
    
    # Fallback
    return f"{prefix} Tax - _TC"
