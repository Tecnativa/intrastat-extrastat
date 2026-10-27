# Copyright 2009-2020 Noviat nv/sa (www.noviat.com).
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# @author Luc de Meyer <info@noviat.com>
# Copyright 2026 Tecnativa - Carlos Dauden

from odoo import api, fields, models
from odoo.fields import Domain


class StockLocation(models.Model):
    _inherit = "stock.location"

    intrastat_region_id = fields.Many2one(
        comodel_name="intrastat.region",
        compute="_compute_intrastat_region_id",
        help="Intrastat region of the first warehouse (by sequence) whose stock "
        "location contains this location.",
    )

    @api.depends("parent_path")
    def _compute_intrastat_region_id(self):
        # One search for all the locations of the prefetch set (the locations
        # of every line of a declaration), as stock.location.warehouse_id does
        warehouses = self.env["stock.warehouse"].search(
            Domain("lot_stock_id", "parent_of", self.ids)
            & Domain("region_id", "!=", False)
        )
        self.intrastat_region_id = False
        for location in self:
            if not location.parent_path:
                continue
            path = set(location.parent_path.split("/")[:-1])
            for warehouse in warehouses:
                if str(warehouse.lot_stock_id.id) in path:
                    location.intrastat_region_id = warehouse.region_id
                    break

    def get_intrastat_region(self):
        self.ensure_one()
        return self.intrastat_region_id
