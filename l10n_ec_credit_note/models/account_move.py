import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ec_type_credit_note = fields.Selection(
        [("discount", "Discount"), ("return", "Return")],
        string="Credit note type",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default="discount",
    )

    def action_reverse(self):
        action = super(AccountMove, self).action_reverse()
        if self.company_id.account_fiscal_country_id.code == "EC":
            if self.move_type == "out_invoice":
                action["views"] = [(self.env.ref("l10n_ec_credit_note.view_account_invoice_refund_sale").id, "form")]
        return action
