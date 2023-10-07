import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _is_required_for_invoice(self, invoice):
        if (
            invoice.country_code != "EC"
            or invoice.journal_id.l10n_ec_emission_type != "electronic"
        ):
            return super()._is_required_for_invoice(invoice)
        if (
            self.code in ("l10n_ec_format_sri",)
            and invoice.is_sale_document()
            or (invoice.l10n_latam_internal_type == "purchase_liquidation")
            or (invoice.l10n_latam_internal_type == "withhold")
        ):
            return True
        return False
