from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_ec_account_edi.models.account_edi_document import (
    AccountEdiDocument,
)
from odoo.addons.test_mail.tests.common import TestMailCommon

from .test_edi_common import TestL10nECEdiCommon


@tagged("post_install", "mail")
class TestL10nMail(TestL10nECEdiCommon, TestMailCommon):
    # class TestL10nMail(TestL10nECEdiCommon):
    def test_l10n_ec_cron_invoice(self):
        self._init_mail_gateway()
        partner = self.partner_with_email
        self._setup_edi_company_ec()
        invoice = self._l10n_ec_prepare_edi_out_invoice(
            partner=partner, auto_post=False
        )
        invoice.action_post()
        edi_doc = invoice._get_edi_document(self.edi_format)
        edi_doc._process_documents_web_services(with_commit=False)

        account_moves = self.env["account.move"].search([("name", "=", invoice.name)])
        for account_move in account_moves:
            account_move.edi_document_ids.write({"state": "sent"})

        cron_tasks = self.env["ir.cron"].search(
            [
                (
                    "name",
                    "=",
                    "Send email with authorized electronic documents(Ecuador)",
                ),
                ("active", "=", True),
            ]
        )
        self.assertTrue(cron_tasks)

        def send_mail_to_partners(instance):
            all_companies = instance.env["res.company"].search(
                [
                    ("partner_id.country_id.code", "=", "EC"),
                    ("l10n_ec_type_environment", "=", "test"),
                ]
            )
            for company in all_companies:
                instance.with_company(company).send_mail_to_partner()

        with patch.object(
            AccountEdiDocument,
            "send_mail_to_partners",
            send_mail_to_partners,
        ):
            result = cron_tasks.method_direct_trigger()
        self.assertTrue(result)
        self.assertEqual(invoice.state, "posted")
        self.assertTrue(edi_doc.l10n_ec_xml_access_key)
