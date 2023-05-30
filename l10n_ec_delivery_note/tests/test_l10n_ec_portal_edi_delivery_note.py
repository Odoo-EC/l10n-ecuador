from datetime import datetime, timedelta

from odoo import _
from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

from .test_l10n_ec_delivery_note_common import TestL10nDeliveryNoteCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nPortalEdiDeliveryNote(HttpCase, TestL10nDeliveryNoteCommon):
    @mute_logger("odoo.addons.http_routing.models.ir_http", "odoo.http")
    def test_l10n_ec_portal_delivery_notes(self):
        """Crear guías de remisión electrónicas, y verificarlas en el portal"""
        self.setup_edi_delivery_note()
        delivery_notes = self.DeliveryNote.browse()
        for x in range(4):
            delivery_notes += self._l10n_ec_create_delivery_note()
            delivery_notes[x].action_confirm()
            edi_doc = delivery_notes[x]._get_edi_document(self.edi_format)
            edi_doc._process_documents_web_services(with_commit=False)
            self.assertEqual(
                delivery_notes[x].l10n_ec_xml_access_key, edi_doc.l10n_ec_xml_access_key
            )
            self.assertEqual(delivery_notes[x].l10n_ec_authorization_date, False)
            # Agregar fecha de autorización y cambiar de estado
            if x >= 1:
                edi_doc.write(
                    {"l10n_ec_authorization_date": datetime.now(), "state": "sent"}
                )
                self.assertEqual(
                    delivery_notes[x].l10n_ec_authorization_date,
                    edi_doc.l10n_ec_authorization_date,
                )
        for x in delivery_notes[:3]:
            x.message_subscribe(partner_ids=[self.user_portal.partner_id.id])
        url = delivery_notes[1].get_portal_url()

        # Autenticación de usuario seguidor
        self.authenticate("test", "test")

        # Página principal se muestrá el menú de Guías de remisión electrónicas
        req = self.url_open(
            url="/my/home",
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn(_("Test Partner Portal"), req.text)
        self.assertIn(_("Electronic Delivery Notes"), req.text)

        # Página listado de guías con rango de fecha, no se listan
        # si no están autorizadas o el usuario no es seguidor
        req = self.url_open(
            url="/my/edi_delivery_notes?date_begin=%s&;date_end=%s"
            % (
                delivery_notes[0].transfer_date - timedelta(days=1),
                delivery_notes[0].transfer_date,
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)
        self.assertNotIn(delivery_notes[0].document_number, req.text)
        self.assertNotIn(delivery_notes[3].document_number, req.text)
        self.assertIn(delivery_notes[1].document_number, req.text)
        self.assertIn(delivery_notes[2].document_number, req.text)

        # Listado de guías en rango de fecha mayor
        req = self.url_open(
            url="/my/edi_delivery_notes?date_begin=%s&date_end=%s"
            % (
                delivery_notes[0].transfer_date,
                delivery_notes[0].transfer_date + timedelta(days=1),
            ),
            allow_redirects=False,
        )
        self.assertIn(_("there are no Electronic Delivery Notes"), req.text)

        # Búsqueda por número de autorización
        req = self.url_open(
            url="/my/edi_delivery_notes?search_in=clave&search=%s"
            % delivery_notes[1].l10n_ec_xml_access_key,
            allow_redirects=False,
        )
        self.assertIn(delivery_notes[1].document_number, req.text)
        self.assertNotIn(delivery_notes[2].document_number, req.text)

        # Búsqueda por fecha de autorización, ordenados por número
        req = self.url_open(
            url="/my/edi_delivery_notes?"
            "search_in=fecha_auth&search=%s&sortby=fecha_auth_asc&sortby=numero_desc"
            % delivery_notes[2].l10n_ec_authorization_date.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            allow_redirects=False,
        )
        self.assertNotIn(delivery_notes[1].document_number, req.text)
        self.assertIn(delivery_notes[2].document_number, req.text)

        # Búsqueda por fecha de autorización con formato incorrecto
        req = self.url_open(
            url="/my/edi_delivery_notes?search_in=fecha_auth&search=%s"
            % delivery_notes[2].l10n_ec_authorization_date.strftime("%d-%m-%Y"),
            allow_redirects=False,
        )
        self.assertIn(_("Invalid date"), req.text)
        self.assertNotIn(delivery_notes[1].document_number, req.text)
        self.assertNotIn(delivery_notes[2].document_number, req.text)

        # Búsqueda por cualquier parte del número del documento
        req = self.url_open(
            url="/my/edi_delivery_notes?search_in=numero&search=%s"
            % delivery_notes[1].document_number[14:],
            allow_redirects=False,
        )
        self.assertIn(delivery_notes[1].document_number, req.text)
        self.assertNotIn(delivery_notes[2].document_number, req.text)

        # Búsqueda por defecto en todos los campos
        req = self.url_open(
            url="/my/edi_delivery_notes?search_in=all&search=%s"
            % delivery_notes[0].company_id.vat,
            allow_redirects=False,
        )
        self.assertIn(delivery_notes[1].document_number, req.text)
        self.assertIn(delivery_notes[2].document_number, req.text)

        # Página individual
        # Sin token presenta la guia
        req = self.url_open(
            url="/my/edi_delivery_note/%s" % delivery_notes[1].id,
            allow_redirects=False,
        )
        self.assertIn(delivery_notes[1].document_number, req.text)
        self.assertEqual(req.status_code, 200)

        # Con token presenta guia
        req = self.url_open(
            url=url,
            allow_redirects=False,
        )
        self.assertIn(delivery_notes[1].document_number, req.text)
        self.assertEqual(req.status_code, 200)

        # No presenta guia si el usuario no es seguidor
        req = self.url_open(
            url="/my/edi_delivery_note/%s" % delivery_notes[3].id,
            allow_redirects=False,
        )
        self.assertIn(_("You should be redirected"), req.text)
        self.assertEqual(req.status_code, 303)

        # Con token presenta la guia aunque no sea seguidor
        req = self.url_open(
            url=delivery_notes[3].get_portal_url(),
            allow_redirects=False,
        )
        self.assertIn(delivery_notes[3].document_number, req.text)

        # Descargar xml
        req = self.url_open(
            delivery_notes[1].get_portal_url(report_type="xml", download=True),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.headers["Content-Type"], "application/xml")
        self.assertEqual(
            delivery_notes[1].edi_document_ids.attachment_id.raw, req.content
        )

        # Descargar RIDE
        req = self.url_open(
            delivery_notes[1].get_portal_url(report_type="pdf", download=True),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.headers["Content-Type"], "application/pdf")
        self.assertIn(delivery_notes[1].l10n_ec_xml_access_key, req.text)

        # Sin autenticación no se visualiza las guias
        self.authenticate(None, None)

        # Página principal no se muestra menú de guias
        req = self.url_open(
            url="/my/home",
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)
        self.assertNotIn(_("Electronic Delivery Notes"), req.text)

        # Página listado de guias, redirige al website
        req = self.url_open(
            url="/my/edi_delivery_notes",
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)
        self.assertIn(_("You should be redirected"), req.text)

        # No presenta página individual de guia de remisión
        # Sin token
        req = self.url_open(
            url="/my/edi_delivery_note/%s" % delivery_notes[1].id,
            allow_redirects=False,
        )
        self.assertIn(_("You are not allowed to access"), req.text)
        self.assertEqual(req.status_code, 403)

        # Con token
        req = self.url_open(
            url=url,
            allow_redirects=False,
        )
        self.assertIn(_("You are not allowed to access"), req.text)
        self.assertEqual(req.status_code, 403)
