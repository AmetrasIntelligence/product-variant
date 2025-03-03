# © 2014-2016 Oihane Crucelaegui - AvanzOSC
# © 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2024 Tecnativa - Carolina Fernandez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        """Create possible product variants not yet created."""
        lines_without_product = self.mapped("order_line").filtered(
            lambda x: not x.product_id and x.product_tmpl_id
        )
        for line in lines_without_product:
            line.create_variant_if_needed()
        return super()._action_confirm()


class SaleOrderLine(models.Model):
    _inherit = ["sale.order.line", "product.configurator"]
    _name = "sale.order.line"
    _partner_id_field = "order_partner_id"

    product_tmpl_id = fields.Many2one(
        store=True,
        readonly=False,
        related=False,
        string="Product Template (no related)",
    )
    product_id = fields.Many2one(required=False)
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
            "CHECK(display_type IS NOT NULL OR "
            "((product_id IS NOT NULL OR product_tmpl_id IS NOT NULL) AND "
            "product_uom IS NOT NULL))",
            "Missing required fields on accountable sale order line.",
        ),
        (
            "non_accountable_null_fields",
            "CHECK(display_type IS NULL OR "
            "(product_id IS NULL AND product_tmpl_id IS NULL AND "
            "price_unit = 0 AND product_uom_qty = 0 AND "
            "product_uom IS NULL AND customer_lead = 0))",
            "Forbidden values on non-accountable sale order line",
        ),
    ]

    @api.depends("product_tmpl_id")
    def _compute_product_uom(self):
        lines_with_template = self.filtered(
            lambda x: x.product_tmpl_id and not x.product_id
        )
        for line in lines_with_template:
            # This condition is intended to set the value in a way similar to
            # what the _compute_product_uom() method of the sale module does.
            if not line.product_uom or (
                line.product_tmpl_id.uom_id.id != line.product_uom.id
            ):
                line.product_uom = line.product_tmpl_id.uom_id
        return super(SaleOrderLine, self - lines_with_template)._compute_product_uom()

    @api.depends("product_tmpl_id", "product_id")
    def _compute_product_uom_category_id(self):
        """This compute is intended to do something similar to the related of the
        sale module product_id.uom_id.category_id but adding the casuistry of the
        product_tmpl_id field.
        """
        for line in self:
            product = line.product_id or line.product_tmpl_id
            if product:
                line.product_uom_category_id = product.uom_id.category_id
            else:
                line.product_uom_category_id = line.product_uom_category_id

    @api.model_create_multi
    def create(self, vals_list):
        """Create product if not exist when the sales order is already
        confirmed and a line is added.
        """
        for vals in vals_list:
            if (
                vals.get("order_id")
                and not vals.get("product_id")
                and not vals.get("is_downpayment")
            ):
                order = self.env["sale.order"].browse(vals["order_id"])
                if order.state == "sale":
                    line = self.new(vals)
                    product = line.create_variant_if_needed()
                    vals["product_id"] = product.id
        return super().create(vals_list)

    @api.model
    def _get_product_description(self, template, product, product_attributes):
        res = super()._get_product_description(
            template=template, product=product, product_attributes=product_attributes
        )
        product = self.product_id.with_context(lang=self.order_partner_id.lang)
        if product.description_sale:
            res = (res or "") + "\n" + product.description_sale
        return res

    @api.depends("product_attribute_ids")
    def _compute_price_unit(self):
        """Add the proper dependency to compute the price correctly."""
        return super()._compute_price_unit()
