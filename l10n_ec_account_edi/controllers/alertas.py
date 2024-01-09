from odoo import http
from odoo.http import request
from datetime import datetime
import odoo.addons.onboarding.controllers.onboarding as onboarding


class OnboardingController(http.Controller):

    # @http.route('/l10n_ec_account_edi/account_invoice_onboarding', auth='user', type='json')
    @http.route('/onboarding/<string:route_name>', auth='user', type='json')
    def get_l10n_ec_account_edi_onboarding_data(self, route_name=None, context=None):
        """ Mensaje de Alerta si la firma electrónica esta por caducarse """

        firma = request.env.company.l10n_ec_key_type_id        
        if not firma:
            return onboarding.OnboardingController.get_onboarding_data(self, route_name, context)

        fecha = firma.expire_date
        dias = (fecha - datetime.today().date()).days

        if dias > 30:
            return onboarding.OnboardingController.get_onboarding_data(self, route_name, context)

        contenido = "<h3>POR FAVOR RENOVAR LA FIRMA ELECTRÓNICA</h3>"
        
        if dias <= 0:
            contenido += f"<h4>Caducó hace {abs(dias)} días.</h4>"
        else:
            contenido += f"<h4>Va a caducar en {abs(dias)} días.</h4>"            

        contenido += f"<h4>Número del Serial: {firma.cert_serial_number} (Necesario al renovar la firma)</h4>"
        
        return {
                    'html': request.env['ir.qweb']._render(
                        'l10n_ec_account_edi.alerta_account_move_in', 
                        {
                            'contenido': contenido,
                        }
                    )
                }
