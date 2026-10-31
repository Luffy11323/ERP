# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class POImportWorkflowRow(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date_value: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		question: DF.Data
		remarks: DF.SmallText | None
		response: DF.SmallText | None
		sequence: DF.Int
		status: DF.Literal["Pending", "In Progress", "Completed", "Hold", "Cancelled"]
		tracking_no: DF.Data | None
	# end: auto-generated types
	pass
