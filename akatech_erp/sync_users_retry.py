import frappe
import urllib.parse
import requests

from akatech_erp.sync_parties import api_call, clean_doc

SKIP_USERS = {"Administrator", "Guest"}


def sync_users():
    res = api_call('resource/User?fields=["name"]&limit_page_length=5000')
    if not res or "data" not in res:
        print("Failed to fetch User list.", flush=True)
        return
    for item in res["data"]:
        name = item["name"]
        if name in SKIP_USERS or frappe.db.exists("User", name):
            continue
        doc_res = api_call(f"resource/User/{urllib.parse.quote(name)}")
        if not doc_res or "data" not in doc_res:
            print(f"Failed to fetch User {name}", flush=True)
            continue
        d = clean_doc(doc_res["data"])
        d["doctype"] = "User"
        for k in ["api_key", "api_secret", "last_login", "last_active", "last_ip",
                  "last_known_versions", "login_after", "login_before", "user_emails",
                  "social_logins", "block_modules", "user_image", "new_password",
                  "reset_password_key", "thread_notify", "bio"]:
            d.pop(k, None)
        # keep only roles that exist locally
        d["roles"] = [
            {"doctype": "Has Role", "role": r["role"]}
            for r in d.get("roles", [])
            if frappe.db.exists("Role", r["role"])
        ]
        try:
            doc = frappe.get_doc(d)
            doc.flags.ignore_permissions = True
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_links = True
            doc.send_welcome_email = 0
            doc.insert(set_name=name)
            frappe.db.commit()
            print(f"Inserted User {name}", flush=True)
        except Exception as e:
            print(f"Error inserting User {name}: {e}", flush=True)
            frappe.db.rollback()
    frappe.db.commit()


def sync_with_user_id(doctype):
    res = api_call(f'resource/{urllib.parse.quote(doctype)}?fields=["name"]&limit_page_length=5000')
    if not res or "data" not in res:
        print(f"Failed to fetch {doctype} list.", flush=True)
        return
    for item in res["data"]:
        name = item["name"]
        if frappe.db.exists(doctype, name):
            continue
        doc_res = api_call(f"resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(name)}")
        if not doc_res or "data" not in doc_res:
            print(f"Failed to fetch {doctype} {name}", flush=True)
            continue
        d = doc_res["data"]
        d["doctype"] = doctype
        uid = d.get("user_id")
        d = clean_doc(d)
        if uid and frappe.db.exists("User", uid):
            d["user_id"] = uid
        try:
            if doctype == "Employee":
                if d.get("cnic") and frappe.db.exists("Employee", {"cnic": d["cnic"]}):
                    d["cnic"] = None
                d["image"] = None  # photo files are not copied to this site
            doc = frappe.get_doc(d)
            doc.flags.ignore_permissions = True
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_links = True
            doc.flags.ignore_validate = True
            doc.insert(set_name=name)
            frappe.db.commit()
            print(f"Inserted {doctype} {name}", flush=True)
        except Exception as e:
            print(f"Error inserting {doctype} {name}: {e}", flush=True)
            frappe.db.rollback()
    frappe.db.commit()


def sync_company():
    name = "Radiant Medical (Pvt.) Ltd."
    if frappe.db.exists("Company", name):
        print(f"Exists Company {name}", flush=True)
        return
    doc_res = api_call(f"resource/Company/{urllib.parse.quote(name)}")
    if not doc_res or "data" not in doc_res:
        print(f"Failed to fetch Company {name}", flush=True)
        return
    d = clean_doc(doc_res["data"])
    d["doctype"] = "Company"
    # accounts/warehouses/cost centers are copied later; drop links that don't exist yet
    for k, v in list(d.items()):
        if isinstance(v, str) and k.startswith(("default_", "round_off", "exchange_gain", "unrealized", "stock_", "write_off", "cost_center", "depreciation", "capital_work", "accumulated", "disposal", "expenses_included", "service_expense", "asset_received", "enable_perpetual", "auto_")) and k != "default_currency":
            d[k] = None
    d["create_chart_of_accounts_based_on"] = ""
    try:
        doc = frappe.get_doc(d)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.name = name
        doc.db_insert()
        for child in doc.get_all_children():
            child.db_insert()
        frappe.db.commit()
        print(f"Inserted Company {name}", flush=True)
    except Exception as e:
        print(f"Error inserting Company {name}: {e}", flush=True)
        frappe.db.rollback()


def fix_employee_company():
    company = "Radiant Medical (Pvt.) Ltd."
    if not frappe.db.exists("Company", company):
        return
    frappe.db.sql("update `tabEmployee` set company=%s where name like 'RM-%%' and company != %s", (company, company))
    frappe.db.commit()
    print("Re-pointed RM employees to Radiant company.", flush=True)


def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    frappe.flags.in_import = True
    sync_company()
    for dt in ["Role", "Module Def", "Role Profile", "Module Profile"]:
        sync_with_user_id(dt)
    sync_users()
    for dt in ["Customer", "Supplier", "Employee"]:
        sync_with_user_id(dt)
    fix_employee_company()
    print("Retry sync complete.", flush=True)


if __name__ == "__main__":
    main()
