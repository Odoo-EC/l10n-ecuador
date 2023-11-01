from odoo.tests import tagged

from .test_edi_common import TestL10nECEdiCommon


@tagged("post_install_l10n", "post_install", "-at_install", "certificate")
class TestL10nCheckCertificate(TestL10nECEdiCommon):
    def test_l10n_ec_check_certificate(self):
        """Test that the cron task is executed correctly."""
        self._setup_edi_company_ec()

        cron_tasks = self.env.ref(
            "l10n_ec_account_edi.ir_cron_check_certificate", False
        )
        self.assertTrue(cron_tasks)

        result = cron_tasks.method_direct_trigger()
        self.assertTrue(result)

    def test_l10n_ec_check_certificate_when_is_expired(self):
        """Test that the cron task is executed correctly when certificate is expired."""
        self._setup_edi_company_ec()

        cron_tasks = self.env.ref(
            "l10n_ec_account_edi.ir_cron_check_certificate", False
        )

        certificates = self.env["sri.key.type"].search([])
        for certificate in certificates:
            certificate.write({"days_for_notification": 3000})

        result = cron_tasks.method_direct_trigger()
        self.assertTrue(result)

    def test_l10n_ec_check_crash_send_email(self):
        """Fail send email."""
        self._setup_edi_company_ec()

        certificates = self.env["sri.key.type"].search([])
        for certificate in certificates:
            certificate.write({"days_for_notification": 3000})

            result = certificate.action_email_notification()
            self.assertFalse(result)
