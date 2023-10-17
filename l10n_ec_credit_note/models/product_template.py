from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # campos para NC
    property_stock_account_discount_id = fields.Many2one(
        "account.account",
        "C.C. Discount",
        company_dependent=True,
        track_visibility="onchange",
    )
    property_stock_account_refund_id = fields.Many2one(
        "account.account",
        "C.C. Refund",
        company_dependent=True,
        track_visibility="onchange",
    )
