from odoo import _, http
from odoo.http import request

from odoo.addons.l10n_ec_account_edi.controllers.l10n_ec_portal_common_electronic import (
    PortalElectronicCommon,
)

EDI_FORMAT_CODE = "l10n_ec_format_sri"


class PortalDeliveryNote(PortalElectronicCommon):
    def _prepare_portal_layout_values(self):
        values = super(PortalDeliveryNote, self)._prepare_portal_layout_values()
        count = request.env["l10n_ec.delivery.note"].search_count(
            self._l10n_ec_edi_documents_domain(EDI_FORMAT_CODE, "delivery_note")
        )
        values["moves"]["delivery_note"] = {
            "name": _("Electronic Delivery Notes"),
            "url": "/my/edi_delivery_notes",
            "count": count,
        }
        return values

    def _l10n_ec_edi_documents_domain(self, edi_format_code, document_type):
        if document_type != "delivery_note":
            return super(PortalDeliveryNote, self)._l10n_ec_edi_documents_domain(
                edi_format_code, document_type
            )
        edi_document_ids = request.env["account.edi.document"].search(
            [
                ("edi_format_id.code", "=", edi_format_code),
                ("state", "=", "sent"),
                ("l10n_ec_authorization_date", "!=", False),
                ("l10n_ec_delivery_note_id", "!=", False),
            ]
        )
        domain = [
            ("l10n_ec_is_edi_doc", "=", True),
            ("edi_document_ids", "in", edi_document_ids.ids),
        ]
        return domain

    @http.route(
        ["/my/edi_delivery_notes", "/my/edi_delivery_notes/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_delivery_note(self, **kwargs):
        self._l10n_ec_update_delivery_note_fields()
        return self.l10n_ec_prepare_edi_documents_portal_rendering_values(
            document_type="delivery_note", **kwargs
        )

    @http.route(
        ["/my/edi_delivery_note/<int:delivery_note_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_delivery_note_detail(self, delivery_note_id, **kwargs):
        self._l10n_ec_update_delivery_note_fields()
        return self.l10n_ec_prepare_details_edi_document_portal(
            document_id=delivery_note_id, document_type="delivery_note", **kwargs
        )

    def _l10n_ec_update_delivery_note_fields(self):
        self.model = "l10n_ec.delivery.note"
        self.report_ref = "l10n_ec_delivery_note.action_report_delivery_note"
        self.edi_format_code = EDI_FORMAT_CODE
        self.field_document_number = "document_number"
        self.field_document_date = "transfer_date"
        self.field_document_authorization = "l10n_ec_authorization_date"
        self.field_document_xml_access_key = "l10n_ec_xml_access_key"
