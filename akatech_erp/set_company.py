import frappe
def set_company():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    
    companies = frappe.get_all("Company", pluck="name")
    if not companies:
        print("No companies found.")
        return
        
    company = companies[0]
    frappe.db.set_single_value("Global Defaults", "default_company", company)
    
    user = frappe.get_doc("User", "Administrator")
    user.append("defaults", {
        "defkey": "company",
        "defvalue": company
    })
    user.flags.ignore_permissions = True
    user.save(ignore_permissions=True)
    
    frappe.db.commit()
    print(f"Set default company to {company}")
    
if __name__ == "__main__":
    set_company()
