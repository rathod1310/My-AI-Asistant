"""
AI Helper - Main API endpoints for AI Assistant
v2.0.0 - Clean, no hardcoding
"""

import frappe
import requests
import json
import re

from ..config.data_registry import REGISTRY, get_keywords_map, get_config
from .data_fetcher import get_live_data
from ..utils.safe_db import safe_get_doc


def get_api_key():
    """Get API key from site config."""
    return frappe.conf.get("vertex_api_key") or frappe.conf.get("ai_api_key") or frappe.conf.get("gemini_api_key")


def build_system_prompt():
    """Build system prompt from REGISTRY."""
    doctype_list = "\n".join(f"- {dt}" for dt in REGISTRY)
    
    return f"""You are an advanced SkyERP AI Assistant with access to LIVE business data.

STRICT RESPONSE RULES — return ONLY valid JSON, no text outside JSON:

1. For text answers (counts, totals, single facts):
{{"type": "text", "message": "HTML answer with <b>bold</b> data"}}

2. For creating records:
{{"type": "create", "doctype": "DocType", "data": {{...}}}}

3. For LISTS of records (show, list, all, get):
{{"type": "list", "message": "header text", "items": ["name1","name2"], "doctype": "Customer", "link": "/app/customer"}}

REGISTERED DOCTYPES:
{doctype_list}

WHEN TO USE type="list":
- User asks "show customers" or "list all customers"
- User asks "show quotations" or "all quotations"
- User asks "what are my items" or "list products"
- User asks "show me invoices" or "display orders"

LIST RESPONSE MUST INCLUDE:
- "type": "list"
- "items": array of document names (e.g., ["CUST-001", "CUST-002"])
- "doctype": the exact doctype name from REGISTERED DOCTYPES above
- "link": "/app/doctypename" (e.g., "/app/customer", "/app/quotation")

COMPREHENSIVE ANSWERING RULES:
1. Use EXACT numbers from live data — never guess
2. Show ₹ symbol for Indian Rupee amounts  
3. Return ONLY valid JSON. No text outside JSON.
4. If live data shows empty [], say "No records found"
5. For "show/list/all" queries → ALWAYS use type="list" with items array
6. For count queries → use type="text" with the number
7. When listing, extract names from live data keys like "customers", "quotations", etc.
8. If "specific_document" is in live data, answer using that document's details
9. If "specific_document_items" is in data, use it for item counts and details
10. NEVER say "not available" or "cannot provide" if data exists in live_data
11. For Purchase Order queries, look for "purchase_orders" or "specific_document" in data
12. For Customer queries, look for "customers", "total_customers", or "overview" in data
13. For ANY document ID mentioned (like PUR-ORD-2026-00003), check "specific_document" first

EXAMPLE RESPONSES:
Q: "How many customers?" → {{"type": "text", "message": "You have <b>15 customers</b>."}}
Q: "Show customers" → {{"type": "list", "message": "Your customers:", "items": ["CUST-001", "CUST-002"], "doctype": "Customer", "link": "/app/customer"}}
Q: "List quotations" → {{"type": "list", "message": "Your quotations:", "items": ["QTN-2024-00001"], "doctype": "Quotation", "link": "/app/quotation"}}
Q: "Revenue?" → {{"type": "text", "message": "Revenue: <b>₹50,000</b>"}}
Q: "How many items in ACC-SINV-2026-00005?" → {{"type": "text", "message": "Sales Invoice ACC-SINV-2026-00005 has <b>3 items</b> with total amount <b>₹15,000</b>."}}
Q: "How many items in PUR-ORD-2026-00003?" → {{"type": "text", "message": "Purchase Order PUR-ORD-2026-00003 has <b>5 items</b>."}}
Q: "Create sales invoice for ABC Ltd" → {{"type": "create", "doctype": "Sales Invoice", "data": {{"customer": "ABC Ltd"}}}}
Q: "Create purchase invoice from XYZ" → {{"type": "create", "doctype": "Purchase Invoice", "data": {{"supplier": "XYZ"}}}}
Q: "Create sales order for ABC" → {{"type": "create", "doctype": "Sales Order", "data": {{"customer": "ABC"}}}}
Q: "Create purchase order from XYZ" → {{"type": "create", "doctype": "Purchase Order", "data": {{"supplier": "XYZ"}}}}

Return ONLY valid JSON."""


