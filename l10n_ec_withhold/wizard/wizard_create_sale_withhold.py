from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizarWithhold(models.TransientModel):
    _name = "l10n_ec.wizard.create.sale.withhold"

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
    )
    issue_date = fields.Date(
        string="Fecha de retencion",
        required=True,
    )
    journal_id = fields.Many2one(comodel_name="account.journal", string="Diario")
    document_number = fields.Char(
        string="Numero de Retencion",
        required=True,
        size=17,
    )
    electronic_authorization = fields.Char(
        string="Electronic authorization",
        size=49,
        required=True,
    )
    withhold_totals = fields.Float(
        string="Total retenido", compute="_compute_total_withhold", store=True
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Related Document",
        readonly=True,
    )
    withhold_line_ids = fields.One2many(
        comodel_name="l10n_ec.wizard.create.sale.withhold.line",
        inverse_name="withhold_id",
        string="Lines",
        required=True,
    )

    @api.depends("withhold_line_ids.withhold_amount")
    def _compute_total_withhold(self):
        for record in self:
            record.withhold_totals = sum(
                record.withhold_line_ids.mapped("withhold_amount")
            )

    def create_move(self):
        """
        Generacion de asiento contable para aplicar como
        pago a factura relacionada
        """

        inv = self.invoice_id
        move_data = {
            "journal_id": self.journal_id.id,
            "name": self.document_number,
            "ref": "RET " + self.document_number,
            "date": self.issue_date,
            "l10n_ec_electronic_authorization": self.electronic_authorization,
            "move_type": "entry",
            "invoice_origin": inv.id,
            "l10n_latam_document_type_id": self.env.ref("l10n_ec_withhold.ec_dt_07").id,
            "partner_id": self.partner_id.id,
        }
        total_counter = 0
        lines = []
        for line in self.withhold_line_ids:

            lines.append(
                (
                    0,
                    0,
                    {
                        "partner_id": self.partner_id.id,
                        "quantity": 1.0,
                        "price_unit": abs(line.withhold_amount),
                        "account_id": line.account_tax_withhold,
                        "name": "RET " + self.document_number,
                        "debit": abs(line.withhold_amount),
                        "credit": 0.00,
                        "tax_ids": [(4, line.tax_withhold_id.id)],
                        "tax_tag_ids": [(4, line.tax_withhold_id.id)],
                        "tax_base_amount": line.base_amount,
                    },
                )
            )
            total_counter += abs(line.withhold_amount)

        lines.append(
            (
                0,
                0,
                {
                    "partner_id": self.partner_id.id,
                    "account_id": inv.partner_id.property_account_receivable_id.id,
                    "name": "RET " + str(self.document_number),
                    "debit": 0.00,
                    "credit": total_counter,
                },
            )
        )

        move_data.update({"line_ids": lines})
        move = self.env["account.move"].create(move_data)
        acctype = "receivable"
        inv_lines = inv.line_ids
        acc2rec = inv_lines.filtered(
            lambda l: l.account_id.internal_type == acctype
        )  # noqa
        acc2rec += move.line_ids.filtered(
            lambda l: l.account_id.internal_type == acctype
        )  # noqa
        # self.write({'move_ret_id': move.id})
        move.post()
        acc2rec.reconcile()

        withholding_lines = move.line_ids.filtered(lambda l: l.tax_ids)
        for line in withholding_lines:
            line.l10n_ec_withhold_id = move.id

        return True

    def button_validate(self):
        """
        Botón de validación de Retención que se usa cuando
        se creó una retención manual, esta se relacionará
        con la factura seleccionada.
        """
        for ret in self:
            if not ret.withhold_line_ids:
                raise UserError(_("No ha aplicado impuestos."))
            # self.action_validate(self.document_number)
            if self.invoice_id.move_type == "out_invoice":
                self.create_move()

        return True


class WizarWithholdLine(models.TransientModel):
    _name = "l10n_ec.wizard.create.sale.withhold.line"

    tax_group_withhold_id = fields.Many2one(
        comodel_name="account.tax.group",
        string="Withholding Type",
        domain="[('l10n_ec_type', 'in', ['withhold_vat', 'withhold_income_tax'])]",
    )
    tax_withhold_id = fields.Many2one(
        comodel_name="account.tax",
        string="Impuesto de retencion",
        domain="[('tax_group_id', '=', tax_group_withhold_id), ('type_tax_use', '=', 'sale')]",
    )
    base_amount = fields.Float(
        string="Monto base", store=True, compute="_compute_valor_base"
    )
    withhold_amount = fields.Float(
        string="Monto retenido", store=True, compute="_compute_valor_withhold"
    )
    account_tax_withhold = fields.Integer(compute="_compute_get_account", store=False)
    account_tax_tag_withhold = fields.Integer(compute="_compute_get_tax", store=False)
    withhold_id = fields.Many2one(
        comodel_name="l10n_ec.wizard.create.sale.withhold",
        string="Withhold",
        ondelete="cascade",
    )

    @api.depends("withhold_id", "tax_withhold_id", "base_amount")
    def _compute_valor_base(self):
        for line in self:
            line.base_amount = 0.0
            if line.tax_withhold_id.tax_group_id.l10n_ec_type == "withhold_income_tax":
                line.base_amount = abs(
                    line.withhold_id.invoice_id.amount_untaxed_signed
                )
            elif line.tax_withhold_id.tax_group_id.l10n_ec_type == "withhold_vat":
                line.base_amount = abs(line.withhold_id.invoice_id.amount_tax_signed)

    @api.depends("base_amount", "withhold_amount")
    def _compute_valor_withhold(self):
        for amount_base in self:
            amount_base.withhold_amount = (
                amount_base.base_amount * amount_base.tax_withhold_id.amount / 100
            )
            amount_base.withhold_amount = abs(round(amount_base.withhold_amount, 2))

    @api.depends("tax_withhold_id")
    def _compute_get_account(self):
        for account in self:
            account_tax = account.tax_withhold_id.invoice_repartition_line_ids
            for repartition_line in account_tax:
                if repartition_line.repartition_type == "tax":
                    account.account_tax_withhold = repartition_line.account_id
                    break
            else:
                raise UserError(_("No se encontró una cuenta de impuestos"))

    @api.depends("tax_withhold_id")
    def _compute_get_tax(self):
        for tax in self:
            tax_id = tax.tax_withhold_id.id
            tax.account_tax_tag_withhold = (4, tax_id)

    @api.onchange("tax_group_withhold_id")
    def onchange_tax_group_withhold(self):
        self.tax_withhold_id = False
