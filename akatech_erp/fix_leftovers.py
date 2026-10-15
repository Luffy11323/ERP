import frappe
import urllib.parse

from akatech_erp.sync_parties import api_call, clean_doc

COMPANY = "Radiant Medical (Pvt.) Ltd."


def aka(name):
    if not name:
        return None
    if name.lower().startswith("rm "):
        return "AKA " + name[3:]
    return name


def fix_module_defs():
    for rm in ["Rm Erp", "RM Payroll", "Rm Stock", "RM Selling", "RM HR", "RM Buying"]:
        new = aka(rm)
        if frappe.db.exists("Module Def", new):
            continue
        doc = frappe.get_doc({"doctype": "Module Def", "module_name": new, "app_name": "akatech_erp", "custom": 1})
        doc.name = new
        doc.db_insert()
        print(f"Inserted Module Def {new}", flush=True)
    frappe.db.commit()


def fix_customer():
    name = "RM-CUS-0359"
    owner = frappe.db.get_value("Customer", {"represents_company": COMPANY}, "name")
    if frappe.db.exists("Customer", name):
        return
    if owner and owner != name:
        print(f"Renaming Customer {owner} -> {name} (same record in Radiant)", flush=True)
        frappe.rename_doc("Customer", owner, name, force=True)
        frappe.db.commit()
        return
    if owner:
        return
    res = api_call(f"resource/Customer/{urllib.parse.quote(name)}")
    if not res or "data" not in res:
        return
    d = clean_doc(res["data"])
    d["doctype"] = "Customer"
    doc = frappe.get_doc(d)
    for f in ("ignore_permissions", "ignore_mandatory", "ignore_links", "ignore_validate"):
        setattr(doc.flags, f, True)
    doc.insert(set_name=name)
    frappe.db.commit()
    print(f"Inserted Customer {name}", flush=True)


def fix_users():
    """Fixes users that failed due to duplicate username constraint on remote."""
    problem_users = ["maryam@radiantmedical.com.pk", "tanveer@radiantmedical.com.pk"]
    for email in problem_users:
        if frappe.db.exists("User", email):
            continue
        try:
            res = api_call(f"resource/User/{urllib.parse.quote(email)}")
            if not res or "data" not in res:
                continue
            d = clean_doc(res["data"])
            d["doctype"] = "User"
            # Disambiguate username to avoid duplicate key constraint
            d["username"] = email
            doc = frappe.get_doc(d)
            for f in ("ignore_permissions", "ignore_mandatory", "ignore_links", "ignore_validate"):
                setattr(doc.flags, f, True)
            doc.insert(set_name=email)
            frappe.db.commit()
            print(f"Inserted User {email} (username set to email)", flush=True)
        except Exception as e:
            frappe.db.rollback()
            print(f"User {email} insert error: {e}", flush=True)


def fix_missing_employees():
    """Scans all Radiant employees and inserts any missing locally, handling duplicate CNICs."""
    res = api_call('resource/Employee?fields=["name"]&limit_page_length=5000')
    if not res or "data" not in res:
        return
    rad_names = [r["name"] for r in res["data"]]
    local_names = set(frappe.get_all("Employee", pluck="name"))
    missing = [name for name in rad_names if name not in local_names]
    print(f"Radiant Employees: {len(rad_names)} | Local: {len(local_names)} | Missing: {len(missing)}", flush=True)

    for name in missing:
        try:
            r = api_call(f"resource/Employee/{urllib.parse.quote(name)}")
            if not r or "data" not in r:
                continue
            d = clean_doc(r["data"])
            d["doctype"] = "Employee"
            d["image"] = None

            # Relax duplicate CNIC constraint
            cnic = d.get("cnic")
            if cnic and frappe.db.exists("Employee", {"cnic": cnic}):
                d["cnic"] = None

            uid = d.get("user_id")
            if uid and not frappe.db.exists("User", uid):
                d["user_id"] = None

            ws = d.get("default_workspace")
            d["default_workspace"] = aka(ws) if ws and frappe.db.exists("Workspace", aka(ws)) else None

            doc = frappe.get_doc(d)
            for f in ("ignore_permissions", "ignore_mandatory", "ignore_links", "ignore_validate"):
                setattr(doc.flags, f, True)
            doc.insert(set_name=name)
            frappe.db.commit()
            print(f"Inserted Employee {name}", flush=True)
        except Exception as e:
            frappe.db.rollback()
            print(f"Employee {name} insert error: {e}", flush=True)


def link_users():
    res = api_call('resource/Employee?fields=["name","user_id"]&limit_page_length=5000')
    if not res or "data" not in res:
        return
    linked = skipped_nouser = missing_emp = same = 0
    for r in res["data"]:
        uid = r.get("user_id")
        if not uid:
            continue
        if not frappe.db.exists("Employee", r["name"]):
            missing_emp += 1
            continue
        if not frappe.db.exists("User", uid):
            skipped_nouser += 1
            continue
        if frappe.db.get_value("Employee", r["name"], "user_id") == uid:
            same += 1
            continue
        frappe.db.set_value("Employee", r["name"], "user_id", uid, update_modified=False)
        linked += 1
    frappe.db.commit()
    print(f"Linked: {linked}, already linked: {same}, user missing: {skipped_nouser}, employee missing: {missing_emp}", flush=True)


def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    frappe.flags.in_import = True
    print("--- Starting Leftovers Resolution ---", flush=True)
    for fn in (fix_module_defs, fix_customer, fix_users, fix_missing_employees, link_users):
        try:
            fn()
        except Exception as e:
            print(f"{fn.__name__} failed: {e}", flush=True)
            frappe.db.rollback()
    print("--- Leftovers Resolution Complete ---", flush=True)


if __name__ == "__main__":
    main()
