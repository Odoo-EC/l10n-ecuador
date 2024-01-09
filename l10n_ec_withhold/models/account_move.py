import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .data import TAX_SUPPORT

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ec_withholding_type = fields.Selection(
        [
            ("purchase", "Purchase"),
            ("sale", "Sale"),
        ],
        string="Withholding Type",
    )
    l10n_ec_withhold_line_ids = fields.One2many(
        comodel_name="l10n_ec.withhold.line",
        inverse_name="withhold_id",
        string="Lineas de retencion",
    )
    l10n_ec_withhold_ids = fields.Many2many(
        "account.move",
        relation="l10n_ec_withhold_invoice_rel",
        column1="move_id",
        column2="withhold_id",
        string="Withhold",
        readonly=True,
        copy=False,
    )
    l10n_ec_withhold_count = fields.Integer(
        string="Withholds Count", compute="_compute_l10n_ec_withhold_count"
    )
    l10n_ec_withhold_active = fields.Boolean(
        string="Withholds?",
        compute="_compute_l10n_ec_withhold_active",
        store=True,
    )
    l10n_ec_tax_support = fields.Selection(
        TAX_SUPPORT, string="Tax Support", help="Tax support in withhold line"
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        self.l10n_ec_tax_support = self._get_l10n_ec_tax_support()
        return super()._onchange_partner_id()

    @api.depends("l10n_ec_withhold_ids")
    def _compute_l10n_ec_withhold_count(self):
        for move in self:
            move.l10n_ec_withhold_count = len(move.l10n_ec_withhold_ids)

    @api.depends(
        "state",
        "fiscal_position_id",
        "company_id",
    )
    def _compute_l10n_ec_withhold_active(self):
        """
        Compute when the user can input withholding.
        By default, if the company is Ecuadorian and this module is installed,
        this feature is enabled.
        However, if withholding is explicitly configured
        as disabled in the tax position, then disable this feature.
        """
        for move in self:
            move_fiscal_position = move.fiscal_position_id
            company_fiscal_position = move.company_id.property_account_position_id
            if (
                move.state != "posted"
                or move.move_type
                not in [
                    "in_invoice",
                    "out_invoice",
                ]
                or move.tax_country_code != "EC"
            ):
                move.l10n_ec_withhold_active = False
                continue
            move.l10n_ec_withhold_active = True
            if (
                move.move_type == "out_invoice"
                and move_fiscal_position.l10n_ec_avoid_withhold
            ):
                move.l10n_ec_withhold_active = False
            if move.move_type == "in_invoice" and (
                move_fiscal_position.l10n_ec_avoid_withhold
                or company_fiscal_position.l10n_ec_avoid_withhold
            ):
                move.l10n_ec_withhold_active = False

    @api.constrains("l10n_ec_withholding_type")
    def _check_l10n_ec_sale_withholding_duplicity(self):
        for move in self:
            if not move.is_sale_withhold():
                continue
            other_withholdings = self.search_count(
                [
                    ("partner_id", "=", move.partner_id.id),
                    ("ref", "=", move.ref),
                    ("l10n_ec_withholding_type", "=", "sale"),
                ]
            )
            if other_withholdings > 1:
                raise UserError(
                    _(
                        "You can't create other withholding with same Number: %s for Customer: %s",
                        move.ref,
                        move.partner_id.display_name,
                    )
                )

    # Sobreescribo para cambiar el nombre que se muestra en la lista de pagos pendientes
    def _compute_payments_widget_to_reconcile_info(self):
        super()._compute_payments_widget_to_reconcile_info()
        for move in self:
            payments_widget_vals = move.invoice_outstanding_credits_debits_widget
            if not payments_widget_vals:
                continue

            for p_l in payments_widget_vals.get("content", []):
                o = self.browse(p_l["move_id"])
                p_l["name"] = o.name

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals

    def _post(self, soft=True):
        # OVERRIDE
        # Set the electronic document to be posted and post immediately for synchronous formats.
        # only for purchase withhold
        posted = super()._post(soft=soft)
        for move in posted:
            # check if tax support is set into any invoice line or invoice
            if move.is_purchase_document() and move.l10n_ec_withhold_active:
                lines_without_tax_support = (
                    any(
                        not invoice_line.l10n_ec_tax_support
                        for invoice_line in move.l10n_ec_withhold_line_ids
                    )
                    if move.l10n_ec_withhold_line_ids
                    else True
                )

                if not move.l10n_ec_tax_support and lines_without_tax_support:
                    raise UserError(
                        _(
                            "Please fill a Tax Support on Invoice: %s or on all Invoice lines"
                        )
                        % (move.display_name)
                    )
        return posted

    def button_cancel(self):
        res = super().button_cancel()
        # cancel purchase withholding
        for move in self:
            for withhold in move.l10n_ec_withhold_ids:
                if withhold.is_purchase_withhold():
                    withhold.button_cancel()
        return res

    def action_send_and_print(self):
        if any(move.is_purchase_withhold() for move in self):
            template = self.env.ref(self._get_mail_template(), raise_if_not_found=False)
            return {
                "name": _("Send"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "account.move.send",
                "target": "new",
                "context": {
                    "active_ids": self.ids,
                    "default_mail_template_id": template.id,
                },
            }
        return super().action_send_and_print()

    @api.model
    def get_withhold_types(self):
        return ["purchase", "sale"]

    def is_withhold(self):
        return (
            self.tax_country_code == "EC"
            and self.l10n_latam_internal_type == "withhold"
            and self.l10n_ec_withholding_type in self.get_withhold_types()
        )

    def is_purchase_withhold(self):
        return self.l10n_ec_withholding_type == "purchase" and self.is_withhold()

    def is_sale_withhold(self):
        return self.l10n_ec_withholding_type == "sale" and self.is_withhold()

    def action_try_create_ecuadorian_withhold(self):
        action = {}
        if any(
            move.is_purchase_document() and move.l10n_ec_withhold_active
            for move in self
        ):
            if len(self) > 1:
                raise UserError(
                    _(
                        "You can't create Withhold for some invoice, "
                        "Please select only a Invoice."
                    )
                )
            action = self._action_create_purchase_withhold_wizard()
        elif any(
            move.is_sale_document() and move.l10n_ec_withhold_active for move in self
        ):
            action = self._action_create_sale_withhold_wizard()
        else:
            raise UserError(
                _(
                    "Please select only invoice "
                    "what satisfies the requirements for create withhold"
                )
            )
        return action

    # Devuelve el valor total del IVA en la factura
    # Busca en el diccionario de 'tax_totals' los valores de los grupos que se llamen 'IVA'
    def get_tax_iva_total(self):
        self.ensure_one()
        tax_totals = dict(self.tax_totals if self.tax_totals else {})
        groups_by_subtotal = tax_totals.get("groups_by_subtotal", {})
        iva_total = 0
        for v in groups_by_subtotal.values():
            tax_group_list = list(v) or []
            for tax_group in tax_group_list:
                if "IVA" in tax_group.get("tax_group_name", "").upper():
                    iva_total += tax_group.get("tax_group_amount", 0.0)
        return abs(iva_total)

    def _action_create_sale_withhold_wizard(self):
        self.ensure_one()
        return self._action_create_withhold_wizard("sale")

    def _action_create_purchase_withhold_wizard(self):
        self.ensure_one()
        return self._action_create_withhold_wizard("purchase")

    def _action_create_withhold_wizard(self, tipo):
        self.ensure_one()

        action = self.env.ref(
            "l10n_ec_withhold.l10n_ec_wizard_withhold_action_window"
        ).read()[0]
        action["views"] = [
            (
                self.env.ref("l10n_ec_withhold.l10n_ec_wizard_withhold_form_view").id,
                "form",
            )
        ]
        ctx = safe_eval(action["context"])
        ctx.pop("default_type", False)
        ctx["type"] = tipo
        ctx["move_id"] = self.id
        ctx["move_amount_untaxed"] = self.amount_untaxed
        ctx["move_amount_iva"] = self.get_tax_iva_total()
        ctx["tax_support"] = self.l10n_ec_tax_support
        ctx.update(self.env.context.copy())
        action["context"] = ctx
        return action

    def action_show_l10n_ec_withholds(self):
        withhold_ids = self.l10n_ec_withhold_ids.ids
        action = self.env.ref("account.action_move_journal_line").read()[0]
        context = {
            "create": False,
            "delete": True,
            "edit": False,
        }
        action["context"] = context
        action["name"] = _("Withholding")
        view_tree_id = self.env.ref(
            "l10n_ec_withhold.view_account_move_withhold_tree"
        ).id
        view_form_id = self.env.ref(
            "l10n_ec_withhold.view_account_move_withhold_form"
        ).id
        action["view_mode"] = "form"
        action["views"] = [(view_form_id, "form")]
        action["res_id"] = withhold_ids[0]
        if len(withhold_ids) > 1:
            action["view_mode"] = "tree,form"
            action["views"] = [(view_tree_id, "tree"), (view_form_id, "form")]
            action["domain"] = [("id", "in", withhold_ids)]

        return action

    def _l10n_ec_get_document_date(self):
        if self.is_purchase_withhold():
            return self.date
        return super()._l10n_ec_get_document_date()

    def _get_l10n_latam_documents_domain(self):
        # support to withholding
        if (
            self.company_id.account_fiscal_country_id.code == "EC"
            and self.is_withhold()
        ):
            return [
                ("country_id.code", "=", "EC"),
                ("internal_type", "=", "withhold"),
            ]
        return super()._get_l10n_latam_documents_domain()

    def _get_l10n_ec_tax_support(self):
        self.ensure_one()
        return self.partner_id.l10n_ec_tax_support

    # Sobreescribir metodo para que las retenciones se abran con su respectivo formulario
    def action_open_business_doc(self):
        self.ensure_one()
        if self.is_withhold():
            form_id = self.env.ref(
                "l10n_ec_withhold.view_account_move_withhold_form"
            ).id
            res = {
                "name": _("Withhold"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "views": [(form_id, "form")],
                "res_model": "account.move",
                "res_id": self.id,
                "target": "current",
            }
            return res
        else:
            return super().action_open_business_doc()

    @api.model
    def validations_withhold(self, invoice, vals):
        if vals["tipo"] == "sale":
            # Validate len of number authorization
            if len(vals["authorization"]) not in [10, 49]:
                raise UserError(
                    _("Authorization is not valid. Should be length equal to 10 or 49")
                )

            # Validate or extract withhold number
            if not vals.get("number"):
                if len(vals["authorization"]) == 49:
                    series_number = vals["authorization"][24:39]
                    vals[
                        "number"
                    ] = f"{series_number[0:3]}-{series_number[3:6]}-{series_number[6:15]}"
                else:
                    raise UserError(_("Please add a document number before continue"))

            # Validate duplicate retention
            withhold_count = self.env["account.move"].search_count(
                [
                    ("partner_id", "=", invoice.partner_id.id),
                    ("ref", "=", vals["number"]),
                    ("l10n_ec_withholding_type", "=", "sale"),
                    ("l10n_latam_internal_type", "=", "withhold"),
                    ("state", "=", "posted"),
                ]
            )
            if withhold_count > 0:
                raise UserError(_(f"Withhold {vals['number']} already exist"))

            # Validate duplicate invoice
            result = self.env["l10n_ec.withhold.line"].search(
                [
                    ("l10n_ec_invoice_withhold_id", "=", invoice.id),
                    ("withhold_id.l10n_ec_withholding_type", "=", "sale"),
                    ("withhold_id.l10n_latam_internal_type", "=", "withhold"),
                    ("withhold_id.state", "=", "posted"),
                ],
                limit=1,
            )
            if result:
                raise UserError(
                    _(
                        f"Invoice {invoice.name} already exist in withhold "
                        f"{result.withhold_id.name}"
                    )
                )

        # Validate date of withhold
        if vals.get("date") and vals.get("date") < invoice.invoice_date:
            raise UserError(
                _(
                    f"Withhold date: {vals['date']} "
                    f"should be equal or major that invoice date: {invoice.invoice_date}"
                )
            )

        # Validate lines
        if not vals.get("lines"):
            raise UserError(_("Please add some withholding lines before continue"))

        # Validate journal
        if not vals.get("journal_id"):
            journal = self.env["account.journal"].search(
                [
                    ("type", "=", "general"),
                    ("l10n_ec_withholding_type", "=", vals["tipo"]),
                ],
                limit=1,
            )
            if journal:
                vals["journal_id"] = journal.id
            else:
                raise UserError(_("Please configure a journal for sale withhold"))

    # Create Withhold
    @api.model
    def create_withhold(self, vals, post=True):
        # get invoice
        invoice = False
        invoice_id = vals.get("invoice_id")
        if not invoice_id:
            invoice = self.search(
                [
                    ("name", "like", "%" + vals["invoice_number"]),
                    ("move_type", "=", "out_invoice"),
                ],
                limit=1,
            )
            if not invoice:
                raise UserError(_(f"Invoice {vals['invoice_number']} not found"))
            invoice_id = invoice.id
        if not invoice:
            invoice = self.browse(invoice_id)

        # Validaciones
        self.validations_withhold(invoice, vals)

        # Create lines
        w_lines = []
        account_lines = []
        total_withhold = vals["total_withhold"]

        tax_tags_base = []

        for line in vals["lines"]:
            line["l10n_ec_invoice_withhold_id"] = invoice_id

            w_lines.append((0, 0, line))

            # Linea contable de la retencion.
            ret_tax = self.env["account.tax"].browse(line["tax_withhold_id"])
            tax_tags_base += ret_tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "base"
            ).tag_ids.ids
            repartition_lines = ret_tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
            )
            for repartition_line in repartition_lines:
                account_id = repartition_line.account_id.id
                amount = line["withhold_amount"] * repartition_line.factor
                debit = 0
                credit = 0
                if vals["tipo"] == "sale":
                    debit = amount
                else:
                    credit = amount

                account_lines.append(
                    (
                        0,
                        0,
                        {
                            "partner_id": invoice.partner_id.id,
                            "account_id": account_id,
                            "name": "RET " + str(vals["number"]),
                            "debit": debit,
                            "credit": credit,
                            "tax_tag_ids": [(6, 0, repartition_line.tag_ids.ids)],
                        },
                    )
                )

        # Linea contable de la base
        if vals["tipo"] == "sale":
            # Linea contable de la retencion. Quito de las cuentas por cobrar
            account_id = invoice.partner_id.property_account_receivable_id.id
        else:
            # Linea contable de la retencion. Quito de las cuentas por pagar
            account_id = invoice.partner_id.property_account_payable_id.id

        # Validar que la cuenta exista en los movimientos de la factura
        account_exist = invoice.line_ids.filtered(
            lambda x: x.account_id.id == account_id
        )
        if not account_exist:
            raise UserError(
                _("Account '%s' not found in invoice lines")
                % (invoice.partner_id.property_account_receivable_id.name)
            )

        if vals["tipo"] == "sale":
            credit = total_withhold
            debit = 0.0
        else:
            credit = 0.0
            debit = total_withhold

        account_lines.append(
            (
                0,
                0,
                {
                    "partner_id": invoice.partner_id.id,
                    "account_id": account_id,
                    "name": "RET " + str(vals["number"]),
                    "debit": debit,
                    "credit": credit,
                    "tax_tag_ids": [(6, 0, tax_tags_base)],
                },
            )
        )

        # Create withhold
        withhold_vals = {
            "journal_id": vals["journal_id"],
            "move_type": "entry",
            "l10n_latam_document_type_id": self.env.ref("l10n_ec.ec_dt_07").id,
            "partner_id": invoice.partner_id.id,
            "l10n_ec_withholding_type": vals["tipo"],
            "ref": vals.get("number", invoice.name),
            "l10n_ec_electronic_authorization": vals.get("authorization"),
            "l10n_ec_withhold_line_ids": w_lines,
            "line_ids": account_lines,
        }
        if vals.get("date"):
            withhold_vals["date"] = vals.get("date")

        withhold = self.create(withhold_vals)

        if post:
            withhold.action_post()
            # asignar retencion a la factura
            invoice.write({"l10n_ec_withhold_ids": [(4, withhold.id)]})

            # Actualizar nombre en lineas
            if vals["tipo"] == "purchase":
                withhold.line_ids.write({"name": withhold.name})

            self._try_reconcile_withholding_moves(
                withhold,
                invoice,
                "asset_receivable" if vals["tipo"] == "sale" else "liability_payable",
            )

        return withhold

    def _try_reconcile_withholding_moves(self, withholding, invoices, account_type):
        assert account_type in ["asset_receivable", "liability_payable"], _(
            "Account type not supported, this must be receivable or payable"
        )
        aml_to_reconcile = invoices.line_ids.filtered(
            lambda line: line.account_id.account_type == account_type
        )
        aml_to_reconcile += withholding.line_ids.filtered(
            lambda line: line.account_id.account_type == account_type
        )
        if not any(aml_to_reconcile.mapped("reconciled")):
            aml_to_reconcile.reconcile()
        return True


class WithholdLine(models.Model):
    _name = "l10n_ec.withhold.line"
    _description = "Withhold line"

    withhold_id = fields.Many2one(
        comodel_name="account.move",
        string="Withhold",
        ondelete="cascade",
    )
    l10n_ec_invoice_withhold_id = fields.Many2one("account.move", string="Document")
    tax_group_withhold_id = fields.Many2one(
        comodel_name="account.tax.group",
        string="Withholding Type",
    )
    tax_withhold_id = fields.Many2one(
        comodel_name="account.tax",
        string="Withholding tax",
    )
    base_amount = fields.Float(string="Amount Base", readonly=False)
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
