{
    "name": "Credit Notes extension for Ecuador",
    "category": "Account",
    "author": "Odoo Community Association (OCA), "
              "Carlos Lopez, Renan Nazate, Yazber Romero, Luis Romero, Jorge Quiguango, Ricardo Jara",
    "website": "https://github.com/OCA/l10n-ecuador",
    "license": "AGPL-3",
    "version": "15.0.0.0.1",
    "depends": ["account", "account_edi", "l10n_ec", "l10n_ec_base"],

    "data": [
        "security/ir.model.access.csv",
        "views/res_config_view.xml",
        "views/product_category_view.xml",
        "views/product_template_view.xml",
        # "views/account_move_view.xml",
        "wizard/account_invoice_refund_view.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
