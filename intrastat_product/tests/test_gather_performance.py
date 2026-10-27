# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import Form, TransactionCase

from .common import IntrastatProductCommon


class TestIntrastatGatherPerformance(IntrastatProductCommon, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "FR customer",
                "country_id": cls.env.ref("base.fr").id,
                "vat": "FR86792377731",
                "property_account_position_id": cls.position.id,
            }
        )
        cls.product = cls.product_c3po.product_variant_ids

    def _post_invoice(self, invoice_date, nlines):
        move_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.customer
        move_form.invoice_date = invoice_date
        for _i in range(nlines):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product
        invoice = move_form.save()
        invoice.action_post()
        return invoice

    def _gather_query_count(self, year, month):
        self._create_declaration(
            {"declaration_type": "dispatches", "year": year, "month": month}
        )
        self.env.flush_all()
        self.env.invalidate_all()
        start = self.env.cr.sql_log_count
        self.declaration.action_gather()
        self.env.flush_all()
        return self.env.cr.sql_log_count - start

    def test_gather_queries_do_not_grow_with_lines(self):
        """The declaration reads the invoice lines in batch: gathering an
        invoice of 2 lines or 3 invoices of 4 lines runs the same queries"""
        self._post_invoice("2025-01-15", 2)
        for day in ("2025-02-03", "2025-02-10", "2025-02-20"):
            self._post_invoice(day, 4)
        # A first declaration fills the caches (xmlids, decimal precisions)
        self._post_invoice("2025-03-15", 2)
        self._gather_query_count("2025", "03")
        queries_few_lines = self._gather_query_count("2025", "01")
        self.assertEqual(len(self.declaration.computation_line_ids), 2)
        queries_many_lines = self._gather_query_count("2025", "02")
        self.assertEqual(len(self.declaration.computation_line_ids), 12)
        self.assertEqual(queries_few_lines, queries_many_lines)
