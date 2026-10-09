import os
import json
import re
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import frappe
from akatech_erp.sync_parties import api_call, clean_doc

# ──────────────────────────────────────────────────────────────────────────────
# FULL doctype list derived from doctypes.txt (all non-zero-count, non-child,
# non-virtual doctypes) in dependency order.
# Child tables are fetched automatically via doc.get_all_children() when the
# parent document is synced, so we do NOT list them separately.
# ──────────────────────────────────────────────────────────────────────────────
DOCTYPES = [
    # ── Core / Metadata ──────────────────────────────────────────────────────
    "Role", "Module Def", "Role Profile", "Module Profile",
    "Workspace", "Workflow", "Workflow State", "Workflow Action Master",
    "Server Script", "Client Script", "Print Format",
    "Custom Field", "Property Setter", "Custom DocPerm",
    "Document Naming Rule", "Scheduled Job Type",
    "Number Card", "Dashboard", "Dashboard Chart", "Dashboard Chart Source",
    "Form Tour", "Report", "Page",
    "Notification", "Email Template",
    "Web Template", "Web Form",
    "Tag", "Tag Link",

    # ── Users & Permissions ──────────────────────────────────────────────────
    "User", "User Permission", "User Type",
    "DocShare", "Document Share Key",

    # ── Company & Setup ──────────────────────────────────────────────────────
    "Company", "Fiscal Year",
    "Country", "Currency", "Language", "Salutation",

    # ── Contacts & Addresses ─────────────────────────────────────────────────
    "Address", "Contact", "Address Template",

    # ── Accounting Masters ───────────────────────────────────────────────────
    "Account", "Cost Center", "Finance Book",
    "Payment Term", "Payment Terms Template",
    "Tax Category", "Tax Rule",
    "Accounting Period",
    "Accounting Dimension",
    "Sales Taxes and Charges Template",
    "Purchase Taxes and Charges Template",
    "Item Tax Template",
    "Mode of Payment",
    "Bank", "Bank Account", "Bank Account Type",
    "Currency Exchange",
    "Price List",
    "Party Type",
    "Income Tax Slab", "Payroll Period",

    # ── HR Masters ───────────────────────────────────────────────────────────
    "Department", "Branch", "Designation",
    "Employee Grade", "Employment Type",
    "Gender",
    "Holiday List",
    "Leave Type", "Leave Period", "Leave Policy",
    "Shift Type", "Shift Location",
    "Expense Claim Type",
    "Job Applicant Source", "Offer Term",
    "Sales Stage",
    "Employee", "Employee Health Insurance",
    "Appraisal Template", "Appraisal Cycle",
    "KRA",
    "Vehicle Service Item",
    "Employee Feedback Criteria",
    "Skill",

    # ── Payroll Masters ──────────────────────────────────────────────────────
    "Salary Component", "Salary Structure", "Salary Component Group",

    # ── Stock Masters ────────────────────────────────────────────────────────
    "UOM", "UOM Category", "UOM Conversion Factor",
    "Warehouse", "Warehouse Type",
    "Item Group", "Brand", "Manufacturer",
    "Item", "Item Attribute", "Item Price",
    "Serial No", "Batch",
    "Stock Entry Type",

    # ── Selling & Buying Masters ─────────────────────────────────────────────
    "Customer Group", "Customer",
    "Supplier Group", "Supplier",
    "Sales Person", "Territory",
    "Industry Type", "Market Segment",
    "Incoterm",
    "Terms and Conditions",
    "Sales Partner Type",
    "Supplier Scorecard Variable", "Supplier Scorecard Standing",
    "Lead Source",
    "Party Link",
    "Item Manufacturer",

    # ── Project & Tasks ──────────────────────────────────────────────────────
    "Project Type", "Task Type", "Activity Type",
    "Project",

    # ── Assets ───────────────────────────────────────────────────────────────
    "Asset Category",
    "Location",
    "Asset", "Asset Repair", "Asset Value Adjustment",
    "Asset Depreciation Schedule",
    "Asset Movement",
    "Asset Maintenance Team",

    # ── Custom / RM Doctypes ─────────────────────────────────────────────────
    "Performance Guarantee Type",
    "Performance Guarantee",
    "LC Register",
    "Item Category",
    "Internal Store Request",
    "Internal Store Monthly Register",
    "Bid SLA Preparation",
    "Bid Evaluation",
    "RM HR Policy",
    "HR Policy Type",
    "Salary Structure Assignment",

    # ── HR Transactions ──────────────────────────────────────────────────────
    "Employee Advance",
    "Additional Salary",
    "Expense Claim",
    "Leave Allocation",
    "Leave Application",
    "Leave Ledger Entry",
    "Leave Policy Assignment",
    "Shift Assignment",
    "Attendance Request",
    "Attendance",
    "Employee Checkin",
    "Appraisal",
    "Employee Onboarding",
    "Employee Promotion",
    "Employee Performance Feedback",
    "Job Applicant", "Job Offer",
    "Staffing Plan",
    "Interview", "Interview Round", "Interview Type",

    # ── Payroll Transactions ─────────────────────────────────────────────────
    "Payroll Entry",
    "Salary Slip",

    # ── Quality & Stock Transactions ─────────────────────────────────────────
    "Quality Inspection Template", "Quality Inspection Parameter",
    "Quality Inspection",
    "Stock Reconciliation",
    "Stock Entry",
    "Serial and Batch Bundle",
    "Landed Cost Voucher",
    "Repost Item Valuation",

    # ── Buying Transactions ──────────────────────────────────────────────────
    "Material Request",
    "Purchase Order",
    "Purchase Receipt",
    "Purchase Invoice",

    # ── Selling Transactions ─────────────────────────────────────────────────
    "Quotation",
    "Sales Order",
    "Delivery Note",
    "Sales Invoice",

    # ── Payment & Finance Transactions ───────────────────────────────────────
    "Payment Terms Template",
    "Payment Request",
    "Payment Entry",
    "Journal Entry",
    "Journal Entry Template",
    "Process Deferred Accounting",
    "Process Subscription",
    "Period Closing Voucher",
    "Repost Accounting Ledger",
    "Unreconcile Payment",
    "Bank Transaction",
    "Process Payment Reconciliation",
    "Account Closing Balance",
    "Process Loan Classification",
    "Process Loan Interest Accrual",

    # ── System Ledgers (last — raw ledger entries) ───────────────────────────
    "Stock Ledger Entry",
    "GL Entry",
    "Payment Ledger Entry",
    "Advance Payment Ledger Entry",

    # ── Misc ─────────────────────────────────────────────────────────────────
    "ToDo",
    "Note",
    "Auto Email Report",
    "Newsletter",
    "Email Group", "Email Group Member",
    "Email Account",
    "Error Log",
    "Deleted Document",
    "Patch Log",
    "Data Import",
    "Prepared Report",
    "Print Style", "Print Heading", "Letter Head",
    "Cheque Print Template",
    "Language",
    "Translation",
    "Domain",
    "Email Domain",
    "Energy Point Rule",
    "Job Opening", "Job Requisition",
    "Kanban Board",
    "List View Settings",
    "List Filter",
    "Issue", "Issue Priority",
    "Lead",
    "Appointment",
    "Opportunity Type",
    "Web Page", "Website Theme",
    "DocType",
    "Driver",
]

