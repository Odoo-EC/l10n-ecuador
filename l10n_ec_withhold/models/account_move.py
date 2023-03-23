import logging

from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ec_withhold_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="l10n_ec_withhold_id",
        string="Lineas de retencion",
        required=True,
        readonly=True,
        store=True,
    )
    l10n_ec_withhold_ids = fields.Many2many(
        "account.move",
        relation="l10n_ec_withhold_invoice_rel",
        column1="move_id",
        column2="withhold_id",
        string="Withhold",
        store=True,
        readonly=True,
    )

    l10n_ec_withhold_count = fields.Integer(
        string="Withholds Count", compute="_compute_l10n_ec_withhold_get"
    )

    l10n_ec_withhold_active = fields.Boolean(
        string="Withholds Count",
        compute="_compute_l10n_ec_withhold_active",
        store=True,
    )

    def action_create_sale_withhold_wizard(self):
        self.ensure_one()
        action = self.env.ref(
            "l10n_ec_withhold.l10n_ec_wizard_sale_withhold_action_window"
        ).read()[0]
        action["views"] = [
            (
                self.env.ref(
                    "l10n_ec_withhold.l10n_ec_wizard_sale_withhold_form_view"
                ).id,
                "form",
            )
        ]
        ctx = safe_eval(action["context"])
        ctx.pop("default_type", False)
        ctx.update(
            {
                "default_partner_id": self.partner_id.id,
                "default_invoice_id": self.id,
                "default_issue_date": self.invoice_date,
            }
        )
        action["context"] = ctx
        return action

    def action_show_l10n_ec_withholds(self):
        withhold_ids = self.l10n_ec_withhold_ids.ids
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_journal_line"
        )
        action["name"] = _("Withholding")
        context = {
            "create": False,
            "delete": False,
            "edit": False,
        }
        action["context"] = context
        if len(withhold_ids) > 1:
            action["domain"] = [("id", "in", withhold_ids)]
        else:
            form_view = [(self.env.ref("account.view_move_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = withhold_ids[0]
        return action

    @api.depends("line_ids.l10n_ec_withhold_id", "line_ids")
    def _compute_l10n_ec_withhold_get(self):
        withhold_ids = (
            self.env["account.move"]
            .search([("invoice_origin", "=", self.id)])
            .mapped("id")
        )
        lines_inv = self.env["account.move"].search([("invoice_origin", "=", self.id)])
        if lines_inv:
            lines_inv_mapped = lines_inv.mapped("id")
            self.l10n_ec_withhold_count = len(lines_inv_mapped)
            self.write({"l10n_ec_withhold_ids": [(6, 0, withhold_ids)]})
        else:
            self.l10n_ec_withhold_count = 0
            self.l10n_ec_withhold_ids = False

    @api.depends("partner_id.l10n_ec_withhold_related")
    def _compute_l10n_ec_withhold_active(self):
        for move in self:
            move.l10n_ec_withhold_active = move.partner_id.l10n_ec_withhold_related


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ec_withhold_id = fields.Many2one(
        comodel_name="account.move",
        string="Withhold",
        readonly=True,
        required=False,
        store=True,
    )
