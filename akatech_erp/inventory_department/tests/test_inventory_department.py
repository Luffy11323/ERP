"""
=============================================================================
Inventory Department Module — Test Suite
=============================================================================
Tests the core Inventory Department functionality:
  - Stock Entry creation and DocType accessibility
  - Module Def and Workspace registration
  - Custom fields from setup_client.py
  - Warehouse existence (created by setup_client.py)

Run from bench:
  bench --site akatech.local run-tests --app akatech_erp --module inventory_department
=============================================================================
"""
import frappe
import unittest


class TestInventoryDepartmentModule(unittest.TestCase):

    def test_module_def_exists(self):
        """Verify 'Inventory Department' Module Def is registered."""
        exists = frappe.db.exists("Module Def", "Inventory Department")
        self.assertTrue(exists, "Module Def 'Inventory Department' not found. Run system_console_script.py first.")

    def test_workspace_exists(self):
        """Verify 'Inventory Department' Workspace exists and is public."""
        ws = frappe.db.get_value("Workspace", "Inventory Department", ["name", "public"], as_dict=True)
        self.assertIsNotNone(ws, "Workspace 'Inventory Department' not found.")
        self.assertEqual(ws.public, 1, "Workspace 'Inventory Department' is not public.")

    def test_stock_entry_doctype_accessible(self):
        """Verify Stock Entry DocType is available."""
        meta = frappe.get_meta("Stock Entry")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "Stock Entry")

    def test_purchase_receipt_doctype_accessible(self):
        """Verify Purchase Receipt DocType is accessible."""
        meta = frappe.get_meta("Purchase Receipt")
        self.assertIsNotNone(meta)

    def test_delivery_note_doctype_accessible(self):
        """Verify Delivery Note DocType is accessible."""
        meta = frappe.get_meta("Delivery Note")
        self.assertIsNotNone(meta)

    def test_item_doctype_accessible(self):
        """Verify Item DocType is accessible."""
        meta = frappe.get_meta("Item")
        self.assertIsNotNone(meta)

    def test_warehouse_exists(self):
        """
        Verify at least one Warehouse exists (created during setup_client.py).
        The script creates warehouses like 'Stores - <CompanyAbbr>'.
        """
        warehouses = frappe.get_all("Warehouse", fields=["name"])
        self.assertGreater(
            len(warehouses), 0,
            "No warehouses found. Has setup_client.py been run and the company set up?"
        )

    def test_item_custom_fields_exist(self):
        """
        Verify custom fields from setup_client.py exist on Item.
        """
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Item", "custom": 1},
            fields=["fieldname", "label"]
        )
        self.assertGreater(
            len(custom_fields), 0,
            "No custom fields on Item DocType. Has setup_client.py been run?"
        )

    def test_serial_no_doctype_accessible(self):
        """Verify Serial No DocType is accessible (used in workspace links)."""
        meta = frappe.get_meta("Serial No")
        self.assertIsNotNone(meta)

    def test_batch_doctype_accessible(self):
        """Verify Batch DocType is accessible (used in workspace links)."""
        meta = frappe.get_meta("Batch")
        self.assertIsNotNone(meta)