def trim_live_data(live_data, max_chars=18000):
    """Trim large data to fit token limits."""
    s = json.dumps(live_data, indent=2, default=str)
    if len(s) <= max_chars:
        return s
    
    trimmed = {}
    for k, v in live_data.items():
        if isinstance(v, list) and len(v) > 100:
            trimmed[k] = v[:100]
            trimmed[f"{k}_total_count"] = len(v)
        else:
            trimmed[k] = v
    
    return json.dumps(trimmed, indent=2, default=str)[:max_chars]


def call_gemini(system_prompt, user_message, api_key, max_tokens=2048):
    """Call Gemini API with retry logic."""
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
        headers={"content-type": "application/json"},
        json={
            "contents": [{"parts": [{"text": system_prompt + "\n\n" + user_message}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.1}
        },
        timeout=60
    )
    
    result = response.json()
    if "error" in result:
        raise Exception("Gemini API Error: " + result["error"].get("message", "Unknown"))
    
    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def parse_ai_response(ai_reply):
    """Parse AI response - handle markdown code blocks."""
    # Extract JSON from markdown code blocks
    if "```" in ai_reply:
        for part in ai_reply.split("```"):
            part = part.strip()
            if part.lower().startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                try:
                    return json.loads(part)
                except:
                    pass
    
    # Try direct JSON parse
    try:
        return json.loads(ai_reply.strip())
    except:
        # Fallback: wrap as text response
        return {"type": "text", "message": ai_reply}


def extract_context_from_history(conversation_history):
    """Extract topics from conversation history (both user and assistant messages)."""
    previous_topics = []
    
    if not conversation_history:
        return previous_topics
    
    # Topic keyword map
    topic_keywords = {
        "Customer":       ["customer", "client", "buyer", "customers", "clients"],
        "Supplier":       ["supplier", "vendor", "suppliers", "vendors"],
        "Sales Invoice":  ["sales invoice", "sinv", "invoice", "revenue", "billing", "receivable"],
        "Purchase Invoice": ["purchase invoice", "pinv", "purchase bill", "payable", "expense"],
        "Sales Order":    ["sales order", "so-"],
        "Purchase Order": ["purchase order", "po-"],
        "Item":           ["item", "product", "stock", "inventory", "items", "products"],
        "Employee":       ["employee", "staff", "salary", "payroll", "hr", "employees"],
        "Payment Entry":  ["payment", "receipt", "collection", "payments"],
        "Quotation":      ["quotation", "quote", "quotations"],
        "Lead":           ["lead", "prospect", "leads"],
    }
    
    try:
        history = json.loads(conversation_history) if isinstance(conversation_history, str) else conversation_history
        if isinstance(history, list):
            # Read both user and assistant messages for context
            for msg in reversed(history[-6:]):
                if not isinstance(msg, dict):
                    continue
                text = msg.get("content", "").lower()
                for topic, keywords in topic_keywords.items():
                    if any(kw in text for kw in keywords):
                        if topic not in previous_topics:
                            previous_topics.append(topic)
    except:
        pass
    
    return previous_topics
def expand_vague_question(question, previous_topics):
    """Expand vague follow-up questions using context."""
    q_lower = question.lower().strip()
    
    # Pattern detection for vague questions
    vague_patterns = [
        # Supplier patterns
        (r"(what about|show me|tell me about|and|now|supplier|vendors?|vendor)", "Supplier"),
        # Customer patterns
        (r"(what about|show me|tell me about|and|now|customer|clients?|buyers?)", "Customer"),
        # Sales Invoice patterns
        (r"(what about|show me|tell me about|and|now|sales invoice|sinv|invoices?)", "Sales Invoice"),
        # Purchase Invoice patterns
        (r"(what about|show me|tell me about|and|now|purchase invoice|pinv|purchase bill)", "Purchase Invoice"),
        # Sales Order patterns
        (r"(what about|show me|tell me about|and|now|sales order|so-)", "Sales Order"),
        # Purchase Order patterns
        (r"(what about|show me|tell me about|and|now|purchase order|po-)", "Purchase Order"),
        # Item patterns
        (r"(what about|show me|tell me about|and|now|items?|products?|stock|inventory)", "Item"),
        # Employee patterns
        (r"(what about|show me|tell me about|and|now|employees?|staff|team|hr)", "Employee"),
        # Payment patterns
        (r"(what about|show me|tell me about|and|now|payments?|receipts?|collection)", "Payment Entry"),
        # Quotation patterns
        (r"(what about|show me|tell me about|and|now|quotations?|quotes?)", "Quotation"),
    ]
    
    # First try exact keyword match for "what about X" type questions
    intro_pattern = r"^(what about|show|tell me about|and what about|now show|now tell)\s+(.+)"
    m = re.search(intro_pattern, q_lower)
    if m:
        topic_part = m.group(2).strip()
        topic_map = {
            "supplier": "Supplier", "suppliers": "Supplier", "vendor": "Supplier", "vendors": "Supplier",
            "customer": "Customer", "customers": "Customer", "client": "Customer", "clients": "Customer",
            "invoice": "Sales Invoice", "invoices": "Sales Invoice", "sales invoice": "Sales Invoice",
            "purchase invoice": "Purchase Invoice", "purchase bill": "Purchase Invoice",
            "sales order": "Sales Order", "order": "Sales Order",
            "purchase order": "Purchase Order",
            "item": "Item", "items": "Item", "product": "Item", "products": "Item", "stock": "Item",
            "employee": "Employee", "employees": "Employee", "staff": "Employee",
            "payment": "Payment Entry", "payments": "Payment Entry",
            "quotation": "Quotation", "quote": "Quotation", "quotations": "Quotation",
            "lead": "Lead", "leads": "Lead",
        }
        for kw, dt in topic_map.items():
            if kw in topic_part:
                return f"Show all {dt}s", True
    
    # Continue / summarize patterns
    continue_patterns = [r"^(what else|anything else|more|other|what next|next|then|continue|go ahead)$"]
    for pattern in continue_patterns:
        if re.search(pattern, q_lower):
            if previous_topics:
                return f"Tell me about {previous_topics[-1]}s", True
            return "Show all business summary", True
    
    # "All / everything" patterns
    if re.search(r"^(all|show all|list all|everything|complete list|full list)$", q_lower):
        return "Show all business summary", True
    
    # Single-word or very short with context
    if len(question.split()) <= 2 and previous_topics:
        simple_refs = ["they", "them", "those", "that", "it", "these", "ones",
                       "list", "details", "info", "more", "next", "show", "yes", "ok", "okay"]
        if q_lower in simple_refs or len(q_lower) <= 5:
            return f"Tell me about {previous_topics[-1]}s", True
    
    return question, False


@frappe.whitelist()
def test_connection():
    """Test AI connection and API key."""
    try:
        import socket
        try:
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        except:
            return {"success": False, "message": "No internet connection on server."}
        
        api_key = get_api_key()
        if not api_key:
            return {"success": False, "message": "API key not configured."}
        
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
            headers={"content-type": "application/json"},
            json={"contents": [{"parts": [{"text": "Say OK"}]}], "generationConfig": {"maxOutputTokens": 5}},
            timeout=15
        )
        
        result = response.json()
        if "error" in result:
            return {"success": False, "message": "API Error: " + str(result["error"].get("message", ""))}
        
        return {"success": True, "message": "Connected"}
    
    except Exception as e:
        return {"success": False, "message": str(e)[:80]}


