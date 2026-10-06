import frappe
import urllib.parse

from akatech_erp.sync_parties import api_call, clean_doc


def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    for u in frappe.get_all("User", filters={"default_workspace": ["is", "set"]}, fields=["name", "default_workspace"]):
        ws = u.default_workspace
        if not frappe.db.exists("Workspace", ws):
            new = ("AKA " + ws[3:]) if ws.upper().startswith("RM ") else None
            new = new if new and frappe.db.exists("Workspace", new) else None
            frappe.db.set_value("User", u.name, "default_workspace", new, update_modified=False)
            print(f"User {u.name}: workspace {ws} -> {new}", flush=True)
    frappe.db.commit()
    name = "RM-LHR-10132"
    res = api_call(f"resource/Employee/{urllib.parse.quote(name)}")
    d = res["data"]
    cnic = d.get("cnic")
    other = frappe.db.get_value("Employee", {"cnic": cnic}, ["name", "employee_name"])
    print(f"CNIC {cnic} held locally by: {other}; radiant: {d.get('employee_name')}; ws: {d.get('default_workspace')}", flush=True)
    uid = d.get("user_id")
    d = clean_doc(d)
    d["doctype"] = "Employee"
    d["image"] = None
    d["default_workspace"] = None
    if other:
        d["cnic"] = None
    if uid and frappe.db.exists("User", uid):
        d["user_id"] = uid
    doc = frappe.get_doc(d)
    for f in ("ignore_permissions", "ignore_mandatory", "ignore_links", "ignore_validate"):
        setattr(doc.flags, f, True)
    doc.insert(set_name=name)
    frappe.db.commit()
    print(f"Inserted {name}; cnic kept: {bool(d.get('cnic'))}", flush=True)


if __name__ == "__main__":
    main()
