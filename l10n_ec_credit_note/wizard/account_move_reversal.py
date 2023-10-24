import re
from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_ec_type_credit_note = fields.Selection(
        [("discount", "Discount"), ("return", "Return")], string="Credit Note type"
    )

    def reverse_moves(self):
        if self.company_id.account_fiscal_country_id.code == "EC":
            return super(AccountInvoiceRefund, self.with_context(l10n_ec_manage_credit_note=True)).reverse_moves()
        return super().reverse_moves()

    def _prepare_default_reversal(self, move):
        move_vals = super(AccountInvoiceRefund, self)._prepare_default_reversal(move)
        if self.env.context.get("l10n_ec_manage_credit_note"):
            move_vals.update(
                {
                    "l10n_ec_type_credit_note": self.l10n_ec_type_credit_note,
                }
            )
        return move_vals
