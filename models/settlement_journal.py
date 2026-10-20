# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


class MarketplaceSettlementJournal(models.Model):
    _name = 'marketplace.settlement.journal'
    _description = 'Marketplace Settlement Journal'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Settlement Batch Reference',
        required=True,
        copy=False,
        default=lambda self: _('New Settlement'),
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
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
    date_start = fields.Date(
        string='Settlement Start Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_end = fields.Date(
        string='Settlement End Date',
        required=True,
        default=fields.Date.context_today,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('parsed', 'Parsed'),
            ('matched', 'Matched'),
            ('posted', 'Posted'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
    )
    account_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Target Journal',
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
        string='Marketplace Partner',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help='Entity for fees and fallback lines when no invoice partner is available.',
    )
    account_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Accounting Entry',
        readonly=True,
        copy=False,
        domain="[('company_id', '=', company_id)]",
    )
    line_ids = fields.One2many(
        comodel_name='marketplace.settlement.line',
        inverse_name='settlement_id',
        string='Settlement Lines',
    )
    line_count = fields.Integer(
        string='Line Count',
        compute='_compute_totals',
    )
    total_gross = fields.Monetary(
        string='Total Gross',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    total_commission = fields.Monetary(
        string='Total Commission',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    total_shipping = fields.Monetary(
        string='Total Shipping',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    total_tax = fields.Monetary(
        string='Total Withholding',
        currency_field='currency_id',
        compute='_compute_totals',
    )
    total_net = fields.Monetary(
        string='Total Net Payout',
        currency_field='currency_id',
        compute='_compute_totals',
    )

    @api.depends(
        'line_ids.gross_amount',
        'line_ids.commission_fee',
        'line_ids.shipping_fee',
        'line_ids.tax_deducted',
        'line_ids.net_amount',
    )
    def _compute_totals(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.total_gross = sum(record.line_ids.mapped('gross_amount'))
            record.total_commission = sum(record.line_ids.mapped('commission_fee'))
            record.total_shipping = sum(record.line_ids.mapped('shipping_fee'))
            record.total_tax = sum(record.line_ids.mapped('tax_deducted'))
            record.total_net = sum(record.line_ids.mapped('net_amount'))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_('Settlement Start Date cannot be set later than End Date.'))

    def action_match_lines(self):
        """Triggers system lookup for all settlement lines attached to this report."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('No settlement lines exist to match.'))
        self.line_ids.action_match_with_system_records()
        self.state = 'matched'

    def _prepare_entry_line_vals(self, account_id, partner_id, label, amount, is_debit_natural=True):
        """
        Creates balanced line values.
        Positive amount with is_debit_natural=True results in Debit.
        Positive amount with is_debit_natural=False results in Credit.
        """
        net_balance = amount if is_debit_natural else -amount
        debit = net_balance if net_balance > 0.0 else 0.0
        credit = -net_balance if net_balance < 0.0 else 0.0

        return {
            'account_id': account_id,
            'partner_id': partner_id,
            'name': label,
            'debit': self.currency_id.round(debit),
            'credit': self.currency_id.round(credit),
        }

    def action_generate_journal_entry(self):
        """
        Constructs and posts a composite multi-line account.move:
        - Debits Clearing / Bank account with total net payout.
        - Debits Commission, Shipping, and TDS/TCS expense/asset accounts.
        - Credits Accounts Receivable per customer invoice / fallback account.
        - Executes reconciliation against matched customer invoice receivable lines.
        """
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Cannot generate journal entry: settlement lines are missing.'))
        if self.account_move_id and self.account_move_id.state == 'posted':
            raise UserError(_('A posted journal entry (%s) is already attached to this settlement.') % self.account_move_id.name)

        bank_clearing_account = self.clearing_account_id or self.account_journal_id.default_account_id
        if not bank_clearing_account:
            raise UserError(_(
                'Please configure a Bank/Clearing Account on this settlement '
                'or designate a Default Account on journal "%s".'
            ) % self.account_journal_id.display_name)

        move_lines = []
        partner_fallback_id = self.marketplace_partner_id.id if self.marketplace_partner_id else False

        # 1. Bank / Clearing Account Line
        if not self.currency_id.is_zero(self.total_net):
            move_lines.append(
                Command.create(
                    self._prepare_entry_line_vals(
                        account_id=bank_clearing_account.id,
                        partner_id=partner_fallback_id,
                        label=_('%s Settlement Remittance (%s to %s)') % (
                            dict(self._fields['marketplace'].selection).get(self.marketplace),
                            self.date_start,
                            self.date_end,
                        ),
                        amount=self.total_net,
                        is_debit_natural=True,
                    )
                )
            )

        # 2. Commission Expense Line
        if not self.currency_id.is_zero(self.total_commission):
            move_lines.append(
                Command.create(
                    self._prepare_entry_line_vals(
                        account_id=self.commission_account_id.id,
                        partner_id=partner_fallback_id,
                        label=_('%s Marketplace Commissions') % dict(self._fields['marketplace'].selection).get(self.marketplace),
                        amount=self.total_commission,
                        is_debit_natural=True,
                    )
                )
            )

        # 3. Shipping / Logistics Expense Line
        if not self.currency_id.is_zero(self.total_shipping):
            move_lines.append(
                Command.create(
                    self._prepare_entry_line_vals(
                        account_id=self.shipping_account_id.id,
                        partner_id=partner_fallback_id,
                        label=_('%s Shipping & Logistics Charges') % dict(self._fields['marketplace'].selection).get(self.marketplace),
                        amount=self.total_shipping,
                        is_debit_natural=True,
                    )
                )
            )

        # 4. TCS / TDS Tax Line
        if not self.currency_id.is_zero(self.total_tax):
            move_lines.append(
                Command.create(
                    self._prepare_entry_line_vals(
                        account_id=self.tax_account_id.id,
                        partner_id=partner_fallback_id,
                        label=_('%s TCS / TDS Withholdings') % dict(self._fields['marketplace'].selection).get(self.marketplace),
                        amount=self.total_tax,
                        is_debit_natural=True,
                    )
                )
            )

        # 5. Accounts Receivable Lines (Credit gross sales per transaction)
        reconcile_mapping = []
        for line in self.line_ids:
            if self.currency_id.is_zero(line.gross_amount):
                continue

            receivable_account = self.default_receivable_account_id
            target_partner_id = line.partner_id.id if line.partner_id else partner_fallback_id

            if line.invoice_id:
                inv_receivable_lines = line.invoice_id.line_ids.filtered(
                    lambda aml: aml.account_id.account_type == 'asset_receivable'
                )
                if inv_receivable_lines:
                    receivable_account = inv_receivable_lines[0].account_id
                    target_partner_id = inv_receivable_lines[0].partner_id.id or target_partner_id

            line_vals = self._prepare_entry_line_vals(
                account_id=receivable_account.id,
                partner_id=target_partner_id,
                label=_('Order %s Settlement') % (line.marketplace_order_id or '/'),
                amount=line.gross_amount,
                is_debit_natural=False,
            )
            move_lines.append(Command.create(line_vals))
            reconcile_mapping.append((line, len(move_lines) - 1))

        if not move_lines:
            raise UserError(_('Zero monetary balances detected. Journal entry creation aborted.'))

        # Build Composite Entry
        move_vals = {
            'journal_id': self.account_journal_id.id,
            'company_id': self.company_id.id,
            'date': self.date_end,
            'ref': self.name,
            'move_type': 'entry',
            'line_ids': move_lines,
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        # Reconcile invoice receivable balances against posted lines
        for line, line_index in reconcile_mapping:
            if not line.invoice_id:
                continue

            created_aml = move.line_ids[line_index]
            open_invoice_receivables = line.invoice_id.line_ids.filtered(
                lambda aml: aml.account_id == created_aml.account_id and not aml.reconciled
            )
            if open_invoice_receivables:
                (open_invoice_receivables | created_aml).reconcile()

        self.write({
            'account_move_id': move.id,
            'state': 'posted',
        })
        return True

    def action_reset_to_draft(self):
        """Allows resetting report back to draft if the related entry is cancelled/reversed."""
        self.ensure_one()
        if self.account_move_id and self.account_move_id.state == 'posted':
            raise UserError(_('Cannot reset to draft while posted journal entry %s exists. Reverse or cancel it first.') % self.account_move_id.name)
        self.state = 'draft'

    def action_view_journal_entry(self):
        """Opens the generated account.move record."""
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_('No journal entry associated with this settlement.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }