import frappe
def execute():
    frappe.db.sql("TRUNCATE TABLE `tabVersion`")
    frappe.db.sql("TRUNCATE TABLE `tabError Log`")
    frappe.db.sql("TRUNCATE TABLE `tabAccess Log`")
    frappe.db.sql("TRUNCATE TABLE `tabActivity Log`")
    frappe.db.sql("TRUNCATE TABLE `tabEmail Queue`")
    frappe.db.commit()
