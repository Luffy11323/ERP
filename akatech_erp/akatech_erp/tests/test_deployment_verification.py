"""
=============================================================================
Deployment Verification Tests — Run AFTER all 3 setup scripts complete
=============================================================================
Verifies that the full deployment (Steps 1, 2, 3) was successful:
  - All 9 custom DocTypes from doctype_setup.py exist
  - All 3 Module Defs and Workspaces from system_console_script.py exist
  - Key customizations from setup_client.py are present

Run this after every new site deployment to confirm everything worked:
  bench --site akatech.local run-tests --app akatech_erp --module akatech_erp

Or run all tests at once from WSL:
  cd ~/frappe-bench
  bench --site akatech.local run-tests --app akatech_erp
=============================================================================
"""
import frappe
import unittest


class TestStep1DocTypeSetup(unittest.TestCase):
    """Tests for doctype_setup.py — must be run FIRST"""

    CUSTOM_DOCTYPES = [
        "PO Import Workflow Row",
        "Item Category",
        "Mode of Transport",
        "LC Register Party",
        "LC Register Proforma Invoice",
        "LC Register Project",
        "LC Register Sales Order",
        "LC Register Purchase Order",
        "LC Register",
    ]

    def test_all_custom_doctypes_exist(self):
        """Verify all 9 custom DocTypes from doctype_setup.py were created."""
        missing = []
        for dt in self.CUSTOM_DOCTYPES:
            if not frappe.db.exists("DocType", dt):
                missing.append(dt)
        self.assertEqual(
            missing, [],
            f"Missing DocTypes (run doctype_setup.py): {missing}"
        )

    def test_lc_register_is_submittable(self):
        """Verify LC Register DocType is submittable (is_submittable=1)."""
        meta = frappe.get_meta("LC Register")
        self.assertEqual(meta.is_submittable, 1, "LC Register should be submittable.")


class TestStep2CustomizationSetup(unittest.TestCase):
    """Tests for setup_client.py — verifies customizations were applied"""

    CORE_DOCTYPES = [
        "Sales Order",
        "Purchase Order",
        "Item",
        "Customer",
        "Supplier",
        "Stock Entry",
        "Delivery Note",
        "Purchase Receipt",
    ]

    def test_customizations_applied_to_core_doctypes(self):
        """Verify each core DocType has at least 1 custom field from setup_client.py."""
        results = {}
        for dt in self.CORE_DOCTYPES:
            count = frappe.db.count("Custom Field", {"dt": dt, "custom": 1})
            results[dt] = count

        no_fields = [dt for dt, count in results.items() if count == 0]
        self.assertEqual(
            no_fields, [],
            f"These DocTypes have 0 custom fields — setup_client.py may not have run: {no_fields}"
        )

    def test_total_customization_count(self):
        """
        Verify total custom fields count is reasonable (should be 300+ after full setup).
        If this fails, setup_client.py may have partially failed.
        """
        total = frappe.db.count("Custom Field", {"custom": 1})
        self.assertGreater(
            total, 100,
            f"Only {total} custom fields found. Expected 300+. setup_client.py may not have run fully."
        )


class TestStep3ModulesAndWorkspaces(unittest.TestCase):
    """Tests for system_console_script.py — verifies modules and workspaces"""

    MODULES = ["Sales Department", "Procurement Department", "Inventory Department"]

    def test_all_module_defs_exist(self):
        """Verify all 3 Module Defs exist."""
        missing = [m for m in self.MODULES if not frappe.db.exists("Module Def", m)]
        self.assertEqual(
            missing, [],
            f"Missing Module Defs (run system_console_script.py): {missing}"
        )

    def test_all_workspaces_exist_and_are_public(self):
        """Verify all 3 Workspaces exist and are marked public."""
        for mod in self.MODULES:
            ws = frappe.db.get_value("Workspace", mod, ["name", "public"], as_dict=True)
            self.assertIsNotNone(ws, f"Workspace '{mod}' not found.")
            self.assertEqual(ws.public, 1, f"Workspace '{mod}' is not public.")

    def test_workspace_content_not_empty(self):
        """Verify each Workspace has content (shortcuts/links configured)."""
        for mod in self.MODULES:
            content = frappe.db.get_value("Workspace", mod, "content")
            self.assertTrue(
                content and len(content) > 10,
                f"Workspace '{mod}' has empty content — it may not have been imported correctly."
            )
