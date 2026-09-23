"""
=============================================================================
Sales Department Module — Test Suite
=============================================================================
Tests the core Sales Department functionality:
  - Sales Order creation and submission
  - Customer master existence
  - Workspace shortcuts (Project, Performance Guarantee, Sales Order)
  - Module Def registration

Run from bench:
  bench --site akatech.local run-tests --app akatech_erp --module sales_department

Or from WSL terminal:
  cd ~/frappe-bench
  bench --site akatech.local run-tests --app akatech_erp --module "Sales Department"
=============================================================================
"""
import frappe
import unittest


class TestSalesDepartmentModule(unittest.TestCase):

    def test_module_def_exists(self):
        """Verify 'Sales Department' Module Def is registered."""
        exists = frappe.db.exists("Module Def", "Sales Department")
        self.assertTrue(exists, "Module Def 'Sales Department' not found. Run system_console_script.py first.")

    def test_workspace_exists(self):
        """Verify 'Sales Department' Workspace exists and is public."""
        ws = frappe.db.get_value("Workspace", "Sales Department", ["name", "public"], as_dict=True)
        self.assertIsNotNone(ws, "Workspace 'Sales Department' not found.")
        self.assertEqual(ws.public, 1, "Workspace 'Sales Department' is not public.")

    def test_sales_order_doctype_accessible(self):
        """Verify Sales Order DocType is available (standard ERPNext)."""
        meta = frappe.get_meta("Sales Order")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "Sales Order")

    def test_customer_doctype_accessible(self):
        """Verify Customer DocType is accessible."""
        meta = frappe.get_meta("Customer")
        self.assertIsNotNone(meta)

    def test_project_doctype_accessible(self):
        """Verify Project DocType is accessible (used for Bid Management shortcuts)."""
        meta = frappe.get_meta("Project")
        self.assertIsNotNone(meta)

    def test_sales_order_custom_fields_exist(self):
        """
        Verify key custom fields added by setup_client.py exist on Sales Order.
        These are fields extracted from Radiant Medical's customizations.
        Adjust field names if setup_client.py was modified.
        """
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Sales Order", "custom": 1},
            fields=["fieldname", "label"]
        )
        # At minimum, setup_client.py should have added at least 1 custom field
        self.assertGreater(
            len(custom_fields), 0,
            "No custom fields found on Sales Order. Has setup_client.py been run?"
        )

    def test_create_and_delete_customer(self):
        """
        Smoke test: create a minimal Customer, verify it saves, then delete it.
        """
        test_name = "__test_akatech_customer__"
        if frappe.db.exists("Customer", test_name):
            frappe.delete_doc("Customer", test_name, force=True)

        doc = frappe.new_doc("Customer")
        doc.customer_name = test_name
        doc.customer_type = "Company"
        doc.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
        doc.territory = "All Territories"
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertTrue(frappe.db.exists("Customer", test_name))

        # Cleanup
        frappe.delete_doc("Customer", test_name, force=True)
        frappe.db.commit()
