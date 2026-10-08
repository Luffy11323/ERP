"""Radiant premium dashboard API.

Read-only endpoints (except check-in) that feed the hero cards injected on the
main workspaces and the Self Service running ledger.  All queries go through
frappe.get_list so standard role / user permissions are always respected.
"""
import frappe
from frappe.utils import flt, getdate, nowdate, get_first_day, get_last_day, today


def _can(doctype):
    try:
        return frappe.has_permission(doctype, "read")
    except Exception:
        return False


def _count(doctype, filters):
    if not _can(doctype):
        return None
    try:
        return len(frappe.get_list(doctype, filters=filters, fields=["name"], limit_page_length=0, as_list=True))
    except Exception:
        return None


def _sum(doctype, field, filters):
    if not _can(doctype):
        return None
    try:
        r = frappe.get_list(doctype, filters=filters, fields=[f"sum({field}) as v"])
        return flt(r[0].v) if r else 0
    except Exception:
        return None


def _month():
    return ["between", [get_first_day(nowdate()), get_last_day(nowdate())]]


# kind: n = count, s = sum(field).  fmt: num | money
def _specs():
    m = _month()
    return {
        "home": {
            "title": "Business Pulse",
            "subtitle": "Live snapshot across Sales, Procurement and Accounts",
            "kpis": [
                ("Open Sales Orders", "Sales Order", "n", None, {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Bill", "To Deliver"]]}, "num", "#6366f1", "sales-order"),
                ("Open Purchase Orders", "Purchase Order", "n", None, {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Bill", "To Receive"]]}, "num", "#0ea5e9", "purchase-order"),
                ("Receivable Outstanding", "Sales Invoice", "s", "outstanding_amount", {"docstatus": 1}, "money", "#10b981", "sales-invoice"),
                ("Payable Outstanding", "Purchase Invoice", "s", "outstanding_amount", {"docstatus": 1}, "money", "#f43f5e", "purchase-invoice"),
            ],
        },
        "procurement": {
            "title": "Procurement Pulse",
            "subtitle": "Purchase orders and pending receipts",
            "kpis": [
                ("POs To Receive", "Purchase Order", "n", None, {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]]}, "num", "#0ea5e9", "purchase-order"),
                ("POs To Bill", "Purchase Order", "n", None, {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Bill"]]}, "num", "#f59e0b", "purchase-order"),
                ("Draft POs", "Purchase Order", "n", None, {"docstatus": 0}, "num", "#94a3b8", "purchase-order"),
                ("PO Value This Month", "Purchase Order", "s", "grand_total", {"docstatus": 1, "transaction_date": m}, "money", "#8b5cf6", "purchase-order"),
            ],
        },
        "sales": {
            "title": "Sales Pulse",
            "subtitle": "Sales orders, deliveries and billing",
            "kpis": [
                ("SOs To Deliver", "Sales Order", "n", None, {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]}, "num", "#6366f1", "sales-order"),
                ("SOs To Bill", "Sales Order", "n", None, {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Bill"]]}, "num", "#f59e0b", "sales-order"),
                ("Draft SOs", "Sales Order", "n", None, {"docstatus": 0}, "num", "#94a3b8", "sales-order"),
                ("SO Value This Month", "Sales Order", "s", "grand_total", {"docstatus": 1, "transaction_date": m}, "money", "#10b981", "sales-order"),
            ],
        },
        "accounts": {
            "title": "Finance Pulse",
            "subtitle": "Receivables, payables and this month's billing",
            "kpis": [
                ("Receivable", "Sales Invoice", "s", "outstanding_amount", {"docstatus": 1}, "money", "#10b981", "sales-invoice"),
                ("Payable", "Purchase Invoice", "s", "outstanding_amount", {"docstatus": 1}, "money", "#f43f5e", "purchase-invoice"),
                ("Overdue Sales Invoices", "Sales Invoice", "n", None, {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", today()]}, "num", "#f59e0b", "sales-invoice"),
                ("Sales Billed This Month", "Sales Invoice", "s", "grand_total", {"docstatus": 1, "posting_date": m}, "money", "#6366f1", "sales-invoice"),
            ],
        },
        "stock": {
            "title": "Inventory Pulse",
            "subtitle": "Receipts, deliveries and requests in flight",
            "kpis": [
                ("Draft Delivery Notes", "Delivery Note", "n", None, {"docstatus": 0}, "num", "#6366f1", "delivery-note"),
                ("Draft Purchase Receipts", "Purchase Receipt", "n", None, {"docstatus": 0}, "num", "#0ea5e9", "purchase-receipt"),
                ("Pending Material Requests", "Material Request", "n", None, {"docstatus": 1, "status": ["in", ["Pending", "Partially Ordered"]]}, "num", "#f59e0b", "material-request"),
                ("Active Items", "Item", "n", None, {"disabled": 0}, "num", "#10b981", "item"),
            ],
        },
        "hr": {
            "title": "People Pulse",
            "subtitle": "Workforce and approvals at a glance",
            "kpis": [
                ("Active Employees", "Employee", "n", None, {"status": "Active"}, "num", "#10b981", "employee"),
                ("Present Today", "Attendance", "n", None, {"docstatus": 1, "attendance_date": today(), "status": "Present"}, "num", "#6366f1", "attendance"),
                ("Absent Today", "Attendance", "n", None, {"docstatus": 1, "attendance_date": today(), "status": "Absent"}, "num", "#f43f5e", "attendance"),
                ("Pending Leave Requests", "Leave Application", "n", None, {"docstatus": 0, "status": "Open"}, "num", "#f59e0b", "leave-application"),
            ],
        },
        "payroll": {
            "title": "Payroll Pulse",
            "subtitle": "This month's salary processing",
            "kpis": [
                ("Slips This Month", "Salary Slip", "n", None, {"docstatus": ["<", 2], "posting_date": m}, "num", "#6366f1", "salary-slip"),
                ("Draft Slips", "Salary Slip", "n", None, {"docstatus": 0}, "num", "#f59e0b", "salary-slip"),
                ("Net Pay This Month", "Salary Slip", "s", "net_pay", {"docstatus": 1, "posting_date": m}, "money", "#10b981", "salary-slip"),
                ("Deductions This Month", "Salary Slip", "s", "total_deduction", {"docstatus": 1, "posting_date": m}, "money", "#f43f5e", "salary-slip"),
            ],
        },
        "crm": {
            "title": "CRM Pulse",
            "subtitle": "Pipeline health",
            "kpis": [
                ("Open Leads", "Lead", "n", None, {"status": ["in", ["Lead", "Open", "Replied"]]}, "num", "#6366f1", "lead"),
                ("Open Opportunities", "Opportunity", "n", None, {"status": "Open"}, "num", "#0ea5e9", "opportunity"),
                ("Quotations This Month", "Quotation", "n", None, {"docstatus": 1, "transaction_date": m}, "num", "#f59e0b", "quotation"),
                ("Customers", "Customer", "n", None, {"disabled": 0}, "num", "#10b981", "customer"),
            ],
        },
        "projects": {
            "title": "Projects Pulse",
            "subtitle": "Delivery tracker",
            "kpis": [
                ("Open Projects", "Project", "n", None, {"status": "Open"}, "num", "#6366f1", "project"),
                ("Open Tasks", "Task", "n", None, {"status": ["in", ["Open", "Working", "Pending Review"]]}, "num", "#f59e0b", "task"),
                ("Overdue Tasks", "Task", "n", None, {"status": ["not in", ["Completed", "Cancelled"]], "exp_end_date": ["<", today()]}, "num", "#f43f5e", "task"),
                ("Completed Tasks", "Task", "n", None, {"status": "Completed"}, "num", "#10b981", "task"),
            ],
        },
        "assets": {
            "title": "Assets Pulse",
            "subtitle": "Fixed asset overview",
            "kpis": [
                ("Total Assets", "Asset", "n", None, {"docstatus": 1}, "num", "#6366f1", "asset"),
                ("Draft Assets", "Asset", "n", None, {"docstatus": 0}, "num", "#94a3b8", "asset"),
                ("Asset Value", "Asset", "s", "gross_purchase_amount", {"docstatus": 1}, "money", "#10b981", "asset"),
                ("Maintenance Logs", "Asset Maintenance Log", "n", None, {"maintenance_status": ["in", ["Planned", "Overdue"]]}, "num", "#f59e0b", "asset-maintenance-log"),
            ],
        },
        "manufacturing": {
            "title": "Production Pulse",
            "subtitle": "Work orders and BOMs",
            "kpis": [
                ("Open Work Orders", "Work Order", "n", None, {"docstatus": 1, "status": ["in", ["Not Started", "In Process"]]}, "num", "#6366f1", "work-order"),
                ("Active BOMs", "BOM", "n", None, {"docstatus": 1, "is_active": 1}, "num", "#0ea5e9", "bom"),
                ("Draft Work Orders", "Work Order", "n", None, {"docstatus": 0}, "num", "#94a3b8", "work-order"),
                ("Completed Orders", "Work Order", "n", None, {"docstatus": 1, "status": "Completed"}, "num", "#10b981", "work-order"),
            ],
        },
    }


WORKSPACE_MAP = {
    "procurement-department": "procurement", "buying": "procurement", "aka-buying": "procurement",
    "sales-department": "sales", "selling": "sales", "after-sales-service": "sales", "aka-selling": "sales",
    "accounts": "accounts", "accounting": "accounts", "financial-reports": "accounts",
    "payables": "accounts", "receivables": "accounts", "kodessy-accounting": "accounts", "kodessy-accounts": "accounts",
    "hr": "hr", "aka-hr": "hr", "rm-hr": "hr", "leaves": "hr", "recruitment": "hr",
    "performance": "hr", "shift-&-attendance": "hr", "employee-lifecycle": "hr",
    "payroll": "payroll", "aka-payroll": "payroll", "rm-payroll": "payroll",
    "salary-payout": "payroll", "tax-&-benefits": "payroll",
    "projects": "projects"
}


def _is_privileged():
    return frappe.session.user == "Administrator"


def _employee(employee=None):
    fields = ["name", "employee_name", "company", "department", "designation"]
    if employee and _is_privileged():
        return frappe.db.get_value("Employee", employee, fields, as_dict=True)
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, fields, as_dict=True)


@frappe.whitelist()
def get_employee_options():
    """Employees a privileged user can preview Self Service as."""
    if not _is_privileged():
        return []
    return frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"],
                          order_by="employee_name asc", limit_page_length=1000)


@frappe.whitelist()
def get_card(slug, employee=None):
    """Return hero card payload for a workspace slug (or None)."""
    if not frappe.conf.get("akatech_premium_ui", 1):
        return None
    slug = (slug or "").lower()

    if slug in ["employee-self-services", "self-service", "home"]:
        emp = _employee(employee)
        return {"type": "self", "title": "My Workspace", "employee": emp,
                "privileged": _is_privileged(), "user": frappe.utils.get_fullname(),
                "checkin": _last_checkin(emp.name) if emp else None,
                "kpis": _self_kpis(emp) if emp else []}

    key = WORKSPACE_MAP.get(slug)
    if not key:
        return None
    spec = _specs().get(key)
    if not spec:
        return None
    kpis = []
    for label, dt, kind, field, filters, fmt, color, route in spec["kpis"]:
        val = _count(dt, filters) if kind == "n" else _sum(dt, field, filters)
        if val is None:
            continue
        kpis.append({"label": label, "value": val, "fmt": fmt, "color": color, "route": route})
    if not kpis:
        return None
    return {"type": "kpi", "title": spec["title"], "subtitle": spec["subtitle"], "kpis": kpis,
            "user": frappe.utils.get_fullname()}


def _self_kpis(emp):
    out = []
    leaves = frappe.db.sql(
        """select sum(total_leaves_allocated) from `tabLeave Allocation`
           where employee=%s and docstatus=1 and %s between from_date and to_date""",
        (emp.name, today()))
    out.append({"label": "Leaves Allocated", "value": flt(leaves[0][0]) if leaves else 0, "fmt": "num", "color": "#6366f1"})
    last = frappe.db.get_value("Salary Slip", {"employee": emp.name, "docstatus": 1},
                               ["net_pay", "end_date"], order_by="end_date desc", as_dict=True)
    out.append({"label": "Last Net Pay", "value": flt(last.net_pay) if last else 0, "fmt": "money", "color": "#10b981"})
    adv = frappe.db.sql(
        """select sum(advance_amount - claimed_amount - return_amount) from `tabEmployee Advance`
           where employee=%s and docstatus=1""", (emp.name,))
    out.append({"label": "Advance Outstanding", "value": flt(adv[0][0]) if adv else 0, "fmt": "money", "color": "#f59e0b"})
    ec = frappe.db.sql(
        """select sum(total_sanctioned_amount) from `tabExpense Claim`
           where employee=%s and docstatus=1 and status='Unpaid'""", (emp.name,))
    out.append({"label": "Claims Pending Payment", "value": flt(ec[0][0]) if ec else 0, "fmt": "money", "color": "#f43f5e"})
    return out


def _last_checkin(employee):
    row = frappe.db.get_value("Employee Checkin", {"employee": employee},
                              ["log_type", "time"], order_by="time desc", as_dict=True)
    if row and getdate(row.time) == getdate(today()):
        return {"log_type": row.log_type, "time": str(row.time)}
    return None


@frappe.whitelist()
def toggle_checkin(employee=None):
    """Create an IN/OUT Employee Checkin for the logged-in employee."""
    emp = _employee(employee)
    if not emp:
        frappe.throw("No active Employee is linked to your user.")
    last = _last_checkin(emp.name)
    log_type = "OUT" if last and last["log_type"] == "IN" else "IN"
    doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp.name,
                          "log_type": log_type, "time": frappe.utils.now_datetime()})
    doc.insert()
    return {"log_type": log_type, "time": str(doc.time)}


@frappe.whitelist()
def get_my_ledger(from_date=None, to_date=None, employee=None):
    """Running ledger for the logged-in employee only.

    Entries: salary slips (with full earning/deduction breakdown), employee advances
    and expense claims. 'received' is money paid out to the employee; 'running'
    is the cumulative total received in chronological order.
    """
    emp = _employee(employee)
    if not emp:
        frappe.throw("No active Employee is linked to your user.")
    from_date = from_date or frappe.utils.add_months(today(), -12)
    to_date = to_date or today()
    rows = []

    slips = frappe.get_all("Salary Slip", filters={"employee": emp.name, "docstatus": 1,
                           "end_date": ["between", [from_date, to_date]]},
                           fields=["name", "start_date", "end_date", "posting_date", "gross_pay",
                                   "total_deduction", "net_pay"], order_by="end_date asc")
    for s in slips:
        det = frappe.get_all("Salary Detail", filters={"parent": s.name},
                             fields=["parentfield", "salary_component", "amount"], order_by="idx asc")
        rows.append({
            "date": str(s.end_date), "type": "Salary", "ref": s.name, "doctype": "Salary Slip",
            "desc": f"Salary {s.start_date} to {s.end_date}",
            "gross": flt(s.gross_pay), "deduction": flt(s.total_deduction), "received": flt(s.net_pay),
            "earnings": [{"c": d.salary_component, "a": flt(d.amount)} for d in det if d.parentfield == "earnings"],
            "deductions": [{"c": d.salary_component, "a": flt(d.amount)} for d in det if d.parentfield == "deductions"],
        })

    for a in frappe.get_all("Employee Advance", filters={"employee": emp.name, "docstatus": 1,
                            "posting_date": ["between", [from_date, to_date]]},
                            fields=["name", "posting_date", "purpose", "advance_amount", "paid_amount",
                                    "claimed_amount", "return_amount", "status"]):
        rows.append({
            "date": str(a.posting_date), "type": "Advance", "ref": a.name, "doctype": "Employee Advance",
            "desc": f"{a.purpose or 'Advance'} ({a.status})",
            "gross": 0, "deduction": 0, "received": flt(a.paid_amount),
            "extra": {"Requested": flt(a.advance_amount), "Claimed": flt(a.claimed_amount),
                      "Returned": flt(a.return_amount),
                      "Outstanding": flt(a.advance_amount) - flt(a.claimed_amount) - flt(a.return_amount)},
        })

    for c in frappe.get_all("Expense Claim", filters={"employee": emp.name, "docstatus": 1,
                            "posting_date": ["between", [from_date, to_date]]},
                            fields=["name", "posting_date", "total_claimed_amount", "total_sanctioned_amount",
                                    "total_amount_reimbursed", "status"]):
        det = frappe.get_all("Expense Claim Detail", filters={"parent": c.name},
                             fields=["expense_type", "sanctioned_amount"])
        rows.append({
            "date": str(c.posting_date), "type": "Expense", "ref": c.name, "doctype": "Expense Claim",
            "desc": f"Expense claim ({c.status})",
            "gross": 0, "deduction": 0, "received": flt(c.total_amount_reimbursed),
            "extra": {"Claimed": flt(c.total_claimed_amount), "Sanctioned": flt(c.total_sanctioned_amount)},
            "earnings": [{"c": d.expense_type, "a": flt(d.sanctioned_amount)} for d in det],
        })

    rows.sort(key=lambda r: (r["date"], r["ref"]))
    running = 0
    for r in rows:
        running += r["received"]
        r["running"] = running

    return {
        "employee": emp, "from": str(from_date), "to": str(to_date), "rows": rows,
        "totals": {
            "gross": sum(r["gross"] for r in rows if r["type"] == "Salary"),
            "deduction": sum(r["deduction"] for r in rows if r["type"] == "Salary"),
            "salary": sum(r["received"] for r in rows if r["type"] == "Salary"),
            "advance": sum(r["received"] for r in rows if r["type"] == "Advance"),
            "expense": sum(r["received"] for r in rows if r["type"] == "Expense"),
            "total": running,
        },
    }


def boot_session(bootinfo):
    bootinfo.akatech_premium = 1 if frappe.conf.get("akatech_premium_ui", 1) else 0
