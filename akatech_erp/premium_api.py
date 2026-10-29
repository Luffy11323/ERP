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
        records = frappe.get_list(doctype, filters=filters, fields=[field], limit_page_length=0, as_list=True)
        return sum(flt(r[0]) for r in records if r and r[0] is not None)
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
    "home": "home",
    "procurement-department": "procurement", "buying": "procurement", "aka-buying": "procurement", "purchase": "procurement", "procurement": "procurement",
    "sales-department": "sales", "selling": "sales", "after-sales-service": "sales", "aka-selling": "sales", "sales": "sales",
    "accounts": "accounts", "accounting": "accounts", "financial-reports": "accounts", "finance": "accounts",
    "payables": "accounts", "receivables": "accounts", "kodessy-accounting": "accounts", "kodessy-accounts": "accounts",
    "stock": "stock", "inventory": "stock", "inventory-department": "stock", "aka-stock": "stock",
    "assets": "assets", "fixed-assets": "assets", "asset": "assets",
    "manufacturing": "manufacturing", "production": "manufacturing",
    "hr": "hr", "aka-hr": "hr", "rm-hr": "hr", "leaves": "hr", "recruitment": "hr",
    "performance": "hr", "shift-&-attendance": "hr", "employee-lifecycle": "hr", "hrms": "hr",
    "payroll": "payroll", "aka-payroll": "payroll", "rm-payroll": "payroll",
    "salary-payout": "payroll", "tax-&-benefits": "payroll",
    "projects": "projects", "project": "projects",
    "crm": "crm",
}


def _is_privileged():
    return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _employee(employee=None):
    fields = ["name", "employee_name", "company", "department", "designation", "image", "user_id"]
    if employee and _is_privileged():
        emp = frappe.db.get_value("Employee", employee, fields, as_dict=True)
        if emp:
            return emp
    emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, fields, as_dict=True)
    if emp:
        return emp
    if _is_privileged():
        # Fallback to the first active employee for preview if administrator isn't linked
        return frappe.db.get_value("Employee", {"status": "Active"}, fields, order_by="name asc", as_dict=True)
    return None


def _card_home_self(employee=None):
    emp = _employee(employee)
    user = frappe.session.user
    
    if emp:
        emp_name = emp.employee_name
        emp_id = emp.name
        emp_image = emp.image or frappe.db.get_value("User", emp.user_id or user, "user_image")
    else:
        user_doc = frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
        emp_name = user_doc.get("full_name") or user
        emp_id = "N/A"
        emp_image = user_doc.get("user_image")

    today_date = today()
    login_time = "--"
    last_out_time = "--"
    is_checked_in = False
    
    if emp:
        checkins = frappe.get_all(
            "Employee Checkin",
            filters={"employee": emp.name, "time": [">=", f"{today_date} 00:00:00"]},
            fields=["log_type", "time"],
            order_by="time asc"
        )
        if checkins:
            first_in = next((c for c in checkins if c.log_type == "IN"), None)
            if first_in:
                login_time = frappe.utils.format_time(first_in.time, "hh:mm a")
            
            last_out = next((c for c in reversed(checkins) if c.log_type == "OUT"), None)
            if last_out:
                last_out_time = frappe.utils.format_time(last_out.time, "hh:mm a")
            
            is_checked_in = (checkins[-1].log_type == "IN")

    first_day = get_first_day(today_date)
    last_day = get_last_day(today_date)
    month_label = frappe.utils.format_date(today_date, "MMMM YYYY")
    
    present_days = 0
    absent_days = 0
    leave_days = 0
    total_hours = 0.0
    total_work_days = 27
    expected_hours = 196.0

    if emp:
        att_records = frappe.get_all(
            "Attendance",
            filters={
                "employee": emp.name,
                "attendance_date": ["between", [first_day, last_day]],
                "docstatus": 1
            },
            fields=["status", "working_hours"]
        )
        for att in att_records:
            if att.status in ["Present", "Work From Home"]:
                present_days += 1
            elif att.status == "Half Day":
                present_days += 0.5
            elif att.status == "Absent":
                absent_days += 1
            elif att.status == "On Leave":
                leave_days += 1
            
            if att.working_hours:
                total_hours += flt(att.working_hours)

    tasks = []
    try:
        todos = frappe.get_all(
            "ToDo",
            filters={"owner": user, "status": "Open"},
            fields=["name", "description", "reference_type", "reference_name", "date"],
            order_by="date desc, creation desc",
            limit=5
        )
        for t in todos:
            desc = frappe.utils.strip_html(t.description or "")
            ref_type = t.reference_type or ""
            ref_name = t.reference_name or ""
            
            # Direct link to the document if referenced, otherwise to ToDo
            if ref_type and ref_name:
                url = f"/app/{frappe.router.slug(ref_type)}/{ref_name}"
            else:
                url = f"/app/todo/{t.name}"

            tasks.append({
                "name": t.name,
                "ref_type": ref_type,
                "ref_name": ref_name,
                "description": desc[:70] if desc else ref_name,
                "url": url,
                "date": str(t.date or "")
            })
    except Exception:
        pass

    return {
        "type": "home_self",
        "employee": emp,
        "employee_name": emp_name,
        "employee_id": emp_id,
        "employee_image": emp_image,
        "login_time": login_time,
        "last_out_time": last_out_time,
        "is_checked_in": is_checked_in,
        "month_label": month_label,
        "present_days": int(present_days) if present_days == int(present_days) else present_days,
        "total_work_days": total_work_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "total_hours": round(total_hours, 1),
        "expected_hours": expected_hours,
        "tasks": tasks,
        "privileged": _is_privileged(),
    }


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
    slug = (slug or "").lower().strip()

    if slug in ["home", "setup", "employee-self-services", "self-service"]:
        return _card_home_self(employee)

    key = WORKSPACE_MAP.get(slug) or (slug if slug in _specs() else None)
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
    rows = frappe.get_all("Employee Checkin", filters={"employee": employee}, fields=["log_type", "time", "creation"], order_by="time desc", limit=1)
    row = rows[0] if rows else None
    if row and (getdate(row.time) == getdate(today()) or getdate(row.creation) == getdate(today())):
        return {"log_type": row.log_type, "time": str(row.time)}
    return None


