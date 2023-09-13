from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardCreatePurchaseWithhold(models.TransientModel):
    _inherit = "l10n_ec.wizard.abstract.withhold"
    _name = "l10n_ec.wizard.create.purchase.withhold"
    _description = "Wizard Purchase withhold"

    withhold_line_ids = fields.One2many(
        comodel_name="l10n_ec.wizard.create.purchase.withhold.line",
        inverse_name="withhold_id",
        string="Lines",
        required=True,
    )
    withhold_totals = fields.Float(compute="_compute_total_withhold", store=True)

    @api.depends("withhold_line_ids.withhold_amount")
    def _compute_total_withhold(self):
        for record in self:
            record.withhold_totals = sum(
                record.withhold_line_ids.mapped("withhold_amount")
            )

    def _prepare_withholding_vals(self):
        withholding_vals = super()._prepare_withholding_vals()
        withholding_vals["l10n_ec_withholding_type"] = "purchase"
        return withholding_vals

    def button_validate(self):
        """
        Create a purchase Withholding and try reconcile with invoice
        """
        self.ensure_one()
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
                    "account_id": self.partner_id.property_account_payable_id.id,
                    "name": "RET " + str(self.document_number),
                    "debit": total_counter,
                    "credit": 0.0,
                },
            )
        )

        withholding_vals.update({"line_ids": lines})
        new_withholding = self.env["account.move"].create(withholding_vals)
        new_withholding.post()
        invoices = self.withhold_line_ids.invoice_id
        invoices.write({"l10n_ec_withhold_ids": [(4, new_withholding.id)]})
        self._try_reconcile_withholding_moves(new_withholding, invoices, "payable")
        return True


class WizardPurchaseWithholdLine(models.TransientModel):
    _inherit = "l10n_ec.wizard.abstract.withhold.line"
    _name = "l10n_ec.wizard.create.purchase.withhold.line"
    _description = "Wizard Purchase withhold line"

    withhold_id = fields.Many2one(
        comodel_name="l10n_ec.wizard.create.purchase.withhold",
        string="Withhold",
        ondelete="cascade",
    )
