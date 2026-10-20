# Marketplace Settlement Reconciler for Odoo 19

An enterprise-grade Odoo 19 module designed to automate e-commerce payout reconciliation for multi-channel sellers operating across Amazon, Flipkart, Meesho, and custom D2C platforms.

## 🚀 Key Features
* **Dynamic CSV Parsing:** Supports native payout reports without requiring manual file restructuring.
* **Smart Invoice Matching:** Instantly links marketplace order IDs to posted Odoo customer invoices.
* **Discrepancy & Tax Tracking:** Flags mismatches between invoice totals and marketplace settlements.
* **Automated Accounting:** Generates balanced double-entry journal entries allocating net payouts to bank clearing accounts and fees to correct expense ledgers.
* **Payment State Automation:** Automatically flips matched invoices to **Paid**.

## 🛠️ Installation & Configuration
1. Clone or copy this repository into your Odoo custom addons directory.
2. Update your Odoo app list and install **Marketplace Settlement Reconciler**.
3. Navigate to **Invoicing > Marketplace Settlements > Import Settlement CSV**, select your platform, map your clearing/expense accounts, and upload your payout report.