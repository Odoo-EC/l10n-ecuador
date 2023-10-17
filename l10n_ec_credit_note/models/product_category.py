from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

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