SITE = "akatech.local"
MAX_WORKERS = 2
CHUNK_SIZE = 50
MAX_RETRIES = 3

def get_progress_file():
    return frappe.get_site_path("private", "files", "sync_progress.json")

def load_progress():
    path = get_progress_file()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_progress(prog):
    path = get_progress_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(prog, f)

def log_ui(title, message):
    print(f"[{title}] {message}", flush=True)
    try:
        frappe.log_error(message, title)
    except Exception:
        pass


def alter_table_add_col(doctype, col):
    """Add a missing column to a doctype's table. Ignores duplicate errors."""
    try:
        frappe.db.sql(f"ALTER TABLE `tab{doctype}` ADD COLUMN `{col}` TEXT")
        frappe.db.commit()
        return True
    except Exception as e:
        msg = str(e)
        if "Duplicate column name" in msg:
            return True   # already there
        raise


def sync_doc(doctype, name, site, _retry=0):
    try:
        frappe.init(site=site)
        frappe.connect()
        frappe.flags.in_import = True

        if frappe.db.exists(doctype, name):
            return doctype, name, True, "Exists"

        doc_res = api_call(
            f"resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(str(name))}"
        )
        if not doc_res or "data" not in doc_res:
            return doctype, name, False, "Failed to fetch"

        d = clean_doc(doc_res["data"])
        d["doctype"] = doctype

        doc = frappe.get_doc(d)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_validate = True
        doc.name = name

        doc.db_insert()
        for child in doc.get_all_children():
            child.db_insert()

        frappe.db.commit()
        return doctype, name, True, "Inserted"

    except Exception as e:
        frappe.db.rollback()
        err = str(e)

        if _retry >= MAX_RETRIES:
            return doctype, name, False, f"[MaxRetry] {err[:150]}"

        if "Unknown column" in err and "in 'INSERT INTO'" in err:
            m = re.search(r"Unknown column '(.+?)'", err)
            if m:
                col = m.group(1)
                try:
                    alter_table_add_col(doctype, col)
                except Exception:
                    pass
                return sync_doc(doctype, name, site, _retry + 1)

        if "Deadlock found" in err or "Lock wait timeout" in err:
            time.sleep(0.2 * (_retry + 1))
            return sync_doc(doctype, name, site, _retry + 1)

        return doctype, name, False, err[:150]
    finally:
        frappe.destroy()

