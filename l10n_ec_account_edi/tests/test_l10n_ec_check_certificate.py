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
