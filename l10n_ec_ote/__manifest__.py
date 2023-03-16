{
    "name": "OTE for Ecuador",
    "summary": "OTE for Ecuador",
    "category": "Localization",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-ecuador",
    "license": "LGPL-3",
    "version": "15.0.1.0.0",
    "depends": ["base", "contacts", "sales_team", "base_address_city"],
    "data": [
        "views/res_city_view.xml",
        "views/l10n_ec_parish_view.xml",
        "data/res.country.state.csv",
        "data/res.city.csv",
        "data/l10n.ec.parish.csv",
        "security/ir.model.access.csv",
        "views/res_partner.xml",
        "views/res_company.xml",
    ],
    "installable": True,
    "auto_install": False,
}
