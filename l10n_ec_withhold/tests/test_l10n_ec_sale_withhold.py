import logging
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.l10n_ec_account_edi.models.account_edi_document import (
    AccountEdiDocument,
)
from odoo.addons.l10n_ec_account_edi.models.account_edi_format import AccountEdiFormat
from odoo.addons.l10n_ec_account_edi.tests.test_edi_common import TestL10nECEdiCommon

_logger = logging.getLogger(__name__)


@tagged("post_install_l10n", "post_install", "-at_install", "invoice")
class TestL10nSaleWithhold(TestL10nECEdiCommon):
    def test_l10n_ec_save_sale_withhold(self):
        _logger.warning("*** test_l10n_ec_invoice ***")

        def mock_l10n_ec_edi_zeep_client(edi_doc_instance, environment, url_type):
            return self._zeep_client_ws_sri()

        def mock_l10n_ec_edi_send_xml_with_auth(edi_doc_instance, client_ws):
            return self._get_response_with_auth(edi_doc_instance)

        def mock_l10n_ec_response_reception_received(
            edi_doc_instance, client_ws, xml_signed
        ):
            return self._get_response_reception_received()

        partner = self.partner_with_email
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

        wizard = Form(
            self.env["l10n_ec.wizard.create.sale.withhold"].with_context(
                **{"active_ids": invoice.ids}
            )
        )
        self.assertEqual(wizard.partner_id, partner)

        wizard.issue_date = invoice.invoice_date
        wizard.journal_id = invoice.journal_id
        wizard.electronic_authorization = "1111111111"
        wizard.document_number = "1-1-1"
        self.assertEqual(wizard.document_number, "001-001-000000001")

        tax_group = self.env["account.tax.group"].search(
            [("l10n_ec_type", "=", "withhold_vat")]
        )

        taxes = self.env["account.tax"].search(
            [
                ("company_id", "=", self.company.id),
                ("tax_group_id", "=", tax_group.id),
                ("type_tax_use", "=", "sale"),
                ("amount", "=", -100),
            ]
        )

        with wizard.withhold_line_ids.new() as line:
            line.invoice_id = invoice
            line.tax_group_withhold_id = tax_group
            line.tax_withhold_id = taxes

        status = wizard.save().button_validate()

        self.assertEqual(status, True)
        # TODO Test withhold in account move

    def test_l10n_ec_fail_sale_withhold(self):
        _logger.warning("*** test_l10n_ec_invoice ***")

        def mock_l10n_ec_edi_zeep_client(edi_doc_instance, environment, url_type):
            return self._zeep_client_ws_sri()

        def mock_l10n_ec_edi_send_xml_with_auth(edi_doc_instance, client_ws):
            return self._get_response_with_auth(edi_doc_instance)

        def mock_l10n_ec_response_reception_received(
            edi_doc_instance, client_ws, xml_signed
        ):
            return self._get_response_reception_received()

        partner = self.partner_with_email
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

        wizard = Form(
            self.env["l10n_ec.wizard.create.sale.withhold"].with_context(
                **{"active_ids": invoice.ids}
            )
        )
        self.assertEqual(wizard.partner_id, partner)

        wizard.issue_date = invoice.invoice_date
        wizard.journal_id = invoice.journal_id
        wizard.electronic_authorization = "1111111111"
        wizard.document_number = "1-1-1"
        self.assertEqual(wizard.document_number, "001-001-000000001")

        with self.assertRaises(UserError):
            wizard.save().button_validate()
