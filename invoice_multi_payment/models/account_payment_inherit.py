from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


   


class account_payment(models.Model):
    _inherit = 'account.payment'
    
    invoice_lines = fields.One2many('payment.invoice.line', 'payment_id', string="Invoice Line")
    multipagos = fields.Boolean(
        string='Multipagos', default=True
    )

    def get_lines_ids(self):
        print("------get_lines_ids-------")
        for rec in self:
            if rec.line_ids:
                rec.line_ids.unlink()
   
    def update_invoice_lines(self):
        for rec in self:
            if rec.payment_type == 'inbound':
                rec.get_lines_ids()
                for inv in rec.invoice_lines:
                    inv.open_amount = inv.invoice_id.amount_residual 
            rec.onchange_partner_id()
        
    # def action_draft(self):
    #     for rec in self:
    #         moves = rec.mapped('move_line_ids.move_id')
    #         moves.filtered(lambda move: move.state == 'posted').button_draft()
    #         moves.with_context(force_delete=True).unlink()
    #         rec.write({'state': 'draft','name':False,'move_name':''})

    def clean_lines_invoices(self):
        for rec in self:
            if rec.invoice_lines:
                for line in rec.invoice_lines:
                    if line.check_line == False:
                        line.unlink()

    def line_value(self):
        for rec in self:
            if rec.invoice_lines:
                amount = 0
                for line in rec.invoice_lines:
                    amount += line.allocation
                val = round(amount,2)
                if val != rec.amount:
                    print("+++++++++++")
                    #raise UserError(_("El total de las lineas excede el total del pago %s.", amount))

    def clean_lines(self):
        for rec in self:
            if rec.invoice_lines:
                for line in rec.invoice_lines:
                    if line.allocation == 0.0:
                        line.unlink()


    def action_post(self):
        ''' draft -> posted '''
        self.line_value()
        self.clean_lines()
        self.move_id._post(soft=False)
        self.multipay()

