# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MarketplaceSettlementLine(models.Model):
    _name = 'marketplace.settlement.line'
    _description = 'Marketplace Settlement Line'
    _order = 'settlement_id desc, id desc'

    settlement_id = fields.Many2one(
        comodel_name='marketplace.settlement.journal',
        string='Settlement Report',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='settlement_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='settlement_id.currency_id',
        readonly=True,
    )
    marketplace_order_id = fields.Char(
        string='Marketplace Order ID',
        required=True,
        index=True,
    )
    order_date = fields.Date(
        string='Order Date',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer / Marketplace Partner',
        help='Partner associated with the matched invoice or order.',
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        index=True,
    )
    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Customer Invoice',
        domain="[('move_type', '=', 'out_invoice'), ('company_id', '=', company_id)]",
        index=True,
    )
    gross_amount = fields.Monetary(
        string='Gross Amount',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Gross sales value debited to the customer.',
    )
    commission_fee = fields.Monetary(
        string='Commission Fee',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Marketplace commission fee charge.',
    )
    shipping_fee = fields.Monetary(
        string='Shipping Fee',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Logistics / courier charges billed by the platform.',
    )
    tax_deducted = fields.Monetary(
        string='TCS / TDS Withheld',
        currency_field='currency_id',
        default=0.0,
        required=True,
        help='Statutory withholding taxes deducted at source.',
    )
    net_amount = fields.Monetary(
        string='Net Settlement Amount',
        currency_field='currency_id',
        compute='_compute_net_amount',
        store=True,
        readonly=False,
        help='Net payout expected from this specific transaction line.',
    )
    status = fields.Selection(
        selection=[
            ('matched', 'Matched'),
            ('not_found', 'Not Found'),
            ('review_needed', 'Review Needed'),
        ],
        string='Matching Status',
        default='not_found',
        required=True,
        index=True,
    )
    notes = fields.Char(
        string='Discrepancy Notes',
    )

    @api.depends('gross_amount', 'commission_fee', 'shipping_fee', 'tax_deducted')
    def _compute_net_amount(self):
        for line in self:
            line.net_amount = (
                line.gross_amount
                - line.commission_fee
                - line.shipping_fee
                - line.tax_deducted
            )

    def action_match_with_system_records(self):
        """
        Locates matching Sale Orders and posted Customer Invoices using marketplace_order_id.
        Searches Sale Order names, client order references, and invoice payment references.
        """
        for line in self:
            order_ref = (line.marketplace_order_id or '').strip()
            if not order_ref:
                line.status = 'not_found'
                continue

            sale_order = self.env['sale.order'].search([
                ('company_id', '=', line.company_id.id),
                '|',
                ('name', '=', order_ref),
                ('client_order_ref', '=', order_ref),
            ], limit=1)

            invoice = False
            if sale_order:
                line.sale_order_id = sale_order.id
                line.partner_id = sale_order.partner_invoice_id or sale_order.partner_id
                invoices = sale_order.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
                )
                if invoices:
                    invoice = invoices[0]
            else:
                invoice = self.env['account.move'].search([
                    ('company_id', '=', line.company_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    '|', '|',
                    ('name', '=', order_ref),
                    ('payment_reference', '=', order_ref),
                    ('ref', '=', order_ref),
                ], limit=1)

            if invoice:
                line.invoice_id = invoice.id
                line.partner_id = invoice.partner_id
                if line.currency_id.compare_amounts(line.gross_amount, invoice.amount_total) == 0:
                    line.status = 'matched'
                    line.notes = False
                else:
                    line.status = 'review_needed'
                    line.notes = _(
                        'Invoice amount (%s) does not equal gross settlement amount (%s).'
                    ) % (invoice.amount_total, line.gross_amount)
            elif sale_order:
                line.status = 'review_needed'
                line.notes = _('Sale order identified, but no posted customer invoice exists.')
            else:
                line.status = 'not_found'
                line.notes = _('No matching sales or invoice record located for order ID.')