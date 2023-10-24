import logging

from odoo import api, fields, models

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
                action["views"] = [
                    (
                        self.env.ref(
                            "l10n_ec_credit_note.view_account_invoice_refund_sale"
                        ).id,
                        "form",
                    )
                ]
        return action

    def _reverse_move_vals(self, default_values, cancel=True):
        l10n_ec_type_credit_note = default_values["l10n_ec_type_credit_note"]
        move_vals = super()._reverse_move_vals(default_values, cancel)
        if (
            self.env.context.get("l10n_ec_manage_credit_note")
            and default_values["l10n_ec_type_credit_note"]
        ):
            move_vals_remove = []
            for line_vals in move_vals["line_ids"]:
                line_dict = line_vals[2]
                if (
                    "exclude_from_invoice_tab" in line_dict
                    and not line_dict["exclude_from_invoice_tab"]
                ):
                    account_id = self._get_account_product_line(
                        line_dict["product_id"], l10n_ec_type_credit_note
                    )
                    # TODO: Respetar cuando es venta
                    if account_id:
                        line_dict["account_id"] = account_id
                if (
                    "is_anglo_saxon_line" in line_dict
                    and line_dict["is_anglo_saxon_line"]
                    and l10n_ec_type_credit_note == "discount"
                ):
                    move_vals_remove.append(line_vals)
            for line_vals in move_vals_remove:
                move_vals["line_ids"].remove(line_vals)
        return move_vals

    @api.model
    def _get_account_product_line(self, product_id, l10n_ec_type_credit_note):
        account_id = False
        if product_id:
            product = self.env["product.product"].browse(product_id)
            if (
                l10n_ec_type_credit_note == "return"
                and product.l10n_ec_property_account_return_id
            ):
                account_id = product.l10n_ec_property_account_return_id.id
            elif (
                l10n_ec_type_credit_note == "discount"
                and product.l10n_ec_property_account_discount_id
            ):
                account_id = product.l10n_ec_property_account_discount_id.id
            if not account_id:
                if product.categ_id:
                    if (
                        l10n_ec_type_credit_note == "return"
                        and product.categ_id.l10n_ec_property_account_return_id
                    ):
                        account_id = (
                            product.categ_id.l10n_ec_property_account_return_id.id
                        )
                    elif (
                        l10n_ec_type_credit_note == "discount"
                        and product.categ_id.l10n_ec_property_account_discount_id
                    ):
                        account_id = (
                            product.categ_id.l10n_ec_property_account_discount_id.id
                        )
        if (not account_id and self.company_id) or (not product_id and self.company_id):
            if (
                l10n_ec_type_credit_note == "return"
                and self.company_id.l10n_ec_property_account_return_id
            ):
                account_id = self.company_id.l10n_ec_property_account_return_id.id
            elif (
                l10n_ec_type_credit_note == "discount"
                and self.company_id.l10n_ec_property_account_discount_id
            ):
                account_id = self.company_id.l10n_ec_property_account_discount_id.id
        return account_id

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        discount_credit_notes = self.filtered(
            lambda x: (
                x.move_type in ["in_refund", "out_refund"]
                and x.l10n_ec_type_credit_note == "discount"
            )
        )

        return super(
            AccountMove, self - discount_credit_notes
        )._stock_account_prepare_anglo_saxon_out_lines_vals()
