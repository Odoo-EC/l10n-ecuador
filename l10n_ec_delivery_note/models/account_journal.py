from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_latam_internal_type = fields.Selection(
        selection_add=[
            ("delivery_note", "Delivery Note"),
        ],
    )
