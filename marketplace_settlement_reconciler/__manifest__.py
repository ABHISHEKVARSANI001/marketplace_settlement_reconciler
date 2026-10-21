# -*- coding: utf-8 -*-
{
    'name': 'Marketplace Settlement Reconciler',
    'version': '19.0.1.0.2',
    'category': 'Accounting/Localizations',
    'summary': 'Automate marketplace settlement reconciliation, payout reports, and invoice matching for Amazon, Flipkart, Meesho, e-commerce accounting, financial journals, and payment gateway settlement.',
    'description': """
Marketplace Settlement Reconciler
==================================
Automates the reconciliation of e-commerce marketplace settlement summaries:
* Supports Amazon, Flipkart, Meesho, and standardized CSV settlement files.
* Matches marketplace Order IDs / Reference IDs against generated Customer Invoices.
* Deconstructs gross remittances into base revenue, commission fees, logistics/shipping charges, refund reversals, and statutory withholdings (TCS / TDS).
* Generates and auto-posts balanced composite journal entries clearing marketplace receivables and booking operating expenses.
    """,
    'author': 'abhishek varsani',
    'website': 'https://github.com/ABHISHEKVARSANI001',
    'license': 'OPL-1',
    'depends': [
        'account',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/marketplace_settlement_line_views.xml',
        'views/marketplace_settlement_journal_views.xml',
        'views/marketplace_settlement_import_wizard_view.xml',
        'views/marketplace_settlement_menus.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
