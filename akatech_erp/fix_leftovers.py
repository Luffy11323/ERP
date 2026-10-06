import frappe
import urllib.parse

from akatech_erp.sync_users_retry import api_call
from akatech_erp.sync_parties import clean_doc

COMPANY = "Radiant Medical (Pvt.) Ltd."


def aka(name):
    if name.lower().startswith("rm "):
        return "AKA " + name[3:]
    return name


def fix_module_defs():
    for rm in ["Rm Erp", "RM Payroll", "Rm Stock", "RM Selling", "RM HR", "RM Buying"]:
        new = aka(rm)
        print(f"Local candidates for {rm}: {frappe.get_all('Module Def', filters={'name': ['like', '%' + rm[3:] + '%']}, pluck='name')}", flush=True)
        if frappe.db.exists("Module Def", new):
            print(f"Exists Module Def {new}", flush=True)
            continue
        doc = frappe.get_doc({"doctype": "Module Def", "module_name": new, "app_name": "akatech_erp", "custom": 1})
        doc.name = new
        doc.db_insert()
        print(f"Inserted Module Def {new}", flush=True)
    frappe.db.commit()


def fix_customer():
    name = "RM-CUS-0359"
    owner = frappe.db.get_value("Customer", {"represents_company": COMPANY}, "name")
    print(f"Customer representing {COMPANY}: {owner}", flush=True)
    if frappe.db.exists("Customer", name):
        print(f"Exists Customer {name}", flush=True)
        return
    if owner and owner != name:
        print(f"Renaming Customer {owner} -> {name} (same record in Radiant)", flush=True)
        frappe.rename_doc("Customer", owner, name, force=True)
        frappe.db.commit()
        print(f"Renamed Customer to {name}", flush=True)
        return
    if owner:
        return
    res = api_call(f"resource/Customer/{urllib.parse.quote(name)}")
    d = clean_doc(res["data"])
    d["doctype"] = "Customer"
    doc = frappe.get_doc(d)
    for f in ("ignore_permissions", "ignore_mandatory", "ignore_links", "ignore_validate"):
        setattr(doc.flags, f, True)
    doc.insert(set_name=name)
    frappe.db.commit()
    print(f"Inserted Customer {name}", flush=True)


def fix_employee_132():
    name = "RM-LHR-10132"
    if frappe.db.exists("Employee", name):
        print(f"Exists Employee {name}", flush=True)
        return
    res = api_call(f"resource/Employee/{urllib.parse.quote(name)}")
    uid = res["data"].get("user_id")
    d = clean_doc(res["data"])
    d["doctype"] = "Employee"
    d["image"] = None
    if uid and frappe.db.exists("User", uid):
        d["user_id"] = uid
    ws = d.get("default_workspace")
    print(f"Default workspace: {ws}; AKA candidate exists: {frappe.db.exists('Workspace', aka(ws)) if ws else None}", flush=True)
    d["default_workspace"] = aka(ws) if ws and frappe.db.exists("Workspace", aka(ws)) else None
    doc = frappe.get_doc(d)
    for f in ("ignore_permissions", "ignore_mandatory", "ignore_links", "ignore_validate"):
        setattr(doc.flags, f, True)
    doc.insert(set_name=name)
    frappe.db.commit()
    print(f"Inserted Employee {name} (workspace left as {d['default_workspace']})", flush=True)


def link_users():
    res = api_call('resource/Employee?fields=["name","user_id"]&limit_page_length=5000')
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
            print(f"User {uid} missing for {r['name']}", flush=True)
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
    for fn in (fix_module_defs, fix_customer, fix_employee_132, link_users):
        try:
            fn()
        except Exception as e:
            print(f"{fn.__name__} failed: {e}", flush=True)
            frappe.db.rollback()
    print("Fix complete.", flush=True)


if __name__ == "__main__":
    main()
