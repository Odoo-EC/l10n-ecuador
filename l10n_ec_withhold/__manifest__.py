{
    "name": "Electronic Withholding Ecuadorian Localization",
    "summary": "Electronic Withholding adapted Ecuadorian localization",
    "category": "Account",
    "author": "Odoo Community Association (OCA), " "Jordan Centeno, Leonardo Gómez",
    "website": "https://github.com/OCA/l10n-ecuador",
    "license": "AGPL-3",
    "version": "15.0.1.0.0",
    "depends": ["l10n_ec_account_edi"],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_latam.document.type.csv",
        "wizard/wizard_create_sale_withhold_view.xml",
        "views/res_partner_view.xml",
        "views/account_move_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
