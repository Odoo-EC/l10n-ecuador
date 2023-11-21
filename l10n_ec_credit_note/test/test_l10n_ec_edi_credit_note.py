import logging
from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.l10n_ec_account_edi.tests.test_edi_common import TestL10nECEdiCommon

_logger = logging.getLogger(__name__)

FORM_ID = "account.view_move_form"


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nClDte(TestL10nECEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        discount_account_id = cls.env['account.account'].search([('code', '=', 'ec4110'),
                                                                 ('company_id', '=', cls.company.id),
                                                                 ], limit=1)
        return_account_id = cls.env['account.account'].search([('code', '=', 'ec4111'),
                                                               ('company_id', '=', cls.company.id),
                                                               ], limit=1)
        cls.company.write({
            'l10n_ec_property_account_discount_id': discount_account_id,
            'l10n_ec_property_account_return_id': return_account_id,
        })

        cls.env.context['test_discount_account_id'] = discount_account_id
        cls.env.context['test_return_account_id'] = return_account_id

    def _prepare_document(self, document_type, partner=None, taxes=None, products=None, journal=None,
                          latam_document_type=None, use_payment_term=False, auto_post=False):
        """Crea y devuelve un documento (factura o nota de crédito) según el tipo especificado.
        :param document_type: Tipo de documento ('invoice' o 'credit_note').
        :param partner: Partner, si no se envía se coloca uno.
        :param taxes: Impuestos, si no se envía se colocan impuestos del producto.
        :param products: Productos, si no se envía se coloca uno.
        :param journal: Diario, si no se envía se coloca
        por defecto diario para factura de venta o nota de crédito.
        :param latam_document_type: Tipo de documento, si no se envía se coloca uno.
        :param use_payment_term: Si es True se coloca
        un término de pago al documento, por defecto False.
        :param auto_post: Si es True valida el documento
        y lo devuelve en estado posted, por defecto False.
        """
        partner = partner or self.partner_dni
        latam_document_type = latam_document_type or self.env.ref("l10n_ec.ec_dt_04")

        move_type = 'out_invoice' if document_type == 'invoice' else 'out_refund'
        internal_type = 'invoice' if document_type == 'invoice' else 'credit_note'

        return self._l10n_ec_create_form_move(
            move_type=move_type,
            internal_type=internal_type,
            partner=partner,
            taxes=taxes,
            products=products,
            journal=journal,
            latam_document_type=latam_document_type,
            use_payment_term=use_payment_term,
            auto_post=auto_post,
        )

    def _create_credit_note(self, credit_note_type, invoice, auto_post=True):
        wizard_vals = {
            'invoice_id': invoice.id,
            'l10n_ec_type_credit_note': credit_note_type,
        }
        reversal_wizard = self.env['account.move.reversal.wizard'].create(wizard_vals)
        if auto_post:
            reversal_wizard.action_reverse_moves()
        return reversal_wizard

    def test_create_invoice_and_credit_note_discount(self):
        invoice_form = self._prepare_document(document_type='invoice', auto_post=True)
        invoice = invoice_form.save()

        credit_note_wizard = self._create_credit_note(credit_note_type='discount', invoice=invoice)
        self.assertTrue(credit_note_wizard)

        for line in invoice.line_ids:
            if credit_note_wizard.l10n_ec_type_credit_note == 'discount':
                expected_account_id = self.company.l10n_ec_property_account_discount_id.id
            else:
                expected_account_id = self.company.l10n_ec_property_account_return_id.id

            self.assertEqual(line.account_id.id, expected_account_id)

    def test_create_invoice_and_credit_note_return(self):
        invoice_form = self._prepare_document(document_type='invoice', auto_post=True)
        invoice = invoice_form.save()
        credit_note_wizard = self._create_credit_note(credit_note_type='return', invoice=invoice)
        self.assertTrue(credit_note_wizard)
        for line in invoice.line_ids:
            if credit_note_wizard.l10n_ec_type_credit_note == 'discount':
                expected_account_id = self.company.l10n_ec_property_account_discount_id.id
            else:
                expected_account_id = self.company.l10n_ec_property_account_return_id.id

            self.assertEqual(line.account_id.id, expected_account_id)
