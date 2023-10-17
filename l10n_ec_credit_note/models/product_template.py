from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # campos para NC
    l10n_ec_property_account_discount_id = fields.Many2one(
        "account.account",
        "C.C. Discount",
        company_dependent=True,
        track_visibility="onchange",
    )
    l10n_ec_property_account_return_id = fields.Many2one(
        "account.account",
        "C.C. Refund",
        company_dependent=True,
        track_visibility="onchange",
    )
