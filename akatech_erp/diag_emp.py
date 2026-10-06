import frappe
import urllib.parse

from akatech_erp.sync_users_retry import api_call


def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    res = api_call('resource/Employee?fields=["name","status","user_id","employee_name"]&limit_page_length=5000')
    rad = res["data"]
    local = set(frappe.get_all("Employee", pluck="name"))
    print(f"Radiant employees: {len(rad)}, local: {len(local)}", flush=True)
    missing = [r for r in rad if r["name"] not in local]
    print(f"Missing locally: {len(missing)}", flush=True)
    for r in missing[:70]:
        print(r, flush=True)
    extra = local - {r["name"] for r in rad}
    print(f"Local not in Radiant: {len(extra)} {list(extra)[:10]}", flush=True)
    v = api_call("resource/Customer/Vitrace%20International%20FZC")
    print("Radiant Vitrace represents_company:", (v or {}).get("data", {}).get("represents_company"), flush=True)
    print("Radiant 0359:", {k: api_call("resource/Customer/RM-CUS-0359")["data"].get(k) for k in ("customer_name", "represents_company", "is_internal_customer")}, flush=True)


if __name__ == "__main__":
    main()
