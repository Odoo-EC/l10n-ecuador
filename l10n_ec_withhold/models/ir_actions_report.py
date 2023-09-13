from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, res_ids=None, data=None):
        # for Ecuadorian company allow print withhold(skip exception)
        if (
            self.model == "account.move"
            and res_ids
            and self.env.company.account_fiscal_country_id.code == "EC"
        ):
            moves = self.env["account.move"].browse(res_ids)
            if any(move.is_withhold() for move in moves):
                return super(
                    IrActionsReport, self.with_context(force_print_withhold=True)
                )._render_qweb_pdf(res_ids=res_ids, data=data)
        return super()._render_qweb_pdf(res_ids=res_ids, data=data)
