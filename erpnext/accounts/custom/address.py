import frappe
from frappe import _
from frappe.contacts.doctype.address.address import (
	Address,
	get_address_display,
	get_address_templates,
)


class ERPNextAddress(Address):
	def validate(self):
     """Validates the address
     Args:
         self: Address object to validate
     Returns: 
         True: If validation passes
     - Validates reference fields are not empty
     - Updates company address if this is default billing/shipping
     - Calls super class validation"""
		self.validate_reference()
		self.update_compnay_address()
		super(ERPNextAddress, self).validate()

	def link_address(self):
		"""Link address based on owner"""
		if self.is_your_company_address:
			return

		return super(ERPNextAddress, self).link_address()

	def update_compnay_address(self):
     """
     Updates company address flag for links
     Args:
         self: Link document object
     Returns: 
         None: No value is returned
     - Get all links associated with document
     - Check if any link doctype is Company
     - If Company link found, set is_your_company_address flag to 1"""
		for link in self.get("links"):
			if link.link_doctype == "Company":
				self.is_your_company_address = 1

	def validate_reference(self):
     """Validates if company address is linked to a company
     Args:
         self: The object being validated
     Returns: 
         None: Does not return anything
     - Checks if address is company address
     - Checks if there are no rows in links table with doctype as Company
     - Throws error if above conditions are true stating company needs to be linked
     - Error title also specifies company is not linked"""
		if self.is_your_company_address and not [
			row for row in self.links if row.link_doctype == "Company"
		]:
			frappe.throw(
				_("Address needs to be linked to a Company. Please add a row for Company in the Links table."),
				title=_("Company Not Linked"),
			)

	def on_update(self):
		"""
		After Address is updated, update the related 'Primary Address' on Customer.
		"""
		address_display = get_address_display(self.as_dict())
		filters = {"customer_primary_address": self.name}
		customers = frappe.db.get_all("Customer", filters=filters, as_list=True)
		for customer_name in customers:
			frappe.db.set_value("Customer", customer_name[0], "primary_address", address_display)


@frappe.whitelist()
def get_shipping_address(company, address=None):
    """
    Gets the shipping address for a company.
    Args:
        company: Company name in one line
        address (optional): Address name in one line
    Returns: 
        address: Shipping address details in one line
    Processing Logic:
        - Fetch address linked to company with is_your_company_address flag
        - If address is passed, filter for that address
        - If no address passed, filter for address with is_shipping_address flag
        - Return address details or empty dict
        - Format address using address template
    """
	filters = [
		["Dynamic Link", "link_doctype", "=", "Company"],
		["Dynamic Link", "link_name", "=", company],
		["Address", "is_your_company_address", "=", 1],
	]
	fields = ["*"]
	if address and frappe.db.get_value("Dynamic Link", {"parent": address, "link_name": company}):
		filters.append(["Address", "name", "=", address])
	if not address:
		filters.append(["Address", "is_shipping_address", "=", 1])

	address = frappe.get_all("Address", filters=filters, fields=fields) or {}

	if address:
		address_as_dict = address[0]
		name, address_template = get_address_templates(address_as_dict)
		return address_as_dict.get("name"), frappe.render_template(address_template, address_as_dict)
