from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    # campos para NC
    l10n_ec_property_account_discount_id = fields.Many2one(
        "account.account",
        "C.C. Discount",
        company_dependent=True,
        tracking=True,
    )
    l10n_ec_property_account_return_id = fields.Many2one(
        "account.account",
        "C.C. Refund",
        company_dependent=True,
        tracking=True,
    )
