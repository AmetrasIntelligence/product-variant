# Copyright 2016 Oihane Crucelaegui - AvanzOSC
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2016 ACSONE SA/NV
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        """Create possible product variants not yet created."""
        lines_without_product = self.order_line.filtered(
            lambda x: not x.product_id and x.product_tmpl_id
        )
        for line in lines_without_product:
            line.create_variant_if_needed()
        return super().button_confirm()

    def copy(self, default=None):
        """Change date_planned for lines without product after calling super"""
        new_po = super().copy(default=default)
        for line in new_po.order_line.filtered(lambda x: not x.product_id):
            product = line.product_tmpl_id._product_from_tmpl()
            seller = product._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=line.product_uom,
            )
            line.date_planned = line._get_date_planned(seller)
        return new_po


class PurchaseOrderLine(models.Model):
    _inherit = ["purchase.order.line", "product.configurator"]
    _name = "purchase.order.line"

    product_id = fields.Many2one(required=False)
    product_id_is_required = fields.Boolean(compute="_compute_product_id_is_required")
    product_uom_category_id = fields.Many2one(
        comodel_name="uom.category",
        compute="_compute_product_uom_category_id",
        # We need to define related=False so that the field is only compute
        # and not related.
        related=False,
    )

    _sql_constraints = [
        (
            "accountable_required_fields",
            "CHECK(display_type IS NOT NULL OR (product_tmpl_id IS NOT NULL OR "
            "product_id IS NOT NULL AND product_uom IS NOT NULL AND "
            "date_planned IS NOT NULL))",
            "Missing required fields on accountable purchase order line.",
        ),
        (
            "non_accountable_null_fields",
            "CHECK(display_type IS NULL OR (product_tmpl_id IS NULL AND "
            "product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND "
            "product_uom IS NULL AND date_planned is NULL))",
            "Forbidden values on non-accountable purchase order line",
        ),
    ]

    @api.depends("company_id")
    def _compute_product_id_is_required(self):
        for item in self:
            item.product_id_is_required = not item.company_id.po_confirm_create_variant

    @api.depends("product_tmpl_id", "product_id")
    def _compute_product_uom_category_id(self):
        """This compute is intended to do something similar to the related of the
        purchase module product_id.uom_id.category_id but adding the casuistry of the
        product_tmpl_id field.
        """
        for line in self:
            product = line.product_id or line.product_tmpl_id
            if product:
                line.product_uom_category_id = product.uom_id.category_id
            else:
                line.product_uom_category_id = line.product_uom_category_id

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id_configurator(self):
        """Make use of PurchaseOrderLine onchange_product_id method with
        a virtual product created on the fly.
        """
        res = super()._onchange_product_tmpl_id_configurator()
        if not self.product_id and self.product_tmpl_id:
            self.product_id = self.product_tmpl_id._product_from_tmpl()
            # HACK: With NewId, the `search` method that looks for vendor pricelists
            # related to the product is unable to find the linked template as the
            # id returns something like `NewId origin: <ID>`. So we'll ensure the
            # proper link overriding the supplier search by context. If Odoo fixes
            # `_prepare_sellers` method to avoid this issue, this won't be necessary
            # anymore
            self.with_context(
                pvc_product_tmpl=self.product_tmpl_id.id
            ).onchange_product_id()
        return res

    @api.model
    def _get_product_description(self, template, product, product_attributes):
        """Add description_purchase to name field (similar to what purchase does)."""
        name = super()._get_product_description(
            template=template, product=product, product_attributes=product_attributes
        )
        if template.description_purchase:
            name += "\n" + template.description_purchase
        return name

    @api.model_create_multi
    def create(self, vals_list):
        """Create variant before calling super when the purchase order is
        confirmed, as it creates associated stock moves.
        """
        for vals in vals_list:
            if vals.get("order_id") and not vals.get("product_id"):
                order = self.env["purchase.order"].browse(vals["order_id"])
                if order.state == "purchase":
                    line = self.new(vals)
                    product = line.create_variant_if_needed()
                    vals["product_id"] = product.id
        return super().create(vals_list)
