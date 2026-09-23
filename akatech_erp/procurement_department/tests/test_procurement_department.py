"""
=============================================================================
Procurement Department Module — Test Suite
=============================================================================
Tests the core Procurement Department functionality:
  - Purchase Order creation and basic fields
  - Module Def and Workspace registration
  - Custom fields from setup_client.py
  - Supplier master smoke test

Run from bench:
  bench --site akatech.local run-tests --app akatech_erp --module procurement_department
=============================================================================
"""
import frappe
import unittest


class TestProcurementDepartmentModule(unittest.TestCase):

    def test_module_def_exists(self):
        """Verify 'Procurement Department' Module Def is registered."""
        exists = frappe.db.exists("Module Def", "Procurement Department")
        self.assertTrue(exists, "Module Def 'Procurement Department' not found. Run system_console_script.py first.")

    def test_workspace_exists(self):
        """Verify 'Procurement Department' Workspace exists and is public."""
        ws = frappe.db.get_value("Workspace", "Procurement Department", ["name", "public"], as_dict=True)
        self.assertIsNotNone(ws, "Workspace 'Procurement Department' not found.")
        self.assertEqual(ws.public, 1, "Workspace 'Procurement Department' is not public.")

    def test_purchase_order_doctype_accessible(self):
        """Verify Purchase Order DocType is available."""
        meta = frappe.get_meta("Purchase Order")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "Purchase Order")

    def test_supplier_doctype_accessible(self):
        """Verify Supplier DocType is accessible."""
        meta = frappe.get_meta("Supplier")
        self.assertIsNotNone(meta)

    def test_purchase_order_custom_fields_exist(self):
        """
        Verify custom fields from setup_client.py exist on Purchase Order.
        Radiant Medical customized PO heavily (order_type: Local/Import/Indent).
        """
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Purchase Order", "custom": 1},
            fields=["fieldname", "label"]
        )
        self.assertGreater(
            len(custom_fields), 0,
            "No custom fields on Purchase Order. Has setup_client.py been run?"
        )

    def test_order_type_field_exists(self):
        """
        Verify the 'order_type' custom field exists on Purchase Order.
        This field drives the Local/Import/Indent workflow shortcuts on the workspace.
        """
        exists = frappe.db.exists("Custom Field", {
            "dt": "Purchase Order",
            "fieldname": "order_type"
        })
        self.assertTrue(
            exists,
            "'order_type' field missing from Purchase Order. Check setup_client.py ran correctly."
        )

    def test_create_and_delete_supplier(self):
        """
        Smoke test: create a minimal Supplier, verify it saves, then delete it.
        """
        test_name = "__test_akatech_supplier__"
        if frappe.db.exists("Supplier", test_name):
            frappe.delete_doc("Supplier", test_name, force=True)

        doc = frappe.new_doc("Supplier")
        doc.supplier_name = test_name
        doc.supplier_type = "Company"
        doc.supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group") or "All Supplier Groups"
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertTrue(frappe.db.exists("Supplier", test_name))

        # Cleanup
        frappe.delete_doc("Supplier", test_name, force=True)
        frappe.db.commit()
