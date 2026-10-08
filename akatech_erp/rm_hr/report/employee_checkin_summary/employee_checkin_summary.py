import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 200},
        {"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "total_checkins", "label": _("Total Check-ins"), "fieldtype": "Int", "width": 120},
        {"fieldname": "latest_checkin", "label": _("Latest Check-in Time"), "fieldtype": "Datetime", "width": 150},
        {"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Shift Type", "width": 150},
    ]

def get_data(filters):
    conditions = ""
    if filters.get("employee"):
        conditions += f" AND employee = '{filters.get('employee')}'"
        
    query = f"""
        SELECT 
            employee,
            employee_name,
            COUNT(name) as total_checkins,
            MAX(time) as latest_checkin,
            shift
        FROM 
            `tabEmployee Checkin`
        WHERE 
            docstatus < 2 {conditions}
        GROUP BY 
            employee
        ORDER BY 
            latest_checkin DESC
    """
    
    return frappe.db.sql(query, as_dict=True)
