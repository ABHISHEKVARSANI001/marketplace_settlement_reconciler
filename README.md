# Marketplace Settlement Reconciler for Odoo 19

[![Odoo v19.0](https://img.shields.io/badge/Odoo-19.0-purple.svg)](https://www.odoo.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3.0-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![GitHub Issues](https://img.shields.io/github/issues/ABHISHEKVARSANI001/marketplace_settlement_reconciler)](https://github.com/ABHISHEKVARSANI001/marketplace_settlement_reconciler/issues)

An enterprise-grade Odoo 19 module designed to eliminate manual reconciliation bottlenecks for multi-channel e-commerce sellers. Seamlessly ingest, match, and reconcile marketplace settlement payout reports from **Amazon, Flipkart, Meesho, and custom D2C platforms** directly into your Odoo accounting.

---

## 🚀 Key Features

- **Multi-Platform Dynamic CSV Parsing:** Native support for standard payout and settlement report structures without requiring manual file restructuring.
- **Smart Invoice Matching:** Instantly maps marketplace order/sub-order IDs to posted Odoo customer invoices.
- **Discrepancy & Tax Tracking:** Accurately flags and logs mismatches between gross invoice values, marketplace commissions, logistics fees, TCS/TDS, and net payouts.
- **Automated Double-Entry Accounting:** Generates balanced journal entries allocating:
  - Net payout amounts to bank clearing accounts.
  - Commission, shipping, and storage fees to respective expense ledgers.
  - Tax deductions (TCS/TDS) to respective tax clearing accounts.
- **Payment State Automation:** Automatically flips matched customer invoices to a **Paid** state upon successful settlement validation.

---

## 🔄 How It Works (Workflow)

1. **Upload Report:** Navigate to **Invoicing > Marketplace Settlements > Import Settlement CSV**, select your platform, and upload your weekly/monthly payout report.
2. **Account Mapping:** Define your default Bank Clearing Account, Commission Expense Account, and Logistics Expense Account.
3. **Automated Reconciliation:** The engine parses rows, matches order IDs, calculates fee breakdowns, and generates the balancing journal entry.
4. **Instant Closure:** Customer invoices are automatically reconciled and marked as paid.

---

## 🛠️ Installation & Configuration

1. Clone or copy this repository into your Odoo custom addons directory:
   ```bash
   git clone https://github.com/ABHISHEKVARSANI001/marketplace_settlement_reconciler.git

3. Ensure your custom addons path is configured in your odoo.conf file.

4. Restart your Odoo server, go to the Apps menu, click Update Apps List, and search for Marketplace Settlement Reconciler to install.

## 📈 Roadmap & Future Updates
- [ ] Automated scheduled actions (Cron jobs) for SFTP/API report downloads.
- [ ] Dedicated native CSV templates for Shopify, eBay, and Myntra.
- [ ] Advanced analytics dashboard for platform-wise profitability and net margins.

## 🤝 Contributing & Support

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/ABHISHEKVARSANI001/marketplace_settlement_reconciler/issues).

Need custom modifications, multi-currency enhancements, or tailored Odoo ERP implementation for your business? Reach out for professional integration services.

## 📄 License
This module is licensed under the LGPL-3.0 License - see the [License: LGPL-3](https://github.com/ABHISHEKVARSANI001/marketplace_settlement_reconciler/blob/main/LICENSE) file for details.

