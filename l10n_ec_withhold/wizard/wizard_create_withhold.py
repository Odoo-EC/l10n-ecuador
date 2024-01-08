import datetime
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.data import TAX_SUPPORT


class WizardCreateWithhold(models.TransientModel):
    _name = "l10n_ec.wizard.create.withhold"
    _description = "Wizard withhold"

    issue_date = fields.Date(
        string="Date",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        default=lambda self: self._get_default_journal(),
    )
    document_number = fields.Char(
        required=False,
        size=17,
    )
    electronic_authorization = fields.Char(
        size=49,
        required=False,
    )

    withhold_line_ids = fields.One2many(
        comodel_name="l10n_ec.wizard.create.withhold.line",
        inverse_name="withhold_id",
        string="Lines",
        required=True,
    )
    withhold_totals = fields.Float(compute="_compute_total_withhold", store=True)

    def _get_default_journal(self):
        return self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("l10n_ec_withholding_type", "=", self._context.get("type")),
            ],
            limit=1,
        )

    @api.depends("withhold_line_ids.withhold_amount")
    def _compute_total_withhold(self):
        for record in self:
            record.withhold_totals = round(
                sum(record.withhold_line_ids.mapped("withhold_amount")), 2
            )

    @api.onchange("electronic_authorization")
    def onchange_authorization(self):
        self.ensure_one()
        if self.electronic_authorization:
            if len(self.electronic_authorization) == 49:
                if self.electronic_authorization[8:10] == "07":
                    self.issue_date = self.extract_date_from_authorization()
                    self.document_number = (
                        self.extract_document_number_from_authorization()
                    )
                else:
                    raise UserError(
                        _("Authorization number not correspond to a withhold")
                    )

    @api.onchange("document_number")
    def onchange_document_number(self):
        if self.document_number:
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

    def extract_date_from_authorization(self):
        return datetime.datetime.strptime(
            self.electronic_authorization[0:8], "%d%m%Y"
        ).date()

    def extract_document_number_from_authorization(self):
        series_number = self.electronic_authorization[24:39]
        return f"{series_number[0:3]}-{series_number[3:6]}-{series_number[6:15]}"

    def button_validate(self):
        """
        Create a Sale Withholding and try reconcile with invoice
        """
        self.ensure_one()

        withhold_vals = {
            "tipo": self._context.get("type"),
            "journal_id": self.journal_id.id,
            "number": self.document_number,
            "date": self.issue_date,
            "authorization": self.electronic_authorization,
            "invoice_id": self._context.get("move_id"),
            "total_withhold": self.withhold_totals,
        }

        lines = []
        for line in self.withhold_line_ids:
            taxes_vals = {
                "tax_group_withhold_id": line.tax_group_withhold_id.id,
                "tax_withhold_id": line.tax_withhold_id.id,
                "base_amount": line.base_amount,
                "withhold_amount": line.withhold_amount,
                "l10n_ec_tax_support": line.l10n_ec_tax_support,
            }
            lines.append(taxes_vals)

        withhold_vals.update({"lines": lines})

        self.env["account.move"].create_withhold(withhold_vals)

        return True


class WizardCreateSaleWithholdLine(models.TransientModel):
    _name = "l10n_ec.wizard.create.withhold.line"
    _description = "Wizard Withhold line"

    withhold_id = fields.Many2one(
        comodel_name="l10n_ec.wizard.create.withhold",
        string="Withhold",
        ondelete="cascade",
    )

    tax_group_withhold_id = fields.Many2one(
        comodel_name="account.tax.group",
        string="Withholding Type",
    )
    tax_withhold_id = fields.Many2one(
        comodel_name="account.tax",
        string="Withholding tax",
    )
    base_amount = fields.Float(string="Amount Base", readonly=True)
    withhold_amount = fields.Float(
        string="Amount Withhold",
    )
    l10n_ec_tax_support = fields.Selection(
        TAX_SUPPORT,
        string="Tax Support",
        copy=False,
        default=lambda self: self._context.get("tax_support"),
    )

    @api.onchange("base_amount", "tax_withhold_id")
    def _onchange_withholding_amount(self):
        for line in self:
            line.withhold_amount = round(
                abs(line.base_amount * line.tax_withhold_id.amount / 100), 2
            )

    @api.onchange("tax_group_withhold_id")
    def _onchange_withholding_base(self):
        for line in self:
            if line.tax_group_withhold_id.l10n_ec_type in [
                "withhold_income_sale",
                "withhold_income_purchase",
            ]:
                line.base_amount = self._context.get("move_amount_untaxed", 0)
            elif line.tax_group_withhold_id.l10n_ec_type in [
                "withhold_vat_sale",
                "withhold_vat_purchase",
            ]:
                line.base_amount = self._context.get("move_amount_iva", 0)
