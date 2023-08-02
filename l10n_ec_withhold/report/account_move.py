from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def is_invoice(self, include_receipts=False):
        if self.l10n_latam_internal_type == 'withhold':
            return True
        return super(AccountMove, self).get_invoice_types(include_receipts)

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_internal_type == 'withhold':
            return "l10n_ec_account_edi.report_invoice_document"
        return super()._get_name_invoice_report()