@frappe.whitelist()
def ask_ai(question, doctype="", conversation_history=""):
    """
    Main AI endpoint - handles all queries with context awareness.
    """
    api_key = get_api_key()
    if not api_key:
        return {"type": "error", "message": "API key not configured."}
    
    # Handle greetings
    q_clean = re.sub(r"[!?.]+$", "", question.lower().strip())
    greetings = ["hi", "hii", "hello", "hey", "good morning", "good evening", "good afternoon", "how are you"]
    if q_clean in greetings:
        user = frappe.session.user_fullname or "there"
        return {
            "type": "text", 
            "message": f"👋 Hello <b>{user}</b>! I am your SkyERP AI Assistant.<br><br>Type <b>help</b> to see commands."
        }
    
    # Handle help
    if q_clean in ["help", "what can you do", "commands", "?"]:
        dt_list = ", ".join(REGISTRY.keys())
        return {
            "type": "text",
            "message": (
                "🤖 <b>SkyERP AI Commands:</b><br><br>"
                "<b>➕ Create:</b> create customer ABC Ltd | add supplier XYZ<br>"
                "<b>📊 Query:</b> how many customers | total revenue this month<br>"
                "<b>🔍 Entity:</b> invoices of ABC Ltd | stock of Laptop<br>"
                "<b>📄 Doc ID:</b> show SINV-2024-00001<br>"
                "<b>📸 Bill Scan:</b> click 📎 to upload bill image<br><br>"
                f"<b>Supported:</b> {dt_list}"
            )
        }
    
    try:
        # Extract context from conversation history
        previous_topics = extract_context_from_history(conversation_history)
        
        # Expand vague questions
        expanded_question, was_expanded = expand_vague_question(question, previous_topics)
        
        # Fetch live data
        live_data = get_live_data(expanded_question)
        
        # Build prompts
        system_prompt = build_system_prompt()
        live_data_str = trim_live_data(live_data)
        
        # Build comprehensive user message
        user_message = f"""LIVE SkyERP Data:
{live_data_str}

Previous Topics: {', '.join(previous_topics) if previous_topics else 'None'}
User Question: {question}
{"Note: This was a vague follow-up, expanded to: " + expanded_question if was_expanded else ""}

Answer based ONLY on the live data above. If data is empty, say so clearly."""
        
        # Call AI
        ai_reply = call_gemini(system_prompt, user_message, api_key)
        parsed = parse_ai_response(ai_reply)
        
        # Handle create actions
        if parsed.get("type") == "create":
            from .document_processor import create_from_ai
            return create_from_ai(parsed.get("doctype"), parsed.get("data", {}))
        
        # Post-process: Add link to list responses if missing
        if parsed.get("type") == "list" and not parsed.get("link"):
            dt = parsed.get("doctype", "")
            if dt:
                # Convert to lowercase with dashes (Frappe v14+ format)
                parsed["link"] = f"/app/{dt.lower().replace(' ', '-')}"
        
        # Post-process: If user asked for list but AI returned text, convert to list
        list_keywords = ["show", "list", "all", "display", "get me", "give me", "what are my", "view"]
        is_list_query = any(kw in question.lower() for kw in list_keywords)
        
        if is_list_query and parsed.get("type") == "text":
            # Try to extract list data from live_data and convert to list response
            for dt_key, dt_name in [
                ("customers", "Customer"),
                ("quotations", "Quotation"),
                ("suppliers", "Supplier"),
                ("items", "Item"),
                ("sales_invoices", "Sales Invoice"),
                ("purchase_invoices", "Purchase Invoice"),
                ("sales_orders", "Sales Order"),
                ("purchase_orders", "Purchase Order"),
                ("payment_entries", "Payment Entry"),
                ("employees", "Employee"),
                ("leads", "Lead"),
                ("projects", "Project"),
                ("tasks", "Task"),
            ]:
                if dt_key in live_data and live_data[dt_key]:
                    items = [r.get("name", "") for r in live_data[dt_key] if r.get("name")]
                    if items:
                        return {
                            "type": "list",
                            "message": f"Your {dt_name.lower()}s:",
                            "items": items[:50],  # Limit to 50 items
                            "doctype": dt_name,
                            "link": f"/app/{dt_name.lower().replace(' ', '-')}"
                        }
        
        # Post-process: Handle count queries (how many) using overview data
        count_keywords = ["how many", "count", "total", "number of"]
        is_count_query = any(kw in question.lower() for kw in count_keywords)
        
        if is_count_query and parsed.get("type") == "text":
            overview = live_data.get("overview", {})
            count_map = {
                "customer": ("Customer", "customers"),
                "customers": ("Customer", "customers"),
                "supplier": ("Supplier", "suppliers"),
                "suppliers": ("Supplier", "suppliers"),
                "vendor": ("Supplier", "suppliers"),
                "vendors": ("Supplier", "suppliers"),
                "item": ("Item", "items"),
                "items": ("Item", "items"),
                "product": ("Item", "items"),
                "products": ("Item", "items"),
                "employee": ("Employee", "employees"),
                "employees": ("Employee", "employees"),
                "staff": ("Employee", "employees"),
                "invoice": ("Sales Invoice", "sales_invoices"),
                "invoices": ("Sales Invoice", "sales_invoices"),
            }
            
            q_lower = question.lower()
            for kw, (dt_name, dt_key) in count_map.items():
                if kw in q_lower:
                    # Try to get count from overview first (most reliable)
                    count = overview.get(dt_name, 0)
                    
                    # Fallback to list length if overview doesn't have it
                    if not count and dt_key in live_data:
                        count = len(live_data[dt_key])
                    
                    if count:
                        return {
                            "type": "text",
                            "message": f"You have <b>{count} {dt_name.lower()}s</b>."
                        }
        
        # Post-process: Enhance text responses with computed links for specific documents
        if parsed.get("type") == "text" and not parsed.get("link"):
            # Check if response mentions a specific document ID
            message = parsed.get("message", "")
            for pattern, doctype in [
                (r"[\w-]*SINV-[\w-]+", "Sales Invoice"),
                (r"[\w-]*PINV-[\w-]+", "Purchase Invoice"),
                (r"[\w-]*SO-[\w-]+", "Sales Order"),
                (r"[\w-]*PO-[\w-]+", "Purchase Order"),
                (r"[\w-]*QTN-[\w-]+", "Quotation"),
            ]:
                match = re.search(pattern, message)
                if match:
                    doc_id = match.group(0)
                    if frappe.db.exists(doctype, doc_id):
                        # Convert doctype to lowercase with dashes for URL
                        dt_slug = doctype.lower().replace(' ', '-')
                        parsed["link"] = f"/app/{dt_slug}/{doc_id}"
                        parsed["doctype"] = doctype
                        parsed["name"] = doc_id
                        break
        
        return parsed
    
    except requests.exceptions.ConnectionError:
        return {"type": "error", "message": "❌ Cannot connect to internet. Please Check internet."}
    except Exception as e:
        frappe.log_error(f"ask_ai error: {e}")
        return {"type": "error", "message": f"Error: {str(e)[:150]}"}