def sync_doctype_bulk(doctype, progress):
    if doctype not in progress:
        progress[doctype] = {"done": []}
    done = set(progress[doctype]["done"])

    limit_length = 2000
    limit_start = 0
    total_found = 0
    
    while True:
        url = f'resource/{urllib.parse.quote(doctype)}?fields=["*"]&limit_start={limit_start}&limit_page_length={limit_length}'
        res = api_call(url)
        if not res or "data" not in res or not res["data"]:
            break
            
        data = res["data"]
        total_found += len(data)
        
        frappe.init(site=SITE)
        frappe.connect()
        frappe.flags.in_import = True
        
        successes = []
        for d in data:
            name = d.get("name")
            if not name or name in done:
                continue
                
            try:
                if frappe.db.exists(doctype, name):
                    successes.append(name)
                    continue
                    
                cd = clean_doc(d)
                cd["doctype"] = doctype
                
                doc = frappe.get_doc(cd)
                doc.flags.ignore_permissions = True
                doc.flags.ignore_links = True
                doc.flags.ignore_mandatory = True
                doc.flags.ignore_validate = True
                doc.name = name
                
                try:
                    doc.db_insert()
                    successes.append(name)
                except Exception as e:
                    err = str(e)
                    if "Unknown column" in err:
                        m = re.search(r"Unknown column '(.+?)'", err)
                        if m:
                            col = m.group(1)
                            try:
                                alter_table_add_col(doctype, col)
                                doc.db_insert()
                                successes.append(name)
                            except: pass
                    else:
                        print(f"  ERR {name}: {err[:150]}", flush=True)
                        
            except Exception as e:
                print(f"  ERR {name}: {str(e)[:150]}", flush=True)
                
        frappe.db.commit()
        frappe.destroy()
        
        if successes:
            progress[doctype]["done"].extend(successes)
            save_progress(progress)
            
        done.update(successes)
        print(f"  Progress {doctype}: {len(progress[doctype]['done'])} records synced via bulk", flush=True)
        
        if len(data) < limit_length:
            break
            
        limit_start += limit_length


