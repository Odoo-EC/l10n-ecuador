import logging
from os import path

from odoo import api, models

_logger = logging.getLogger(__name__)
EDI_DATE_FORMAT = "%d/%m/%Y"


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    def _prepare_jobs(self):
        # pass context for force edi for witholding
        # because Odoo server only process EDI when is_invoice() return True
        return super(
            AccountEdiDocument, self.with_context(force_edi_withhold=True)
        )._prepare_jobs()

    def _l10n_ec_get_xsd_filename(self):
        if self.move_id.is_purchase_withhold():
            base_path = path.join("l10n_ec_account_edi", "data", "xsd")
            filename = "ComprobanteRetencion_V2.0.0"
            return path.join(base_path, f"{filename}.xsd")
        return super()._l10n_ec_get_xsd_filename()

    def _l10n_ec_render_xml_edi(self):
        if self.move_id.is_purchase_withhold():
            ViewModel = self.env["ir.ui.view"].sudo()
            return ViewModel._render_template(
                "l10n_ec_withhold.ec_edi_withhold", self._l10n_ec_get_info_withhold()
            )
        return super()._l10n_ec_render_xml_edi()

    def _l10n_ec_get_info_withhold(self):
        self.ensure_one()
        withhold = self.move_id
        type_id = withhold.l10n_ec_get_identification_type()
        withhold_date = self._l10n_ec_get_edi_date()
        company = withhold.company_id or self.env.company
        withhold_data = {
            "fechaEmision": withhold_date.strftime(EDI_DATE_FORMAT),
            "dirEstablecimiento": self._l10n_ec_clean_str(
                withhold.journal_id.l10n_ec_emission_address_id.street or ""
            )[:300],
            "contribuyenteEspecial": company.l10n_ec_get_resolution_data(withhold_date),
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
            "periodoFiscal": withhold_date.strftime("%m/%Y"),
            "docsSustento": self._l10n_ec_get_support_data(),
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

    @api.model
    def _l10n_ec_prepare_tax_vals_edi(self, tax_data):
        tax_vals = super()._l10n_ec_prepare_tax_vals_edi(tax_data)
        # profit withhold tak from l10n_ec_code_base
        tax = tax_data["tax"]
        if tax.tax_group_id.l10n_ec_type == "withhold_income_tax":
            tax_vals["codigoPorcentaje"] = tax.l10n_ec_code_base
        return tax_vals

    def _l10n_ec_get_support_data(self):
        def filter_support_invoice_lines(invoice_line):
            invoice_line_tax_support = (
                invoice_line.l10n_ec_tax_support
                or invoice_line.move_id.l10n_ec_tax_support
            )
            return tax_support == invoice_line_tax_support

        docs_sustento = []
        withhold = self.move_id
        # agrupar los documentos por sustento tributario y factura
        invoice_line_data = {}
        for withhold_line in withhold.l10n_ec_withhold_line_ids:
            invoice = withhold_line.l10n_ec_invoice_withhold_id
            line_key = (invoice, withhold_line.l10n_ec_tax_support)
            invoice_line_data.setdefault(line_key, []).append(withhold_line)
        for line_key in invoice_line_data:
            invoice, tax_support = line_key
            invoice_taxes_data = invoice._prepare_edi_tax_details(
                filter_invl_to_apply=filter_support_invoice_lines,
            )
            withhold_taxes_data = withhold._prepare_edi_tax_details(
                filter_invl_to_apply=filter_support_invoice_lines
            )
            amount_total = abs(
                invoice_taxes_data.get("base_amount")
                + invoice_taxes_data.get("tax_amount")
            )
            support_data = {
                "codSustento": tax_support,  # TODO credito fiscal
                "codDocSustento": invoice.l10n_latam_document_type_id.code or "01",
                "numDocSustento": invoice.l10n_latam_document_number.replace("-", ""),
                "fechaEmisionDocSustento": invoice._l10n_ec_get_document_date().strftime(
                    EDI_DATE_FORMAT
                ),
                "pagoLocExt": "01",  # TODO
                "tipoRegi": False,  # TODO
                "paisEfecPago": False,  # TODO
                "DobTrib": "NO",  # TODO
                "SujRetNorLeg": False,  # TODO
                "pagoRegFis": False,  # TODO
                "totalSinImpuestos": self._l10n_ec_number_format(
                    invoice_taxes_data.get("base_amount"), 6
                ),
                "importeTotal": self._l10n_ec_number_format(amount_total, 6),
                "impuestosDocSustento": self.l10n_ec_header_get_total_with_taxes(
                    invoice_taxes_data
                ),
                "retenciones": self.l10n_ec_header_get_total_with_taxes(
                    withhold_taxes_data
                ),
                "pagos": [
                    {
                        "name": invoice.l10n_ec_sri_payment_id.name,
                        "formaPago": invoice.l10n_ec_sri_payment_id.code,
                        "total": self._l10n_ec_number_format(amount_total, 6),
                    }
                ],
            }
            docs_sustento.append(support_data)
        _logger.info(docs_sustento)
        return docs_sustento
