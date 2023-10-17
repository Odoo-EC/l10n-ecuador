import re
from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_ec_type_credit_note = fields.Selection(
        [("discount", "Discount"), ("return", "Return")], string="Credit Note type"
    )