#we could add another line with a comparation between amount_residual > 0
    @api.onchange('partner_id', 'currency_id')
    def onchange_partner_id(self):
        print("------onchange_partner_id-------")
        if self.payment_type == 'inbound':
            if self.partner_id and self.payment_type != 'transfer' and self.multipagos == True:
                vals = {}
                line = [(6, 0, [])]
                invoice_ids = []
                if self.payment_type == 'outbound' and self.partner_type == 'supplier':
                    invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                      ('state', '=','posted'),
                                                                      ('amount_residual','>',0.0),
                                                                      # ('type','=', 'in_invoice'),
                                                                      ('currency_id', '=', self.currency_id.id)])

                if self.payment_type == 'inbound' and self.partner_type == 'supplier':
                    invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                      ('state', '=','posted'),
                                                                      ('amount_residual','>',0.0),
                                                                      # ('type','=', 'in_refund'),
                                                                      ('currency_id', '=', self.currency_id.id)])

                if self.payment_type == 'inbound' and self.partner_type == 'customer':
                    invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                      ('state', '=','posted'),
                                                                      ('amount_residual','>',0.0),
                                                                      #('type','=', 'out_invoice'),
                                                                      ('currency_id', '=', self.currency_id.id)])

                if self.payment_type == 'outbound' and self.partner_type == 'customer':
                    invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                      ('state', '=','posted'),
                                                                      ('amount_residual','>',0.0),
                                                                      # ('type','=', 'out_refund'),
                                                                      ('currency_id', '=', self.currency_id.id)])
                print("INVOICES: ", invoice_ids)
                for inv in invoice_ids[::-1]:
                    vals = {
                           'invoice_id': inv.id,
                           }
                    
                    line.append((0, 0, vals))
                self.invoice_lines = line
                self.onchnage_amount()
            if self.partner_id and self.payment_type != 'transfer' and self.multipagos == False:
                vals = {}
                line = [(6, 0, [])]
                invoice_ids = []
                if self.payment_type == 'outbound' and self.partner_type == 'supplier':
                    invoice_ids = self.env['account.move'].search([('name', '=', self.communication)])

                if self.payment_type == 'inbound' and self.partner_type == 'supplier':
                    invoice_ids = self.env['account.move'].search([('name', '=', self.communication)])

                if self.payment_type == 'inbound' and self.partner_type == 'customer':
                    invoice_ids = self.env['account.move'].search([('name', '=', self.communication)])

                if self.payment_type == 'outbound' and self.partner_type == 'customer':
                    invoice_ids = self.env['account.move'].search([('name', '=', self.communication)])

                for inv in invoice_ids[::-1]:
                    vals = {
                           'invoice_id': inv.id,
                           }
                    
                    line.append((0, 0, vals))
                self.invoice_lines = line
                self.onchnage_amount()
        # if self.payment_type == 'outbound':
        
    
    @api.onchange('amount')
    def onchnage_amount(self):
        total = 0.0
        remain = self.amount
        for line in self.invoice_lines:
            if line.open_amount <= remain:
                line.allocation = line.open_amount
                remain -= line.allocation
            else:
                line.allocation = remain
                remain -= line.allocation
            total += line.allocation

  
    def multipay(self):
        for rec in self:
            if rec.invoice_lines:
                lines = False
                for line in rec.invoice_lines:
                    lines = self.env['account.move.line'].browse(line.invoice_line_id.id)
                    print("---**************11111--------",lines)
                    if lines != False:
                        for lin in rec.move_id.line_ids:
                            print("---**************2222222--------",lin)
                            if lin.invoice_id.id == line.invoice_id.id and lin.credit > 0:

                                print("----------**********************--------33333",lin.id, self.env['account.move.line'].browse(lin.id))
                                lines += self.env['account.move.line'].browse(lin.id)
                                print("----------*********** RETUR ***********-------",lines)
                                rec.move_id.js_assign_outstanding_lines(lines)
                                lines = False

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        for rec in self:
            if rec.invoice_lines:
                write_off_line_vals = write_off_line_vals or {}

                if not rec.outstanding_account_id:
                    raise UserError(_(
                        "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                        rec.payment_method_line_id.name, rec.journal_id.display_name))

                # Compute amounts.
                write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

                if rec.payment_type == 'inbound':
                    # Receive money.
                    liquidity_amount_currency = rec.amount
                elif rec.payment_type == 'outbound':
                    # Send money.
                    liquidity_amount_currency = -rec.amount
                    write_off_amount_currency *= -1
                else:
                    liquidity_amount_currency = write_off_amount_currency = 0.0

                write_off_balance = rec.currency_id._convert(
                    write_off_amount_currency,
                    rec.company_id.currency_id,
                    rec.company_id,
                    rec.date,
                )
                liquidity_balance = rec.currency_id._convert(
                    liquidity_amount_currency,
                    rec.company_id.currency_id,
                    rec.company_id,
                    rec.date,
                )
                counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
                counterpart_balance = -liquidity_balance - write_off_balance
                currency_id = rec.currency_id.id

                if rec.is_internal_transfer:
                    if rec.payment_type == 'inbound':
                        liquidity_line_name = _('Transfer to %s', rec.journal_id.name)
                    else: # payment.payment_type == 'outbound':
                        liquidity_line_name = _('Transfer from %s', rec.journal_id.name)
                else:
                    liquidity_line_name = rec.payment_reference

                # Compute a default label to set on the journal items.

                payment_display_name = {
                    'outbound-customer': _("Customer Reimbursement"),
                    'inbound-customer': _("Customer Payment"),
                    'outbound-supplier': _("Vendor Payment"),
                    'inbound-supplier': _("Vendor Reimbursement"),
                }

                default_line_name = rec.env['account.move.line']._get_default_line_name(
                    _("Internal Transfer") if rec.is_internal_transfer else payment_display_name['%s-%s' % (rec.payment_type, rec.partner_type)],
                    rec.amount,
                    rec.currency_id,
                    rec.date,
                    partner=rec.partner_id,
                )

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': rec.date,
                        'amount_currency': liquidity_amount_currency,
                        'currency_id': currency_id,
                        'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                        'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                        'partner_id': rec.partner_id.id,
                        'account_id': rec.outstanding_account_id.id,
                    }
                ]
                for line in rec.invoice_lines:
                    
                    # Compute amounts.
                    write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

                    if rec.payment_type == 'inbound':
                        # Receive money.
                        liquidity_amount_currency = line.allocation
                    elif rec.payment_type == 'outbound':
                        # Send money.
                        liquidity_amount_currency = -line.allocation
                        write_off_amount_currency *= -1
                    else:
                        liquidity_amount_currency = write_off_amount_currency = 0.0

                    write_off_balance = rec.currency_id._convert(
                        write_off_amount_currency,
                        rec.company_id.currency_id,
                        rec.company_id,
                        rec.date,
                    )
                    liquidity_balance = rec.currency_id._convert(
                        liquidity_amount_currency,
                        rec.company_id.currency_id,
                        rec.company_id,
                        rec.date,
                    )
                    counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
                    counterpart_balance = -liquidity_balance - write_off_balance
                    currency_id = rec.currency_id.id

                    if rec.is_internal_transfer:
                        if rec.payment_type == 'inbound':
                            liquidity_line_name = _('Transfer to %s', rec.journal_id.name)
                        else: # payment.payment_type == 'outbound':
                            liquidity_line_name = _('Transfer from %s', rec.journal_id.name)
                    else:
                        liquidity_line_name = rec.payment_reference

                    # Compute a default label to set on the journal items.

                    payment_display_name = {
                        'outbound-customer': _("Customer Reimbursement"),
                        'inbound-customer': _("Customer Payment"),
                        'outbound-supplier': _("Vendor Payment"),
                        'inbound-supplier': _("Vendor Reimbursement"),
                    }

                    default_line_name = rec.env['account.move.line']._get_default_line_name(
                        _("Internal Transfer") if rec.is_internal_transfer else payment_display_name['%s-%s' % (rec.payment_type, rec.partner_type)],
                        line.allocation,
                        rec.currency_id,
                        rec.date,
                        partner=rec.partner_id,
                    )

                    # Receivable / Payable.
                    liquidity_balance = -liquidity_balance
                    line_vals_list.append({
                            'name': rec.payment_reference or default_line_name,
                            'date_maturity': rec.date,
                            'amount_currency': counterpart_amount_currency,
                            'currency_id': currency_id,
                            # 'debit': balance > 0.0 and balance or 0.0,
                            # 'credit': balance < 0.0 and -balance or 0.0,
                            'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                            'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                            'partner_id': rec.partner_id.id,
                            'account_id': rec.destination_account_id.id,
                            'invoice_id': line.invoice_id.id
                        })
                print("iffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff ", line_vals_list)
                return line_vals_list
            else:
                write_off_line_vals = write_off_line_vals or {}

                if not self.outstanding_account_id:
                    raise UserError(_(
                        "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                        self.payment_method_line_id.name, self.journal_id.display_name))

                # Compute amounts.
                write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

                if self.payment_type == 'inbound':
                    # Receive money.
                    liquidity_amount_currency = self.amount
                elif self.payment_type == 'outbound':
                    # Send money.
                    liquidity_amount_currency = -self.amount
                    write_off_amount_currency *= -1
                else:
                    liquidity_amount_currency = write_off_amount_currency = 0.0

                write_off_balance = self.currency_id._convert(
                    write_off_amount_currency,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
                liquidity_balance = self.currency_id._convert(
                    liquidity_amount_currency,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
                counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
                counterpart_balance = -liquidity_balance - write_off_balance
                currency_id = self.currency_id.id

                if self.is_internal_transfer:
                    if self.payment_type == 'inbound':
                        liquidity_line_name = _('Transfer to %s', self.journal_id.name)
                    else: # payment.payment_type == 'outbound':
                        liquidity_line_name = _('Transfer from %s', self.journal_id.name)
                else:
                    liquidity_line_name = self.payment_reference

                # Compute a default label to set on the journal items.

                payment_display_name = {
                    'outbound-customer': _("Customer Reimbursement"),
                    'inbound-customer': _("Customer Payment"),
                    'outbound-supplier': _("Vendor Payment"),
                    'inbound-supplier': _("Vendor Reimbursement"),
                }

                default_line_name = self.env['account.move.line']._get_default_line_name(
                    _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
                    self.amount,
                    self.currency_id,
                    self.date,
                    partner=self.partner_id,
                )

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': liquidity_amount_currency,
                        'currency_id': currency_id,
                        'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                        'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': self.outstanding_account_id.id,
                    },
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                        'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': self.destination_account_id.id,
                    },
                ]
                if not self.currency_id.is_zero(write_off_amount_currency):
                    # Write-off line.
                    line_vals_list.append({
                        'name': write_off_line_vals.get('name') or default_line_name,
                        'amount_currency': write_off_amount_currency,
                        'currency_id': currency_id,
                        'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
                        'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': write_off_line_vals.get('account_id'),
                    })
                return line_vals_list

     # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.payment <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                # if len(liquidity_lines) != 1:
                #     raise UserError(_(
                #         "Journal Entry %s is not valid. In order to proceed, the journal items must "
                #         "include one and only one outstanding payments/receipts account.",
                #         move.display_name,
                #     ))

                # if len(counterpart_lines) != 1:
                #     raise UserError(_(
                #         "Journal Entry %s is not valid. In order to proceed, the journal items must "
                #         "include one and only one receivable/payable account (with an exception of "
                #         "internal transfers).",
                #         move.display_name,
                #     ))

                if writeoff_lines and len(writeoff_lines.account_id) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, "
                        "all optional journal items must share the same account.",
                        move.display_name,
                    ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'payment_type': 'inbound' if liquidity_amount > 0.0 else 'outbound',
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                # if liquidity_amount > 0.0:
                #     payment_vals_to_write.update({'payment_type': 'inbound'})
                # elif liquidity_amount < 0.0:
                #     payment_vals_to_write.update({'payment_type': 'outbound'})
                print("----_synchronize_from_moves------",payment_vals_to_write)

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        for rec in self:
            if self._context.get('skip_account_move_synchronization'):
                print("---** 698 **-----_synchronize_to_moves")
                return

            if not any(field_name in changed_fields for field_name in (
                'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
                'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id',
            )):
                print("---** 701 **-----_synchronize_to_moves")
                return

            for pay in self.with_context(skip_account_move_synchronization=True):
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                # Make sure to preserve the write-off amount.
                # This allows to create a new payment with custom 'line_ids'.

                if writeoff_lines:
                    counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
                    writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))

                    # To be consistent with the payment_difference made in account.payment.register,
                    # 'writeoff_amount' needs to be signed regarding the 'amount' field before the write.
                    # Since the write is already done at this point, we need to base the computation on accounting values.
                    if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                        sign = -1
                    else:
                        sign = 1
                    writeoff_amount = abs(writeoff_amount) * sign

                    write_off_line_vals = {
                        'name': writeoff_lines[0].name,
                        'amount': writeoff_amount,
                        'account_id': writeoff_lines[0].account_id.id,
                    }
                else:
                    write_off_line_vals = {}

                line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
                line_ids_commands = []
                contador = ""
                for li in line_vals_list:
                    # print("---** 508 **-----_synchronize_to_moves",liquidity_lines.id, li)
                    if li['debit'] > 0:
                        contador = contador + "|"
                        line_ids_commands.append((1, liquidity_lines.id, li))
                    if li['credit'] > 0:
                        for lin in counterpart_lines:
                            # if lin.invoice_id == int(li['invoice_id']):
                            contador = contador + "|"
                            line_ids_commands.append((1,lin.id,li))
                print("-----** 745 **-----",contador,line_ids_commands)  
                for line in writeoff_lines:
                    line_ids_commands.append((2, line.id))

                for extra_line_vals in line_vals_list[2:]:
                    line_ids_commands.append((0, 0, extra_line_vals))

                # Update the existing journal items.
                # If dealing with multiple write-off lines, they are dropped and a new one is generated.
                pay.move_id.write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })



