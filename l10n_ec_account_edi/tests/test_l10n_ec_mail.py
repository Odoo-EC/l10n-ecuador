from odoo.tests import tagged

from .test_edi_common import TestL10nECEdiCommon

# from odoo.addons.test_mail.tests.common import TestMailCommon


@tagged("post_install", "mail")
# class TestL10nMail(TestL10nECEdiCommon, TestMailCommon):
class TestL10nMail(TestL10nECEdiCommon):
    def test_l10n_ec_out_invoice(self):
        # self._init_mail_gateway()
        partner = self.partner_with_email
        self._setup_edi_company_ec()
        invoice = self._l10n_ec_prepare_edi_out_invoice(
            partner=partner, auto_post=False
        )
        invoice.action_post()
        edi_doc = invoice._get_edi_document(self.edi_format)
        edi_doc._process_documents_web_services(with_commit=False)
        edi_doc.send_mail_to_partner()
        # print("Invoice:", invoice.name)
        # print("Customer:", invoice.partner_id.vat)
        # print("Customer:", invoice.partner_id.name)
        # print("Customer email:", invoice.partner_id.email)
        # print("Move state:", invoice.state)
        # print("Move is_move_sent:", invoice.is_move_sent)
        # print("Edi state:", invoice.edi_document_ids.state)
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
        result = cron_tasks.method_direct_trigger()
        self.assertTrue(result)
        self.assertEqual(invoice.state, "posted")
        self.assertTrue(edi_doc.l10n_ec_xml_access_key)
