import logging
from os import path

from odoo import models

_logger = logging.getLogger(__name__)
EDI_DATE_FORMAT = "%d/%m/%Y"


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    def _l10n_ec_get_xsd_filename(self):
        filename = super()._l10n_ec_get_xsd_filename()
        base_path = path.join("l10n_ec_account_edi", "data", "xsd")
        document_type = self._l10n_ec_get_document_type()
        if document_type == "withhold":
            filename = "ComprobanteRetencion_V2.0.0"
        return path.join(base_path, f"{filename}.xsd")

    def _l10n_ec_render_xml_edi(self):
        xml_file = super()._l10n_ec_render_xml_edi()
        document_type = self._l10n_ec_get_document_type()
        if document_type == "withhold":
            ViewModel = self.env["ir.ui.view"].sudo()
            xml_file = ViewModel._render_template(
                "l10n_ec_withhold.ec_edi_withhold", self._l10n_ec_get_info_withhold()
            )
        return xml_file

    def _l10n_ec_get_info_withhold(self):
        self.ensure_one()
        withhold = self.move_id
        type_id = withhold.l10n_ec_get_identification_type()
        date_withhold = withhold.invoice_date
        company = withhold.company_id or self.env.company
        # taxes_data = withhold._l10n_ec_get_taxes_grouped_by_tax_group()
        # amount_total = abs(taxes_data.get("base_amount") + taxes_data.get("tax_amount"))
        # currency = withhold.currency_id
        withhold_data = {
            "fechaEmision": (date_withhold).strftime(EDI_DATE_FORMAT),
            "dirEstablecimiento": self._l10n_ec_clean_str(
                withhold.journal_id.l10n_ec_emission_address_id.street or ""
            )[:300],
            "contribuyenteEspecial": company.l10n_ec_get_resolution_data(date_withhold),
            "obligadoContabilidad": self._l10n_ec_get_required_accounting(
                company.partner_id.property_account_position_id
            ),
            "tipoIdSujetoRetenido": type_id,
            "tipoSujetoRetenido": self._l10n_ec_get_type_suject_withholding(type_id),
            "parteRel": "NO",
            "razonSocialSujetoRetenido": self._l10n_ec_clean_str(
                withhold.commercial_partner_id.name
            )[:300],
            "idSujetoRetenido": withhold.commercial_partner_id.vat,
            "periodoFiscal": (date_withhold).strftime("%m/%Y"),
            "docsSustento": self._l10n_ec_get_support_data(withhold),
            "infoAdicional": self._l10n_ec_get_info_additional(),
        }
        withhold_data.update(self._l10n_ec_get_info_tributaria(withhold))
        return withhold_data

    def _l10n_ec_get_type_suject_withholding(self, type_id):
        # codigos son tomados de la ficha técnica ATS, TABLA 14
        type_suject_withholding = False
        if type_id == "08":  # Si tipo identificación es del exterior
            type_suject_withholding = (
                "01"  # Persona Natural TODO: obtener si es compañia "02"
            )
        return type_suject_withholding

    def _l10n_ec_get_support_data(self, withhold):
        support_data = {
            "codSustento": "01",  # TODO credito fiscal
            "codDocSustento": "01",  # TODO documento Factura
            "numDocSustento": "001001000000001",  # TODO
            "fechaEmisionDocSustento": (self.withhold.invoice_date).strftime(
                EDI_DATE_FORMAT
            ),  # TODO
            "pagoLocExt": "01",  # TODO
            "tipoRegi": False,  # TODO
            "paisEfecPago": False,  # TODO
            "DobTrib": "NO",  # TODO
            "SujRetNorLeg": False,  # TODO
            "pagoRegFis": False,  # TODO
            "totalSinImpuestos": 125.90,  # TODO
            "impuestosDocSustento": {
                "codImpuestoDocSustento": "2",  # TODO IVA
                "codigoPorcentaje": "2",  # TODO 12%
                "baseImponible": 125.90,
                "tarifa": 12,
                "valorImpuesto": 15.11,
            },
            "retenciones": {
                "codigo": "1",
                "codigoRetencion": "312",
                "baseImponible": 125.90,
                "porcentajeRetener": 1.75,
                "valorRetenido": 2.20,
            },
            "pagos": withhold._l10n_ec_get_payment_data(),
        }
        return support_data