@frappe.whitelist()
def scan_bill_image(image_data, invoice_type="auto"):
    """
    OCR endpoint for bill/invoice/order scanning.
    invoice_type: "auto", "sales", "purchase", "sales_order", "purchase_order"
    Supports image files (jpeg, png, webp, gif) and PDF files.
    """
    api_key = get_api_key()
    if not api_key:
        return {"type": "error", "message": "API key not configured."}
    
    try:
        # Parse image/pdf data
        if "," in image_data:
            mime_part, b64_part = image_data.split(",", 1)
            mime_type = mime_part.split(":")[1].split(";")[0] if ":" in mime_part else "image/jpeg"
        else:
            b64_part = image_data
            mime_type = "image/jpeg"
        
        # Validate supported MIME types
        supported_mime = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "application/pdf"]
        if mime_type not in supported_mime:
            # Try to treat unknown as jpeg
            mime_type = "image/jpeg"
        
        # OCR prompt - supports all document types
        extraction_prompt = """You are an expert OCR system for SkyERP ERP.
Extract ALL information from this document (bill/invoice/order) and return ONLY valid JSON.

Return this exact JSON structure:
{"document_type": "sales_invoice" or "purchase_invoice" or "sales_order" or "purchase_order",
"party_name": "customer or supplier name",
"invoice_number": "document number or null",
"posting_date": "YYYY-MM-DD or null",
"due_date": "YYYY-MM-DD or null",
"delivery_date": "YYYY-MM-DD or null",
"gstin": "GST number or null",
"items": [{"item_name": "product name", "description": "description", "qty": 1, "rate": 0.00, "uom": "Nos", "amount": 0.00}],
"taxes": [{"tax_type": "CGST/SGST/IGST/VAT", "description": "e.g. CGST 9%", "amount": 0.00}],
"subtotal": 0.00, "tax_total": 0.00, "grand_total": 0.00, "currency": "INR"}

Rules:
- document_type: use "sales_invoice" for invoices/bills where YOU are the seller; "purchase_invoice" for bills from suppliers; "sales_order" for customer orders; "purchase_order" for supplier orders
- Extract EVERY line item with correct qty, rate, amount
- Use YYYY-MM-DD format for all dates
- Use null for missing fields (not empty string)
- Return ONLY valid JSON, absolutely no other text or markdown"""
        
        # Build Gemini request parts - handle both images and PDFs
        if mime_type == "application/pdf":
            parts = [
                {"inline_data": {"mime_type": "application/pdf", "data": b64_part}},
                {"text": extraction_prompt}
            ]
        else:
            parts = [
                {"inline_data": {"mime_type": mime_type, "data": b64_part}},
                {"text": extraction_prompt}
            ]
        
        # Call Gemini Vision
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
            headers={"content-type": "application/json"},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.1},
            },
            timeout=90,
        )
        
        result = response.json()
        if "error" in result:
            return {"type": "error", "message": "Gemini Error: " + str(result["error"].get("message", ""))}
        
        ai_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Parse JSON from response
        extracted = None
        if "```" in ai_text:
            for part in ai_text.split("```"):
                part = part.strip()
                if part.lower().startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{") and part.endswith("}"):
                    try:
                        extracted = json.loads(part)
                        break
                    except:
                        pass
        
        if not extracted:
            try:
                s = ai_text.find("{")
                e = ai_text.rfind("}")
                if s != -1 and e != -1:
                    extracted = json.loads(ai_text[s:e+1])
            except:
                pass
        
        if not extracted:
            return {"type": "error", "message": "Could not read document data. Please try a clearer photo or PDF."}
        
        # Normalize invoice_type from user selection
        # invoice_type from frontend: "auto", "sales", "purchase", "sales_order", "purchase_order"
        # document_type from AI: "sales_invoice", "purchase_invoice", "sales_order", "purchase_order"
        
        # Map user-selected type to final type
        user_type_map = {
            "sales": "sales_invoice",
            "purchase": "purchase_invoice",
            "sales_order": "sales_order",
            "purchase_order": "purchase_order",
        }
        
        if invoice_type != "auto" and invoice_type in user_type_map:
            # User explicitly selected a type - use it
            final_type = user_type_map[invoice_type]
        else:
            # Auto-detect from AI response
            detected = (extracted.get("document_type") or extracted.get("invoice_type") or "").lower()
            # Normalize old format "sales"/"purchase" from AI
            if detected == "sales":
                detected = "sales_invoice"
            elif detected == "purchase":
                detected = "purchase_invoice"
            
            valid_types = ["sales_invoice", "purchase_invoice", "sales_order", "purchase_order"]
            final_type = detected if detected in valid_types else "sales_invoice"
        
        # Create document from extracted data
        from .document_processor import create_invoice_from_extracted
        return create_invoice_from_extracted(final_type, extracted)
    
    except requests.exceptions.ConnectionError:
        return {"type": "error", "message": "❌ Cannot connect to internet."}
    except Exception as e:
        frappe.log_error(f"scan_bill_image error: {e}")
        return {"type": "error", "message": f"Error scanning document: {str(e)[:200]}"}
