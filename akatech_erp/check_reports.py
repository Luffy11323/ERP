import frappe
def check_reports():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    reports = frappe.db.sql("""
        SELECT name, module, is_standard, report_type 
        FROM `tabReport` 
        WHERE module IN ('RM HR', 'RM Payroll', 'Kodessy Tools', 'Kodessy Accounts', 'AKA BUYING', 'AKA SELLING')
    """, as_dict=True)
    for r in reports:
        print(f"Report: {r.name}, Module: {r.module}, Standard: {r.is_standard}, Type: {r.report_type}")
        
    pages = frappe.db.sql("""
        SELECT name, module, standard 
        FROM `tabPage` 
        WHERE module IN ('RM HR', 'RM Payroll', 'Kodessy Tools', 'Kodessy Accounts', 'AKA BUYING', 'AKA SELLING')
    """, as_dict=True)
    for p in pages:
        print(f"Page: {p.name}, Module: {p.module}, Standard: {p.standard}")

    doctypes = frappe.db.sql("""
        SELECT name, module, custom 
        FROM `tabDocType` 
        WHERE module IN ('RM HR', 'RM Payroll', 'Kodessy Tools', 'Kodessy Accounts', 'AKA BUYING', 'AKA SELLING')
    """, as_dict=True)
    for d in doctypes:
        print(f"DocType: {d.name}, Module: {d.module}, Custom: {d.custom}")

if __name__ == "__main__":
    check_reports()
