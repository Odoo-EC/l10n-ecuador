from odoo.tests import tagged
import logging

_logger = logging.getLogger(__name__)

from unittest.mock import patch

from odoo.addons.l10n_ec_account_edi.models.account_edi_document import (
    AccountEdiDocument,
)
from odoo.addons.l10n_ec_account_edi.models.account_edi_format import AccountEdiFormat

from .test_edi_common import TestL10nECEdiCommon


@tagged("post_install_l10n", "post_install", "-at_install", "invoice")
class TestL10nInvoice(TestL10nECEdiCommon):
    def test_l10n_ec_invoice(self):
        _logger.warning('*** test_l10n_ec_invoice ***')

        def mock_l10n_ec_edi_zeep_client(edi_doc_instance, environment, url_type):
            return self._zeep_client_ws_sri()

        def mock_l10n_ec_edi_send_xml_with_auth(edi_doc_instance, client_ws):
            return self._get_response_with_auth(edi_doc_instance)

        def mock_l10n_ec_response_reception_received(
            edi_doc_instance, client_ws, xml_signed
        ):
            return self._get_response_reception_received()

        partner = self.partner
        self._setup_edi_company_ec()
        invoice = self._l10n_ec_prepare_edi_out_invoice(
            partner=partner, auto_post=False
        )
        invoice.action_post()
        edi_doc = invoice._get_edi_document(self.edi_format)

        with patch.object(
            AccountEdiFormat,
            "_l10n_ec_get_edi_ws_client",
            mock_l10n_ec_edi_zeep_client,
        ):
            with patch.object(
                AccountEdiDocument,
                "_l10n_ec_edi_send_xml_auth",
                mock_l10n_ec_edi_send_xml_with_auth,
            ):
                with patch.object(
                    AccountEdiDocument,
                    "_l10n_ec_edi_send_xml",
                    mock_l10n_ec_response_reception_received,
                ):
                    edi_doc._process_documents_web_services(with_commit=False)

        self.assertEqual(invoice.state, "posted")
        self.assertTrue(edi_doc.l10n_ec_xml_access_key)
