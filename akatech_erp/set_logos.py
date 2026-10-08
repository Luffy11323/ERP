import frappe

def set_logos():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    # System Settings
    ss = frappe.get_doc("System Settings", "System Settings")
    ss.app_logo = "/files/logo.png"
    ss.flags.ignore_permissions = True
    ss.flags.ignore_mandatory = True
    ss.save()

    # Website Settings
    ws = frappe.get_doc("Website Settings", "Website Settings")
    ws.splash_image = "/files/logo.png"
    ws.favicon = "/files/logo.png"
    ws.app_logo = "/files/logo.png"
    ws.flags.ignore_permissions = True
    ws.flags.ignore_mandatory = True
    ws.save()

    frappe.db.commit()
    print("Logos updated successfully!")

if __name__ == "__main__":
    set_logos()
