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

    def _reverse_move_vals(self, default_values, cancel=True):
        move_vals = super()._reverse_move_vals(default_values, cancel)
        if self.env.context.get("l10n_ec_manage_credit_note") and default_values['l10n_ec_type_credit_note']:
            for line_vals in move_vals['line_ids']:
                line_dict = line_vals[2]
                if 'product_id' in line_dict:
                    account_id = self._get_account_product_line(line_dict['product_id'],
                                                                default_values['l10n_ec_type_credit_note'])
                    if account_id:
                        line_dict['account_id'] = account_id
        return move_vals

    @api.model
    def _get_account_product_line(self, product_id, l10n_ec_type_credit_note):
        account_id = False
        if product_id:
            product = self.env['product.product'].browse(product_id)
            if l10n_ec_type_credit_note == "return" and product.l10n_ec_property_account_return_id:
                account_id = product.l10n_ec_property_account_return_id.id
            elif l10n_ec_type_credit_note == "discount" and product.l10n_ec_property_account_discount_id:
                account_id = product.l10n_ec_property_account_discount_id.id
            if not account_id:
                if product.categ_id:
                    if l10n_ec_type_credit_note == "return" and product.categ_id.l10n_ec_property_account_return_id:
                        account_id = product.categ_id.l10n_ec_property_account_return_id.id
                    elif l10n_ec_type_credit_note == "discount" and product.categ_id.l10n_ec_property_account_discount_id:
                        account_id = product.categ_id.l10n_ec_property_account_discount_id.id
            if not account_id and self.company_id:
                if product.categ_id:
                    if l10n_ec_type_credit_note == "return" and self.company_id.l10n_ec_property_account_return_id:
                        account_id = self.company_id.l10n_ec_property_account_return_id.id
                    elif l10n_ec_type_credit_note == "discount" and self.company_id.l10n_ec_property_account_discount_id:
                        account_id = self.company_id.l10n_ec_property_account_discount_id.id
        return account_id
