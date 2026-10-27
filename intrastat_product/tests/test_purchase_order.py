# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase

from .common_purchase import IntrastatPurchaseCommon


class TestIntrastatProductPurchase(IntrastatPurchaseCommon):
    """Tests for this module"""

    def test_purchase_to_invoice_default(self):
        date_order = "2021-09-01"
        declaration_date = "2021-10-01"
        with freeze_time(date_order):
            self._create_purchase_order()
        self.purchase.button_confirm()
        self.purchase.picking_ids.button_validate()
        self.assertEqual("done", self.purchase.picking_ids.state)

        with freeze_time(date_order):
            action = self.purchase.action_create_invoice()
        invoice_id = action["res_id"]
        invoice = self.move_obj.browse(invoice_id)

        invoice.invoice_date = fields.Date.from_string(date_order)
        invoice.action_post()

        # Check if transport mode has been transmitted to invoice
        # It should be None as not defined on sale order
        self.assertFalse(
            invoice.intrastat_transport_id,
        )

        vals = {
            "declaration_type": "arrivals",
        }
        with freeze_time(declaration_date):
            self._create_declaration(vals)
        self.declaration.action_gather()

        self._check_line_values()
        self.declaration.draft2confirmed()
        self.declaration.confirmed2done()
        self._check_line_values(final=True)

        # Check the Excel file
        file_data = self._create_xls()
        self.check_xls(file_data[0])

    def _invoice_received_purchase(self, date_order):
        with freeze_time(date_order):
            self._create_purchase_order()
        self.purchase.button_confirm()
        self.purchase.picking_ids.button_validate()
        with freeze_time(date_order):
            action = self.purchase.action_create_invoice()
        invoice = self.move_obj.browse(action["res_id"])
        invoice.invoice_date = fields.Date.from_string(date_order)
        invoice.action_post()
        return invoice

    def test_purchase_declaration_region(self):
        """The region of an arrival is the one of the warehouse whose stock
        location received the goods, else the default region of the company"""
        warehouse = self.purchase_obj.new({}).picking_type_id.warehouse_id
        # Configured by the inventory and accounting administrators
        warehouse.sudo().region_id = self.region
        self._invoice_received_purchase("2021-09-01")
        company_region = self.region_obj.sudo().create(
            {
                "code": "BRU",
                "country_id": self.env.ref("base.be").id,
                "company_id": self.company.id,
                "name": "Brussels",
            }
        )
        self.company.sudo().intrastat_region_id = company_region
        with freeze_time("2021-10-01"):
            self._create_declaration({"declaration_type": "arrivals"})
        self.declaration.action_gather()
        self.assertEqual(self.declaration.computation_line_ids.region_id, self.region)
        self.assertEqual(
            self.declaration.computation_line_ids.region_code, self.region.code
        )
        # Without region on the warehouse, the company one applies
        warehouse.sudo().region_id = False
        self.env.invalidate_all()
        self.declaration.action_gather()
        self.assertEqual(
            self.declaration.computation_line_ids.region_id, company_region
        )


class TestIntrastatProductPurchaseCase(TestIntrastatProductPurchase, TransactionCase):
    """Test Intrastat Purchase"""
