import frappe, json

def run():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    from akatech_erp import premium_api as p
    for slug in ["home", "procurement-department", "sales-department", "accounting", "hr", "payroll", "stock"]:
        try:
            c = p.get_card(slug)
            print(slug, "->", [(k["label"], k["value"]) for k in c["kpis"]] if c else None)
        except Exception as e:
            print(slug, "ERR", e)
    opts = p.get_employee_options()
    print("employees", len(opts))
    if opts:
        e = opts[0].name
        c = p.get_card("employee-self-services", employee=e)
        print("self", c["employee"], [(k["label"], k["value"]) for k in c["kpis"]])
        l = p.get_my_ledger(employee=e, from_date="2020-01-01")
        print("ledger rows", len(l["rows"]), l["totals"])
    frappe.destroy()

if __name__ == "__main__":
    run()