class PaymentInvoiceLine(models.Model):
    _name = 'payment.invoice.line'
    
    check_line = fields.Boolean(
        string=' ',
    )
    payment_id = fields.Many2one('account.payment', string="Payment")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    invoice_line_id = fields.Many2one('account.move.line', compute='_get_invoice_data', string="line")
    invoice = fields.Char(related='invoice_id.name', string="Invoice Number")
    #account_id = fields.Many2one(related="invoice_id.account_id", string="Account")
    date = fields.Date(string='Invoice Date', compute='_get_invoice_data', store=True)
    due_date = fields.Date(string='Due Date', compute='_get_invoice_data', store=True)
    total_amount = fields.Float(string='Total Amount', compute='_get_invoice_data', store=True)
    open_amount = fields.Float(string='Due Amount', compute='_get_invoice_data', store=True)
    allocation = fields.Float(string='Allocation Amount')
    account_move_line_id= fields.Many2one('account.move', string="Invoice")
    
    #@api.multi
    @api.depends('invoice_id')
    def _get_invoice_data(self):
        for data in self:
            invoice_id = data.invoice_id
            data.date = invoice_id.invoice_date
            data.due_date = invoice_id.invoice_date_due
            data.total_amount = invoice_id.amount_total 
            data.open_amount = invoice_id.amount_residual
            x = self.env['account.move.line'].search([('name', '=', data.invoice),('debit', '!=', 0.0),('move_id','=', invoice_id.id)])
            for i in x:
                print("DATA LINES: ", i.move_name, i.balance, i.credit, i.debit, i.display_name, i.display_type, i.account_id.name, i.invoice_id, i.invoice_id.name)
            invoice_line_ids = self.env['account.move.line'].search([('name', '=', data.invoice),('debit', '!=', 0.0),('move_id','=', invoice_id.id)],limit=1)
            data.invoice_line_id = invoice_line_ids.id

class AccountMove(models.Model):
    _inherit = 'account.move'

    def js_assign_outstanding_lines(self,lines):
        return lines.reconcile()

class AccountMoveLines(models.Model):
    _inherit = 'account.move.line'

    invoice_id = fields.Many2one('account.move', string="Invoice")

