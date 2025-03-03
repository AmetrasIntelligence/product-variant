# Copyright 2014-2016 Oihane Crucelaegui - AvanzOSC
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# Copyright 2015-2021 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - Carolina Fernandez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Sale - Product variants",
    "summary": "Product variants in sale management",
    "version": "16.0.1.0.2",
    "development_status": "Production/Stable",
    "license": "AGPL-3",
    "depends": ["sale", "product_variant_configurator"],
    "author": "OdooMRP team,"
    "AvanzOSC,"
    "Tecnativa,"
    "Odoo Community Association (OCA)",
    "category": "Sales Management",
    "website": "https://github.com/OCA/product-variant",
    "data": ["views/sale_view.xml"],
    "installable": True,
    "post_init_hook": "assign_product_template",
}
