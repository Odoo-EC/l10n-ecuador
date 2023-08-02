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

    def button_validate(self):
        """
        Create a Sale Withholding and try reconcile with invoice
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
                    "account_id": self.partner_id.property_account_receivable_id.id,
                    "name": "RET " + str(self.document_number),
                    "debit": 0.00,
                    "credit": total_counter,
                },
            )
        )

        withholding_vals.update({"line_ids": lines})
        new_withholding = self.env["account.move"].create(withholding_vals)
        new_withholding.post()
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
