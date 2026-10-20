# -*- coding: utf-8 -*-

import base64
import csv
import io
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MarketplaceSettlementImportWizard(models.TransientModel):
    _name = 'marketplace.settlement.import.wizard'
    _description = 'Marketplace Settlement Import Wizard'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    marketplace = fields.Selection(
        selection=[
            ('amazon', 'Amazon'),
            ('flipkart', 'Flipkart'),
            ('meesho', 'Meesho'),
            ('custom', 'Custom / Other'),
        ],
        string='Marketplace Platform',
        required=True,
        default='amazon',
    )
    file_data = fields.Binary(
        string='Settlement File (CSV)',
        required=True,
        attachment=False,
    )
    file_name = fields.Char(
        string='File Name',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Settlement Journal',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    clearing_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Bank / Clearing Account',
        domain="[('company_ids', 'in', company_id), ('active', '=', True)]",
        help='Receiving account for payout. If omitted, journal default account will be used.',
    )
    commission_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Commission Expense Account',
        required=True,
        domain="[('company_ids', 'in', company_id), ('account_type', '=', 'expense'), ('active', '=', True)]",
    )
    shipping_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Shipping Expense Account',
        required=True,
        domain="[('company_ids', 'in', company_id), ('account_type', '=', 'expense'), ('active', '=', True)]",
    )
    tax_account_id = fields.Many2one(
        comodel_name='account.account',
        string='TCS / TDS Account',
        required=True,
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ('asset_current', 'expense')), ('active', '=', True)]",
    )
    default_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Receivable Account',
        required=True,
        domain="[('company_ids', 'in', company_id), ('account_type', '=', 'asset_receivable'), ('active', '=', True)]",
    )
    marketplace_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Marketplace Vendor / Partner',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company

        if 'journal_id' in fields_list and not res.get('journal_id'):
            bank_journal = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', 'in', ('bank', 'general')),
            ], limit=1)
            if bank_journal:
                res['journal_id'] = bank_journal.id
                if bank_journal.default_account_id:
                    res['clearing_account_id'] = bank_journal.default_account_id.id

        if 'default_receivable_account_id' in fields_list and not res.get('default_receivable_account_id'):
            @api.model
            def default_get(self, fields_list):
             res = super().default_get(fields_list)
            company = self.env.company

        # Attempt to set smart defaults for standard accounting configurations
        if 'journal_id' in fields_list and not res.get('journal_id'):
            bank_journal = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', 'in', ('bank', 'general')),
            ], limit=1)
            if bank_journal:
                res['journal_id'] = bank_journal.id
                if bank_journal.default_account_id:
                    res['clearing_account_id'] = bank_journal.default_account_id.id

        if 'default_receivable_account_id' in fields_list and not res.get('default_receivable_account_id'):
            receivable_account = self.env['account.account'].search([
                ('company_ids', 'in', company.id),
                ('account_type', '=', 'asset_receivable'),
                ('active', '=', True),
            ], limit=1)
            if receivable_account:
                res['default_receivable_account_id'] = receivable_account.id

        return res
    
        if receivable_account:
                res['default_receivable_account_id'] = receivable_account.id

        return res

    def _clean_float(self, value):
        """Converts strings with currency symbols or commas to float."""
        if not value:
            return 0.0
        cleaned = str(value).strip().replace(',', '').replace('$', '').replace('₹', '').replace('€', '')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_date(self, value):
        """Parses common settlement date formats."""
        if not value:
            return None
        date_str = str(value).strip().split('T')[0].split(' ')[0]
        formats = ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d')
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _get_row_value(self, row, alias_list):
        """Matches dictionary keys against a list of header aliases."""
        for alias in alias_list:
            for key, val in row.items():
                if key and alias in key.strip().lower():
                    return val
        return None

    def _get_column_mappings(self):
        """Returns header aliases per supported marketplace."""
        mappings = {
            'amazon': {
                'order_id': ['order-id', 'order id', 'order_id', 'amazon-order-id', 'merchant-order-id'],
                'gross': ['principal', 'product-sales', 'item-related-fee', 'item-price', 'gross-amount', 'amount', 'total'],
                'commission': ['selling-fee', 'commission', 'referral-fee', 'amazon-fee', 'fee'],
                'shipping': ['fba-per-unit-fulfillment-fee', 'shipping-chargeback', 'shipping-fee', 'weight-handling-fee', 'logistics-fee'],
                'tax': ['tcs-amount', 'tds-amount', 'tcs-cgst', 'tcs-sgst', 'tcs-igst', 'tcs', 'tds', 'withholding'],
                'date': ['posted-date', 'posted-date-time', 'date/time', 'order-date', 'date'],
            },
            'flipkart': {
                'order_id': ['order_id', 'order id', 'order_item_id', 'order item id', 'order-id'],
                'gross': ['sale_amount', 'gross_amount', 'order_amount', 'invoice_amount', 'total_offer_price', 'sale-price'],
                'commission': ['marketplace_fee', 'commission', 'commission_amount', 'seller_commission'],
                'shipping': ['logistics_fee', 'shipping_fee', 'pickpack_fee', 'shipping_charge', 'delivery_fee'],
                'tax': ['tcs_amount', 'tds_amount', 'tcs', 'tds', 'tcs_rate', 'tds_rate', 'total_taxes'],
                'date': ['order_date', 'dispatch_date', 'settlement_date', 'date'],
            },
            'meesho': {
                'order_id': ['sub_order_no', 'sub order no', 'order_id', 'order_no', 'order id'],
                'gross': ['final_settlement_amount', 'sale_price', 'gross_settlement_amount', 'supplier_discounted_price', 'order_total'],
                'commission': ['meesho_commission', 'commission_amount', 'commission', 'referral_fee'],
                'shipping': ['return_shipping_charge', 'shipping_charge', 'shipping_fee', 'shipping_cost'],
                'tax': ['tcs_amount', 'tds_amount', 'tcs', 'tds', 'tax_deducted'],
                'date': ['payment_date', 'order_date', 'date'],
            },
            'custom': {
                'order_id': ['order_id', 'order id', 'order', 'ref', 'reference', 'marketplace_order_id'],
                'gross': ['gross', 'gross_amount', 'sale', 'sales_amount', 'amount', 'total', 'invoice_total'],
                'commission': ['commission', 'commission_fee', 'fees', 'fee', 'charge'],
                'shipping': ['shipping', 'shipping_fee', 'freight', 'logistics', 'delivery_charge'],
                'tax': ['tax', 'tax_deducted', 'tcs', 'tds', 'withholding', 'withholding_tax'],
                'date': ['date', 'order_date', 'invoice_date', 'settlement_date'],
            },
        }
        return mappings.get(self.marketplace, mappings['custom'])

    def action_parse_and_import(self):
        """
        Parses uploaded CSV data, structures One2many lines, creates the settlement journal,
        matches lines against posted customer invoices, and navigates to the result.
        """
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Please upload a settlement CSV file.'))

        # Decode binary content safely using utf-8-sig to clear potential BOM markers
        try:
            file_bytes = base64.b64decode(self.file_data)
            csv_content = file_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_content = file_bytes.decode('latin-1')
            except Exception as e:
                raise UserError(_('Failed to decode the uploaded file. Ensure it is a valid CSV: %s') % str(e))

        if not csv_content.strip():
            raise UserError(_('The uploaded file is empty.'))

        # Determine dialect / delimiter dynamically
        sample = csv_content[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',\t;')
            delimiter = dialect.delimiter
        except Exception:
            delimiter = '\t' if '\t' in sample else ','

        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
        if not reader.fieldnames:
            raise UserError(_('Invalid file format: No CSV header columns could be identified.'))

        col_map = self._get_column_mappings()
        settlement_lines = []
        parsed_dates = []

        for row_index, row in enumerate(reader, start=1):
            if not any(row.values()):
                continue

            order_id_val = self._get_row_value(row, col_map['order_id'])
            if not order_id_val:
                continue

            order_id = str(order_id_val).strip()
            gross_val = self._clean_float(self._get_row_value(row, col_map['gross']))
            commission_val = abs(self._clean_float(self._get_row_value(row, col_map['commission'])))
            shipping_val = abs(self._clean_float(self._get_row_value(row, col_map['shipping'])))
            tax_val = abs(self._clean_float(self._get_row_value(row, col_map['tax'])))

            raw_date = self._get_row_value(row, col_map['date'])
            order_date = self._parse_date(raw_date)
            if order_date:
                parsed_dates.append(order_date)

            line_vals = {
                'marketplace_order_id': order_id,
                'order_date': order_date,
                'gross_amount': gross_val,
                'commission_fee': commission_val,
                'shipping_fee': shipping_val,
                'tax_deducted': tax_val,
                'status': 'not_found',
            }
            settlement_lines.append((0, 0, line_vals))

        if not settlement_lines:
            raise UserError(_(
                'No valid settlement rows could be extracted. Please ensure the file contains matching '
                'headers for the selected marketplace (%s).'
            ) % dict(self._fields['marketplace'].selection).get(self.marketplace))

        # Establish start and end dates from parsed rows or fallback to today
        today = fields.Date.context_today(self)
        date_start = min(parsed_dates) if parsed_dates else today
        date_end = max(parsed_dates) if parsed_dates else today

        batch_name = self.file_name or _('%s Settlement - %s') % (
            dict(self._fields['marketplace'].selection).get(self.marketplace),
            today,
        )

        journal_vals = {
            'name': batch_name,
            'company_id': self.company_id.id,
            'marketplace': self.marketplace,
            'date_start': date_start,
            'date_end': date_end,
            'account_journal_id': self.journal_id.id,
            'clearing_account_id': self.clearing_account_id.id if self.clearing_account_id else self.journal_id.default_account_id.id,
            'commission_account_id': self.commission_account_id.id,
            'shipping_account_id': self.shipping_account_id.id,
            'tax_account_id': self.tax_account_id.id,
            'default_receivable_account_id': self.default_receivable_account_id.id,
            'marketplace_partner_id': self.marketplace_partner_id.id if self.marketplace_partner_id else False,
            'state': 'parsed',
            'line_ids': settlement_lines,
        }

        settlement = self.env['marketplace.settlement.journal'].create(journal_vals)

        # Trigger automatic matching on lines
        settlement.line_ids.action_match_with_system_records()
        settlement.state = 'matched'

        return {
            'name': _('Settlement Report: %s') % settlement.name,
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.settlement.journal',
            'res_id': settlement.id,
            'view_mode': 'form',
            'target': 'current',
        }