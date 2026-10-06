import frappe

def create_workflow_states():
    states = [
        'Pending L3 Approval', 'Reviewed', 'Preparing', 'Pending Approval', 
        'Finalized', 'Approved and Paid', 'Approved', 'Pending L2 Approval', 
        'In Review', 'Pending Review', 'Cancelled', 'On Hold', 'Changes Required', 
        'Pending Final Approval', 'Pending L1 Approval', 'Rejected', 'Submitted', 
        'Issued', 'Draft', 'Pending Approval by Accounts'
    ]
    
    for state in states:
        if not frappe.db.exists("Workflow State", state):
            doc = frappe.new_doc("Workflow State")
            doc.workflow_state_name = state
            doc.insert(ignore_permissions=True)
            print(f"Created Workflow State: {state}")
        else:
            print(f"Workflow State exists: {state}")
            
    frappe.db.commit()

create_workflow_states()