def sync_doctype(doctype, progress):
    frappe.init(site=SITE)
    frappe.connect()

    print(f"\n--- Syncing {doctype} ---", flush=True)
    
    # Check if doctype has child tables locally to determine safe bulk mode
    has_children = False
    try:
        meta = frappe.get_meta(doctype)
        has_children = len(meta.get_table_fields()) > 0
    except Exception:
        has_children = True
        
    frappe.destroy()

    if not has_children:
        print(f"  [BULK MODE] {doctype} has no child tables. Speeding up via bulk fetching!", flush=True)
        sync_doctype_bulk(doctype, progress)
        return

    frappe.init(site=SITE)
    frappe.connect()
    res = api_call(
        f'resource/{urllib.parse.quote(doctype)}?fields=["name"]&limit_page_length=500000'
    )
    frappe.destroy()

    if not res or "data" not in res:
        print(f"  Could not fetch list for {doctype}", flush=True)
        return

    names = [r["name"] for r in res["data"]]
    total = len(names)
    print(f"  Total in Radiant: {total}", flush=True)

    if doctype not in progress:
        progress[doctype] = {"done": []}

    done = set(progress[doctype]["done"])
    pending = [n for n in names if n not in done]
    print(f"  Pending: {len(pending)}", flush=True)

    if not pending:
        return

    for i in range(0, len(pending), CHUNK_SIZE):
        chunk = pending[i: i + CHUNK_SIZE]
        successes = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(sync_doc, doctype, name, SITE): name
                for name in chunk
            }
            for future in as_completed(futures):
                dt, nm, ok, msg = future.result()
                if ok:
                    successes.append(nm)
                else:
                    print(f"  ERR {nm}: {msg}", flush=True)

        if successes:
            progress[doctype]["done"].extend(successes)
            save_progress(progress)

        print(
            f"  Progress {doctype}: {len(progress[doctype]['done'])} / {total}",
            flush=True,
        )


def main():
    frappe.init(site=SITE)
    progress = load_progress()
    frappe.destroy()

    for dt in DOCTYPES:
        try:
            sync_doctype(dt, progress)
        except Exception as e:
            print(f"FATAL ERROR syncing {dt}: {e}", flush=True)

    print("\n\n=== MIGRATION COMPLETE ===", flush=True)


def sync_updates(doctype):
    print(f"\n--- Checking Updates for {doctype} ---", flush=True)
    res = api_call(f'resource/{urllib.parse.quote(doctype)}?fields=["name","modified"]&limit_page_length=500000')
    if not res or 'data' not in res:
        return

    data = res['data']
    to_sync = []
    for d in data:
        name = d['name']
        remote_modified = d.get('modified')
        local_modified = frappe.db.get_value(doctype, name, 'modified')
        
        if not local_modified or (remote_modified and str(remote_modified) > str(local_modified)):
            to_sync.append(name)

    if not to_sync:
        print(f"  No updates found for {doctype}.", flush=True)
        return

    print(f"  Found {len(to_sync)} updates/new records for {doctype}. Syncing now...", flush=True)

    site = frappe.local.site if hasattr(frappe.local, 'site') and frappe.local.site else SITE
    successes = []
    for i in range(0, len(to_sync), CHUNK_SIZE):
        chunk = to_sync[i : i + CHUNK_SIZE]
        for name in chunk:
            dt, nm, ok, msg = sync_doc(doctype, name, site)
            if ok:
                successes.append(nm)
            else:
                print(f"  ERR {nm}: {msg}", flush=True)
                    
    print(f"  Successfully synced {len(successes)} / {len(to_sync)} records.", flush=True)

@frappe.whitelist()
def run_scheduled_sync():
    """Background Hook Entry Point (Monthly)"""
    frappe.enqueue("akatech_erp.sync_all_parallel.execute_updates", queue="long", timeout=7200)

def execute_updates():
    """Runs without frappe.init() because it is already inside a Frappe worker"""
    log_ui("Sync Started", "Started monthly background database sync.")
    for dt in DOCTYPES:
        try:
            sync_updates(dt)
        except Exception as e:
            log_ui("Sync Error", f"FATAL ERROR checking updates for {dt}: {e}")
    log_ui("Sync Complete", "Scheduled update sync successfully completed.")

if __name__ == "__main__":
    main()
