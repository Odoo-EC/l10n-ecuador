import datetime
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardCreateSaleWithhold(models.TransientModel):
    _inherit = "l10n_ec.wizard.abstract.withhold"
    _name = "l10n_ec.wizard.create.sale.withhold"
    _description = "Wizard Sale withhold"

    withhold_line_ids = fields.One2many(
        comodel_name="l10n_ec.wizard.create.sale.withhold.line",
        inverse_name="withhold_id",
        string="Lines",
        required=True,
    )
    withhold_totals = fields.Float(compute="_compute_total_withhold", store=True)

    invoice_ids = fields.Many2many(comodel_name="account.move", string="Invoice")

    @api.model
    def default_get(self, fields):

        defaults = super().default_get(fields)

        invoices = self.env["account.move"].browse(self.env.context.get("active_ids"))

        if len(invoices.partner_id) > 1:
            raise UserError(_("Choose a multiple invoices of a same customer"))

        defaults["invoice_ids"] = [(6, 0, self.env.context.get("active_ids", []))]
        defaults["partner_id"] = invoices.partner_id.id

        return defaults

    @api.depends("withhold_line_ids.withhold_amount")
    def _compute_total_withhold(self):
        for record in self:
            record.withhold_totals = sum(
                record.withhold_line_ids.mapped("withhold_amount")
            )

    def _prepare_withholding_vals(self):
        withholding_vals = super()._prepare_withholding_vals()
        withholding_vals["l10n_ec_withholding_type"] = "sale"
        return withholding_vals

    @api.onchange("electronic_authorization")
    def onchange_authorization(self):
        if self.electronic_authorization is not False:
            if len(self.electronic_authorization) == 49:
                self.issue_date = self.extract_date_from_authorization()
                self.document_number = self.extract_document_number_from_authorization()

    @api.onchange("document_number")
    def onchange_document_number(self):
        if self.document_number is not False:
            self.document_number = self._format_document_number(self.document_number)

    def _format_document_number(self, document_number):
        document_number = re.sub(r"\s+", "", document_number)  # remove any whitespace
        num_match = re.match(r"(\d{1,3})-(\d{1,3})-(\d{1,9})", document_number)
        if num_match:
            # Fill each number group with zeroes (3, 3 and 9 respectively)
            document_number = "-".join(
                [n.zfill(3 if i < 2 else 9) for i, n in enumerate(num_match.groups())]
            )
        else:
            raise UserError(
                _("Ecuadorian Document %s must be like 001-001-123456789")
                % (document_number)
            )

        return document_number

    def validate_authorization(self):
        authorization_len = len(self.electronic_authorization)
        if authorization_len not in [10, 49]:
            raise UserError(
                _("Authorization is not valid. Should be length equal to 10 or 49")
            )

    def validate_repeated_invoice(self):
        for line in self.withhold_line_ids:
            result = self.env["account.move.line"].search(
                [("l10n_ec_invoice_withhold_id", "=", line.invoice_id.id)]
            )
            if len(result) > 0:
                raise UserError(
                    _(
                        f"Invoice {line.invoice_id.name} already exist in withhold "
                        f"{result.move_id.name}"
                    )
                )

    def extract_date_from_authorization(self):
        return datetime.datetime.strptime(
            self.electronic_authorization[0:8], "%d%m%Y"
        ).date()

    def extract_document_number_from_authorization(self):
        series_number = self.electronic_authorization[24:39]
        return "{}-{}-{}".format(
            series_number[0:3], series_number[3:6], series_number[6:15]
        )

    def button_validate(self):
        """
        Create a Sale Withholding and try reconcile with invoice
        """
        self.ensure_one()
        self.validate_authorization()
        self.validate_repeated_invoice()
        if not self.withhold_line_ids:
            raise UserError(_("Please add some withholding lines before continue"))

        withholding_vals = self._prepare_withholding_vals()
        total_counter = 0
        lines = []
        for line in self.withhold_line_ids:
            taxes_vals = line._get_withholding_line_vals(self)
            for tax_vals in taxes_vals:
                lines.append((0, 0, tax_vals))
                if tax_vals.get("tax_tag_ids"):
                    total_counter += abs(tax_vals.get("price_unit"))

        lines.append(
            (
                0,
                0,
                {
                    "partner_id": self.partner_id.id,
                    "account_id": self.partner_id.property_account_receivable_id.id,
                    "name": "RET " + str(self.document_number),
                    "debit": 0.00,
                    "credit": 0.00,  # total_counter,
                },
            )
        )

        withholding_vals.update({"line_ids": lines})
        new_withholding = self.env["account.move"].create(withholding_vals)
        new_withholding.action_post()
        self._try_reconcile_withholding_moves(new_withholding, "receivable")
        return True


class WizardCreateSaleWithholdLine(models.TransientModel):
    _inherit = "l10n_ec.wizard.abstract.withhold.line"
    _name = "l10n_ec.wizard.create.sale.withhold.line"
    _description = "Wizard Sale withhold line"

    withhold_id = fields.Many2one(
        comodel_name="l10n_ec.wizard.create.sale.withhold",
        string="Withhold",
        ondelete="cascade",
    )
