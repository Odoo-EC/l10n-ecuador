from odoo import _, fields, models
from .data import TAX_SUPPORT


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ec_withhold_related = fields.Boolean(
        string="Agente de retencion?", help="Seleccionar si es agente de retencion"
    )

    l10n_ec_tax_support = fields.Selection(
        TAX_SUPPORT,
        string=_('Tax Support'),
        help=_('Tax support in invoice line')
    )
