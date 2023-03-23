from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ec_withhold_related = fields.Boolean(
        string="Agente de retencion?", help="Seleccionar si es agente de retencion"
    )
