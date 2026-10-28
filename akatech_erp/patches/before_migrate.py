import frappe


def execute():
	"""Auto-fix known migration blockers before ERPNext patches run."""
	try:
		# 1. Workstation Operating Component fix:
		# If a Company has default_operating_cost_account set to a Group account,
		# clear it so erpnext.patches.v16_0.make_workstation_operating_components passes.
		if frappe.db.has_column("Company", "default_operating_cost_account"):
			companies = frappe.db.sql(
				"""
				SELECT c.name, c.default_operating_cost_account, a.is_group
				FROM `tabCompany` c
				JOIN `tabAccount` a ON a.name = c.default_operating_cost_account
				WHERE a.is_group = 1
			""",
				as_dict=True,
			)
			for comp in companies:
				frappe.db.set_value(
					"Company", comp.name, "default_operating_cost_account", None, update_modified=False
				)
				frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error in akatech_erp before_migrate: {e}", "Migration Fix")
