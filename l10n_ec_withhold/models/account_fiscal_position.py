from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ec_withhold = fields.Boolean(
        string="Requiere Retenciones ?", help="Selecionar si la posición fiscal requiere retenciones"
    )
