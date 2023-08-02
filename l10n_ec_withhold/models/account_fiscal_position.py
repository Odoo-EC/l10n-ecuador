from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ec_withhold = fields.Boolean(
        string="Requires retentions ?",
        help="Select if the tax position requires withholding",
    )
