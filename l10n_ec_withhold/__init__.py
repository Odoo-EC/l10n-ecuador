from . import models
from . import wizard

from odoo import api, SUPERUSER_ID


def _l10n_ec_withhold_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["account.chart.template"]._l10n_ec_journal_post_init()
