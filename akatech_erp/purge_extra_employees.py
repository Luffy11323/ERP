import frappe

from akatech_erp.sync_parties import api_call

LINKED = [
    "Attendance", "Salary Slip", "Leave Application", "Leave Allocation", "Employee Checkin",
    "Expense Claim", "Employee Advance", "Additional Salary", "Salary Structure Assignment",
    "Shift Assignment", "Journal Entry Account", "Payment Entry",
]


def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    res = api_call('resource/Employee?fields=["name"]&limit_page_length=5000')
    rad = {r["name"] for r in res["data"]}
    extra = [n for n in frappe.get_all("Employee", pluck="name") if n not in rad]
    print(f"Local employees not in Radiant: {len(extra)} (prefixes: {sorted({n.rsplit('-', 1)[0] for n in extra})})", flush=True)

    # report linked records
    for dt in LINKED:
        field = "employee" if dt != "Journal Entry Account" and dt != "Payment Entry" else "party"
        try:
            if not frappe.get_meta(dt).has_field(field) and field != "party":
                continue
            n = frappe.db.count(dt, {field: ["in", extra]})
            if n:
                print(f"  linked {dt}: {n}", flush=True)
        except Exception as e:
            print(f"  (skip {dt}: {e})", flush=True)

    deleted = failed = 0
    frappe.flags.in_import = True
    for n in extra:
        try:
            frappe.delete_doc("Employee", n, force=1, ignore_permissions=True, delete_permanently=True)
            frappe.db.commit()
            deleted += 1
        except Exception as e:
            frappe.db.rollback()
            failed += 1
            print(f"Could not delete {n}: {e}", flush=True)
    print(f"Deleted: {deleted}, failed: {failed}", flush=True)


if __name__ == "__main__":
    main()