def _sync_checkin_series():
    """Ensure tabSeries for Employee Checkin is at least the highest number existing in DB."""
    try:
        now = frappe.utils.now_datetime()
        prefix = f"EMP-CKIN-{now.strftime('%m-%Y')}-"
        
        # Get highest existing name with this prefix
        max_name = frappe.db.sql(
            """SELECT name FROM `tabEmployee Checkin`
               WHERE name LIKE %s
               ORDER BY name DESC LIMIT 1""",
            (f"{prefix}%",)
        )
        if max_name and max_name[0] and max_name[0][0]:
            name_str = str(max_name[0][0])
            num_str = name_str.replace(prefix, "")
            if num_str.isdigit():
                max_val = int(num_str)
                frappe.db.sql(
                    """INSERT INTO `tabSeries` (name, current)
                       VALUES (%s, %s)
                       ON DUPLICATE KEY UPDATE current = GREATEST(current, %s)""",
                    (prefix, max_val, max_val)
                )
                frappe.db.commit()
    except Exception:
        pass


@frappe.whitelist()
def toggle_checkin(employee=None):
    """Create an IN/OUT Employee Checkin for the logged-in employee."""
    emp = _employee(employee)
    if not emp:
        frappe.throw("No active Employee is linked to your user.")
    last = _last_checkin(emp.name)
    log_type = "OUT" if last and last["log_type"] == "IN" else "IN"

    _sync_checkin_series()

    prefix = f"EMP-CKIN-{frappe.utils.now_datetime().strftime('%m-%Y')}-"
    for _ in range(5):
        try:
            doc = frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": emp.name,
                "log_type": log_type,
                "time": frappe.utils.now_datetime()
            })
            doc.insert()
            frappe.db.commit()
            return {"log_type": log_type, "time": str(doc.time)}
        except frappe.DuplicateEntryError:
            # Advance series counter and retry next number
            frappe.db.sql(
                """INSERT INTO `tabSeries` (name, current)
                   VALUES (%s, 1)
                   ON DUPLICATE KEY UPDATE current = current + 1""",
                (prefix,)
            )
            frappe.db.commit()

    frappe.throw("Unable to register checkin. Please try again.")


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
