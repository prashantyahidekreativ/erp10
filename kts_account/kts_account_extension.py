from datetime import datetime
from odoo import models, fields, api,_
from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp
from odoo import exceptions, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from pytz import timezone

class kts_account_freight_and_packing(models.Model):   
    _name = "account.freight_and_packing"
    name= fields.Char('Name', size=256, index=True)
    packing_account= fields.Many2one('account.account', 'Packing Account',)
    freight_account= fields.Many2one('account.account', 'Freight Account')       
    journal_type= fields.Many2one('account.journal','Journal Type')
    active= fields.Boolean('Active',default=True) 

class account_extension(models.Model): 
    _inherit = 'account.tax'
    precision = fields.Many2one('decimal.precision',string='Precision')
    #automatic_add = fields.Selection([('sale','Sale'),('purchase','Purchase'),('sale_purchase','Sale and Purchase'),],string="Automatic Add")
    freight_charges = fields.Boolean('Fright Charge')
    packing_charges = fields.Boolean('Packing Charge')     
    tax_type= fields.Selection([('sales_tax','Sales'), ('purchase_tax','Purchase'),('sales_purchase_tax','Sales and Purchase')], 'Automatic Add')
    tax_category = fields.Selection([('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                    ('ecess_on_cenvat','Ecess on Cenvat'), ('hcess_on_cenvat','Hcess on Cenvat'), 
                    ('service_tax','Service Tax'), ('ecess_on_service_tax','Ecess on Service Tax'), ('hcess_on_service_tax','Hcess on Service Tax'),('secess_on_cenvat','Swachh Ecess'),('krushi_kalyan_cess','Krushi kalyan Cess On Service Tax')], 'Type')    
    sub_tax_ids = fields.Many2many('account.tax', 'kts_sub_tax_rel', 'sub_tax_id', 'sub_tax', 'Sub Taxes')
    invoice_ids = fields.Many2many('account.invoice','kts_account_invoice_tax_rel','kts_Tax','kts_Invoice')
    sequence=fields.Integer('Sequence')
    
    @api.onchange('price_include','packing_charges','freight_charges')
    def onchange_price_include_reset(self):
        if self.price_include:
           if self.packing_charges or self.freight_charges:
               self.update({'packing_charges':False,'freight_charges':False})
               return {'value':{'packing_charges':False,'freight_charges':False},
                       'warning':{'title':'UserError', 'message':'If price Include in tax you cannot select freight and packing on tax!'}}
               
    
    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()
        if self.amount_type == 'fixed':
            return math.copysign(self.amount, base_amount) * quantity
        if (self.amount_type == 'percent' and not self.price_include) or (self.amount_type == 'division') or (self._context.get('tax')):
            return base_amount * self.amount / 100
        if self.amount_type == 'percent' and self.price_include:   # and self._context.get('tax'):
            return  base_amount - (base_amount / (1 + self.amount / 100))
        if self.amount_type == 'division' and not self.price_include:
            return base_amount / (1 - self.amount / 100) - base_amount

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """ Returns all information required to apply taxes (in self + their children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        } """
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.decimal_places
        if company_id.tax_calculation_rounding_method == 'round_globally':
            prec += 5
        total_excluded = total_included = base = round(price_unit * quantity, prec)
        #total_excluded = total_included = base = price_unit * quantity
        
        for tax in self:
            prec = tax.precision.digits
            if tax.amount_type == 'group':
                ret = tax.children_tax_ids.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base']
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue
            
            if tax.sub_tax_ids  and tax.price_include and not self._context.get('tax'):
                    ret = tax.sub_tax_ids._compute_amount(price_unit, currency, quantity, product, partner)
                    #total_excluded = ret['total_excluded']
                    ret = round(ret, prec)
                    base = price_unit-ret
                    #total_included = ret['total_included']
                    #tax_amount = total_included - total_excluded
                    #taxes += ret['taxes']
                    

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            #if company_id.tax_calculation_rounding_method == 'round_globally':
            tax_amount = round(tax_amount, prec)
            #else:
             #   tax_amount = currency.round(tax_amount)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            if tax.include_base_amount and not self._context.get('tax'):
                base = price_unit
                #base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.name,
                'amount': tax_amount,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
            })

        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': currency.round(total_excluded),
            'total_included': currency.round(total_included),
            'base': base,
        }    
        
class kts_account_fiscal_position(models.Model):
    _inherit='account.fiscal.position'
    start_date= fields.Date('Start Date', required=True)
    end_date= fields.Date('End Date')
    tax_type= fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'),
            ('cst','CST'), ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service'),], 'Tax Type', default='no_tax')
    form_type= fields.Selection([('form_c','Form C'), ('form_h','Form H'), ('form_i','Form I')], 'Form Type',index=True)
    trade_type= fields.Selection([('domestic','Domestic'), ('export','Export'), ('sez','SEZ'), ('eou','EOU'), ('domestic_scrap','Domestic Scrap')], 'Trade Type',default='domestic')
    type = fields.Selection([('out_invoice','Sale'),('in_invoice','Purchase')],string='Type')
    note=fields.Text('Remark')
    price_include=fields.Boolean('Price Include Tax',default=False)
    
    @api.onchange('start_date','end_date')
    def check_change(self):
        if self.end_date and self.start_date:
           if self.start_date > self.end_date:
               self.update({'end_date':False})
               return {'value':{'end_date':False},'warning':{'title':'UserError', 'message':'End date should greater than start date!'}}
               
    
class kts_account_invoice(models.Model):
    _inherit='account.invoice' 
    
    @api.model
    def _default_packing_account(self):
        if self._context:
              journal = self._default_journal()
              res = self.env['account.freight_and_packing'].search([('journal_type','=',journal.id)])
        return  res.packing_account
                         
    @api.model
    def _default_freight_account(self):
        if self._context:
              journal = self._default_journal()
              res = self.env['account.freight_and_packing'].search([('journal_type','=',journal.id)])
        return  res.freight_account
   
    @api.model
    def _default_fiscal_position_id(self):
        if self._context.get('default_fiscal_position_id', False):
            return self.env['account.fiscal.position'].browse(self._context.get('default_fiscal_position_id'))
        inv_type = self._context.get('type') 
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [('type', '=', inv_type)]
        res = self.env['account.fiscal.position'].search(domain)
        return {'domain':{'default_fiscal_position_id':[('id','in',res.ids)]} } 
  
    
      
    packing_account=fields.Many2one('account.account', 'Packing Account', readonly=True, states={'draft': [('readonly', False)]}, default=_default_packing_account,)
    freight_account=fields.Many2one('account.account', 'Freight Account', readonly=True, states={'draft': [('readonly', False)]}, default=_default_freight_account,)   
    packing_charges= fields.Float('Packing charges', readonly=True, states={'draft': [('readonly', False)]})            
    freight_charges= fields.Float('Freight charges', readonly=True, states={'draft': [('readonly', False)]})
    tax_type = fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service')], string='Tax Type',default='no_tax',readonly=True,states={'draft': [('readonly', False)]})  
    packing_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    freight_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
        readonly=True, states={'draft': [('readonly', False)]},default = _default_fiscal_position_id,)  
    freight_and_packing = fields.Monetary('Freight And Packing',digits=dp.get_precision('account'), compute='_compute_amount')
    tds_account=fields.Many2one('account.ktstds', 'TDS Account', readonly=True, states={'draft': [('readonly', False)]},)
    tds_charges= fields.Float('TDS charges', readonly=True, states={'draft': [('readonly', False)]},)            
    tds_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'TDS Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    tds_packing = fields.Boolean('Apply TDS') 
    tds_freight = fields.Boolean('Apply TDS')
    tds_amount = fields.Monetary('TDS',digits=dp.get_precision('account'), compute='_compute_amount')
    confirmation_date=fields.Datetime('Confirmation Date')
    item_removal_date=fields.Datetime('Item Removal Date')
    dispatch_mode=fields.Many2one('kts.dispatch.mode','Dispatch Mode')
    
    @api.onchange('date_invoice')
    def onchange_date_invoice_confirm_date(self):
        if self._context:
           if self.date_invoice and self.type=='out_invoice':
              time=(fields.Datetime.from_string(fields.Datetime.now())).strftime("%H:%M:%S")
              date_time=self.date_invoice+' '+time
              self.update({'confirmation_date':date_time}) 
              return {'value':{  'confirmation_date':date_time
                           } }

    
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(kts_account_invoice, self)._onchange_partner_id()
        if self._context.get('default_fiscal_position_id', False):
            self.fiscal_position_id=self._context.get('default_fiscal_position_id',False)
        
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id','freight_charges','packing_charges','packing_charges_type','freight_charges_type')
    def _compute_amount(self):
        tds_charges=self.tds_charges if self.tds_charges_type=='fixed' else 0.0
        tds_charges=self.tds_account.perc if self.tds_charges_type=='variable' else 0.0
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        
        packing_charges=self.packing_charges if ( self.packing_charges_type =='fixed' or self.packing_charges_type =='variable') else 0.0
        freight_charges=self.freight_charges if ( self.freight_charges_type =='fixed' or self.freight_charges_type =='variable') else 0.0

        if self.packing_charges_type =='variable':
            packing_charges=round(self.amount_untaxed * packing_charges/100.0) 
        if self.freight_charges_type =='variable':
            freight_charges=round(self.amount_untaxed*freight_charges/100.0)   
        
            
        self.freight_and_packing = packing_charges + freight_charges 
        
        if self.tds_freight or self.tds_packing:
            if self.tds_charges_type=='variable': 
               amount = packing_charges + freight_charges +self.amount_untaxed
               self.tds_amount = round(amount*tds_charges/100.0)
            elif self.tds_charges_type=='fixed': 
                 self.tds_amount=tds_charges
                 
        if not self.tds_freight and not self.tds_packing:
            if self.tds_charges_type=='variable': 
               amount = self.amount_untaxed
               self.tds_amount = round(amount*tds_charges/100.0)
               
            elif self.tds_charges_type=='fixed': 
                 self.tds_amount=tds_charges
                 
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax + self.freight_and_packing   
        if self.fiscal_position_id.price_include:
            self.amount_total=round(self.amount_total,0)
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            amount_total_company_signed = self.currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = self.currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
        
    @api.onchange('invoice_line_ids','tax_line_ids','freight_charges','packing_charges','packing_charges_type','freight_charges_type')
    def _onchange_invoice_line_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return
    
    def calculate_tax(self,line,tax_ids,price_unit,quantity, product_id ):
        ctx=dict(self._context)
        ctx.update({'tax':True})
        taxes = tax_ids.with_context(ctx).compute_all(price_unit, self.currency_id, quantity, product_id, self.partner_id)['taxes']
        for tax in taxes:
            val = {
                'id': tax['id'],
                'invoice_id': self.id,
                'name': tax['name'],
                'tax_id': tax['id'],
                'amount': tax['amount'],
                'manual': False,
                'sequence': tax['sequence'],
                'base_amount':price_unit,
                'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
                'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
            }
        return val  
    
    @api.multi
    def get_taxes_values(self):
        #why overwritten?
        #base method calculate each tax on every invoice line, if applicable, and then sums up tax amount, that causes rounding issue
        #solution: each tax should be calculated on whole document
        
        #not considered:
        #currency rate conversion is not taken into account
        
        #step 1: find out all unique taxes applicable on the invoice
        tax_line={}
        for line in self.invoice_line_ids:
            for tax in line.invoice_line_tax_ids:
                if tax in tax_line: 
                    tax_line.update({tax:{'val':tax_line[tax]['val']+(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.quantity), 'order_line':line}})
                else:
                    tax_line.update({tax:{'val':(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.quantity), 'order_line':line}})
        
        
        #step 2: separate taxes which has sub-taxes and which does not
        tax_independent=[]
        tax_with_sub_taxes=[]
        
        for key, value in tax_line.iteritems():
            if len(key.sub_tax_ids)>0:
                tax_with_sub_taxes.append({'invoice_line':value['order_line'], 'invoice_line_tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False,'tax_type':key.tax_category})
            else:
                value=calculate_base(self, key, value )
                tax_independent.append({'invoice_line':value['order_line'], 'invoice_line_tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False,'tax_type':key.tax_category})

        #step 3: calculate tax for both types of taxes
        calculated_taxes=[]                    
        for line in tax_independent:
            val=self.calculate_tax(line['invoice_line'],line['invoice_line_tax_id'], line['price_unit'], line['quantity'], line['product_id'])
            val.update({'tax_type':line['tax_type']})
            calculated_taxes.append(val)
                                    
        for line in tax_with_sub_taxes:
            sub_taxt_base=0.0
            for tax_id in line['invoice_line_tax_id'].sub_tax_ids:
                base_sub_tax=calculate_base(self, tax_id, {'val':line['price_unit']})
                val=self.calculate_tax(line['invoice_line'],tax_id, base_sub_tax['val'], line['quantity'], line['product_id'])
                sub_taxt_base=sub_taxt_base+ val['amount']
            base=calculate_base(self,line['invoice_line_tax_id'], {'val':line['price_unit']})['val']+sub_taxt_base
            val=self.calculate_tax(line['invoice_line'],line['invoice_line_tax_id'], base, line['quantity'], line['product_id'])
            val.update({'tax_type':line['tax_type']})
            calculated_taxes.append(val)
            
        #step 4: group taxes and return
        tax_grouped = {}
        for tax in calculated_taxes:
            key = tax['id']
            if key not in tax_grouped:
                tax_grouped[key] =  tax
            else:
                tax_grouped[key]['amount'] += tax['amount'] 
                tax_grouped[key]['base_amount']+=tax['base_amount']  
            del tax['id']
        return tax_grouped  
   
    
        
        
    @api.onchange('fiscal_position_id')
    def fiscal_position_change(self):
        """Updates taxes and accounts on all invoice lines"""
        self.ensure_one()
        res = {}
        lines_without_product = []
        fp = self.fiscal_position_id
        inv_type = self.type
        for line in self.invoice_line_ids:
            if line.product_id:
                product = line.product_id
                if inv_type in ('out_invoice', 'out_refund'):
                    taxes = product.taxes_id
                else:                        
                    taxes = product.supplier_taxes_id
                    taxes = taxes 
                if fp:
                    
                    taxes = fp.map_tax(taxes)

                line.invoice_line_tax_ids = [(6, 0, taxes.ids)]
                
            else:
                lines_without_product.append(line.name)

        if lines_without_product:
            res['warning'] = {'title': _('Warning')}
            if len(lines_without_product) == len(self.invoice_line):
                res['warning']['message'] = _(
                    "The invoice lines were not updated to the new "
                    "Fiscal Position because they don't have products.\n"
                    "You should update the Account and the Taxes of each "
                    "invoice line manually.")
            else:
                res['warning']['message'] = _(
                    "The following invoice lines were not updated "
                    "to the new Fiscal Position because they don't have a "
                    "Product:\n- %s\nYou should update the Account and the "
                    "Taxes of these invoice lines manually."
                ) % ('\n- '.join(lines_without_product))
        return res
    
    @api.model
    def freight_line_get(self):
        res = []
        freight_charges=self.freight_charges if ( self.freight_charges_type =='fixed' or self.freight_charges_type =='variable') else 0.0
        if self.freight_charges_type =='variable':
            freight_charges=round(self.amount_untaxed*freight_charges/100.0)   
        if freight_charges > 0.0: 
            res.append({
                    'invoice_id': self.id,
                    'type': 'src',
                    'name': self.freight_charges_type,
                    'price_unit': freight_charges,
                    'quantity': 1,
                    'price': freight_charges,
                    'account_id': self.freight_account.id,
                    'account_analytic_id': False,
                })
        return res
    
    @api.model
    def packing_line_get(self):
        res = []
        packing_charges=self.packing_charges if ( self.packing_charges_type =='fixed' or self.packing_charges_type =='variable') else 0.0
        if self.packing_charges_type =='variable':
            packing_charges=round(self.amount_untaxed*packing_charges/100.0)   
        
        if packing_charges > 0.0:
            res.append({
                    'invoice_id': self.id,
                    'type': 'src',
                    'name': self.packing_charges_type,
                    'price_unit': packing_charges,
                    'quantity': 1,
                    'price': packing_charges,
                    'account_id': self.packing_account.id,
                    'account_analytic_id': False,
                })
        return res
    
    @api.model
    def tds_line_get(self):
        res = []
        if self.tds_amount > 0.0:
            res.append({
                    'invoice_id': self.id,
                    'type': 'src',
                    'name': self.tds_account.name,
                    'price_unit': self.tds_amount,
                    'quantity': 1,
                    'price': (-1)*self.tds_amount,
                    'account_id': self.tds_account.tds_account.id,
                    'account_analytic_id': False,
                })
        return res
    
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml =  inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()
            iml += inv.freight_line_get()
            iml += inv.packing_line_get()
            iml += inv.tds_line_get()
            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=inv.currency_id.id).compute(total, date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['dont_create_taxes'] = True
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True

    
def calculate_base(document,tax,value):
    freight=document.freight_charges if ( document.freight_charges_type=='fixed' or document.freight_charges_type=='variable' ) else False
    packing=document.packing_charges if ( document.packing_charges_type=='fixed' or document.packing_charges_type=='variable' ) else False

    taxable_freight=False
    taxable_packing=False
    
    if ( freight and tax.freight_charges and document.freight_charges_type=='variable'):            
        taxable_freight=value['val']*(freight/100.00)
    elif ( freight and tax.freight_charges and document.freight_charges_type=='fixed'): 
        taxable_freight=freight
        
    if ( packing and tax.packing_charges and document.packing_charges_type=='variable'):            
        taxable_packing=value['val']*(packing/100.00)
    elif ( packing and tax.packing_charges and document.packing_charges_type=='fixed'): 
        taxable_packing=packing               
        
    value['val']=(value['val']+taxable_freight) if taxable_freight else value['val']
    value['val']=(value['val']+taxable_packing) if taxable_packing else value['val']
    return value    
    
    
class kts_account_invoice_line_tax_include(models.Model):
    _inherit='account.invoice.line'
     
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * self.quantity* (1 - (self.discount or 0.0) / 100.0) 
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, 1.0, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        #self.update({'price_subtotal':self.price_subtotal})
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
    

class kts_account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"
    base_amount=fields.Float('Base Amount', digits=dp.get_precision('Account'), store=True)
    tax_type =fields.Selection(related='tax_id.tax_category', string='Tax Type', store=True)
    sequence=fields.Integer(related='tax_id.sequence',store=True)

class kts_account_tds(models.Model):
    _name = "account.ktstds"
    name= fields.Char('Name', size=256, index=True)
    tds_account=fields.Many2one('account.account', 'TDS Account')
    precision=fields.Many2one('decimal.precision', 'Precision')
    active= fields.Boolean('Active',default=True) 
    perc = fields.Float('Percentage',default=0.0)

class kts_dispatch_mode(models.Model):
    _name='kts.dispatch.mode'
    name=fields.Char('Name')

class kts_sale_order(models.Model):
    _inherit='sale.order'
    @api.depends('order_line.price_subtotal','freight_charges','packing_charges',)
    def _compute_order_tax(self):
        self.ensure_one()
        test=self._context.get('tax_line_ids')
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():   
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        
    @api.multi
    def write(self,vals):
        res = super(kts_sale_order, self).write(vals)
        return res
        
    @api.one
    @api.depends('order_line.price_subtotal','tax_line_ids.amount')
    def _amount_all(self):
        for order in self:         
            order.amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            packing_charges=order.packing_charges if ( order.packing_charges_type =='fixed' or order.packing_charges_type =='variable') else 0.0
        
            freight_charges=order.freight_charges if ( order.freight_charges_type =='fixed' or order.freight_charges_type =='variable') else 0.0
            if order.packing_charges_type =='variable':
                 packing_charges=round(order.amount_untaxed*packing_charges/100.0) 
            if order.freight_charges_type =='variable':
                 freight_charges=round(order.amount_untaxed*freight_charges/100.0)   
        
            order.freight_and_packing = packing_charges + freight_charges
            order.amount_tax = sum(line.amount for line in order.tax_line_ids)
            order.amount_total = order.amount_untaxed + order.amount_tax +order.freight_and_packing 
            if order.fiscal_position_id.price_include:
                order.amount_total = round(order.amount_total,0)
    
    packing_account=fields.Many2one('account.account', 'Packing Account', readonly=True, states={'draft': [('readonly', False)]})
    freight_account=fields.Many2one('account.account', 'Freight Account', readonly=True, states={'draft': [('readonly', False)]})   
    packing_charges= fields.Float('Packing charges', readonly=True, states={'draft': [('readonly', False)]})            
    freight_charges= fields.Float('Freight charges', readonly=True, states={'draft': [('readonly', False)]})
    tax_type = fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service')], 'Tax Type',default='no_tax', readonly=True, states={'draft': [('readonly', False)],'sent': [('readonly', False)]})  
    packing_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'Packing Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    freight_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'Freight Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    tax_line_ids = fields.One2many('sale.order.tax', 'order_id', string='Tax Lines', readonly=True, store=True, states={'draft': [('readonly', False)]},copy=True, compute= _compute_order_tax)
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position',domain=[('type','=','out_invoice')],readonly=True, states={'draft': [('readonly', False)],'sent': [('readonly', False)]}  )
    freight_and_packing = fields.Monetary('Freight And Packing',digits=dp.get_precision('account'), compute='_amount_all')
    order_line = fields.One2many('sale.order.line', 'order_id', string='Order Lines', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True, required=True)
    dispatch_mode=fields.Many2one('kts.dispatch.mode','Dispatch Mode')
    client_order_ref_date=fields.Date('Customer Ref Date')
    
    
#     @api.onchange('tax_type','validity_date')
#     def tax_type_onchange(self):
#         res=[]
#         warn={}
#         self.ensure_one()
#         if not self.tax_type:
#             return
#         type = 'out_invoice'
#         tax_type=self.tax_type
#         fspo = self.env['account.fiscal.position'].search(['&',('tax_type','=',tax_type),('type','=',type)]) 
#         for i in fspo:
#             if i.end_date and self.validity_date and i.end_date > self.validity_date:
#                 res.append(i.id)  
#             elif i.end_date and self.validity_date and i.end_date < self.validity_date:
#                   warn= {'warning': {
#                         'title': _('Warning'),
#                         'message':  (_('%s This fiscal position is not valide for upto this date')% i.name)
#                          } }
#                   
#             else: res.append(i.id)
#         if warn:
#              return  warn 
#         return {'domain':{'fiscal_position_id':[('id','in',res)]  } }        
        
    @api.onchange('fiscal_position_id')
    def fiscal_position_change(self):
        """Updates taxes and accounts on all invoice lines"""
        self.ensure_one()
        res = {}
        lines_without_product = []
        fp = self.fiscal_position_id
        inv_type = 'out_invoice'
        for line in self.order_line:
            if line.product_id:
                product = line.product_id
                if inv_type in ('out_invoice', 'out_refund'):
                    taxes = product.taxes_id
                else:                        
                    taxes = product.supplier_taxes_id
                    taxes = taxes or account.tax_ids
                if fp:
                    
                    taxes = fp.map_tax(taxes)

                line.tax_id = [(6, 0, taxes.ids)]
                
            else:
                lines_without_product.append(line.name)

        if lines_without_product:
            res['warning'] = {'title': _('Warning')}
            if len(lines_without_product) == len(self.order_line):
                res['warning']['message'] = _(
                    "The invoice lines were not updated to the new "
                    "Fiscal Position because they don't have products.\n"
                    "You should update the Account and the Taxes of each "
                    "invoice line manually.")
            else:
                res['warning']['message'] = _(
                    "The following invoice lines were not updated "
                    "to the new Fiscal Position because they don't have a "
                    "Product:\n- %s\nYou should update the Account and the "
                    "Taxes of these invoice lines manually."
                ) % ('\n- '.join(lines_without_product))
        return res
       
#     @api.onchange('order_line','tax_line_ids','freight_charges','packing_charges')
#     def onchange_compute_order_tax(self):
#         self.ensure_one()
#         taxes_grouped = self.get_taxes_values()
#         tax_lines = self.tax_line_ids.browse([])
#         for tax in taxes_grouped.values():
#             tax_lines += tax_lines.new(tax)
#         self.tax_line_ids = tax_lines
#         self.update({'tax_line_ids':self.tax_line_ids})
#         return 
#     
    @api.multi
    def  get_taxes_values(self):
        tax_line={}
        
        for line in self.order_line:
            for tax in line.tax_id:
                if tax in tax_line: 
                    tax_line.update({tax:{'val':tax_line[tax]['val']+(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.product_uom_qty), 'order_line':line}})
                else:
                    tax_line.update({tax:{'val':(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.product_uom_qty), 'order_line':line}})
        tax_independent=[]
        tax_with_sub_taxes=[]
        
        for key, value in tax_line.iteritems():
            if len(key.sub_tax_ids)>0:
                tax_with_sub_taxes.append({'order_line':value['order_line'], 'tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False})
            else:
                value=calculate_base(self, key, value )
                tax_independent.append({'order_line':value['order_line'], 'tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False})

        #step 3: calculate tax for both types of taxes
        calculated_taxes=[]                    
        for line in tax_independent:
            val=self.calculate_tax(line['order_line'],line['tax_id'], line['price_unit'], line['quantity'], line['product_id'])
            calculated_taxes.append(val)
                                    
        for line in tax_with_sub_taxes:
            sub_taxt_base=0.0
            for tax_id in line['tax_id'].sub_tax_ids:
                base_sub_tax=calculate_base(self, tax_id, {'val':line['price_unit']})
                val=self.calculate_tax(line['order_line'],tax_id, base_sub_tax['val'], line['quantity'], line['product_id'])
                sub_taxt_base=sub_taxt_base+ val['amount']
            base=calculate_base(self,line['tax_id'], {'val':line['price_unit']})['val']+sub_taxt_base
            val=self.calculate_tax(line['order_line'],line['tax_id'], base, line['quantity'], line['product_id'])
            calculated_taxes.append(val)
            
        #step 4: group taxes and return
        tax_grouped = {}
        for tax in calculated_taxes:
            key = tax['id']
            if key not in tax_grouped:
                tax_grouped[key] =  tax
            else:
                tax_grouped[key]['amount'] += tax['amount']   
            del tax['id']
        return tax_grouped
    
    def calculate_tax(self,line,tax_ids,price_unit,quantity, product_id ):
        ctx=dict(self._context)
        ctx.update({'tax':True})
        taxes = tax_ids.with_context(ctx).compute_all(price_unit, self.currency_id, quantity, product_id, self.partner_id)['taxes']
        for tax in taxes:
            val = {
                'id': tax['id'],
                'order_id': self.id,
                'name': tax['name'],
                'tax_id': tax['id'],
                'amount': tax['amount'],
                'manual': False,
                'sequence': tax['sequence'],
                'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
                }

            # If the taxes generate moves on the same financial account as the invoice line,
            # propagate the analytic account from the invoice line to the tax line.
            # This is necessary in situations were (part of) the taxes cannot be reclaimed,
            # to ensure the tax move is allocated to the proper analytic account.
           
        return val
   
    @api.multi
    def _prepare_invoice(self):
        res = super(kts_sale_order, self)._prepare_invoice()
        res.update({
                    'freight_charges_type':self.freight_charges_type,
                    'packing_charges_type':self.packing_charges_type,
                    'freight_charges':self.freight_charges,
                    'packing_charges':self.packing_charges,
                    'tax_type':self.tax_type,
                    'dispatch_mode':self.dispatch_mode.id
                    })    
        return res
class kts_sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id',)
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        
        for line in self:
                 if line.product_id:
                    price = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, 1.0, product=line.product_id, partner=line.order_id.partner_id)
                    line.price_subtotal = taxes['total_excluded']
                    
   
   # tax_id = fields.Many2many('account.tax','sale_order_line_tax_rel','order_line_id','tax_id', string='Taxes')
    


class SaleOrderTax(models.Model):
    _name = "sale.order.tax"
    _description = "Sale order Tax"
    
    @api.model
    def create(self, vals):
        test=vals
        if vals.get('order_id'):
            order_id=vals.get('order_id')
            tax_id=vals.get('tax_id')
            ret=self.search([('order_id','=',order_id),('tax_id','=',tax_id)]).ids
            if ret:
               dupl_tax=self.browse(ret)
               dupl_tax.unlink() 
        res=super(SaleOrderTax, self).create(vals)
        return res
    
    @api.multi
    def write(self,vals):
        test=vals
        res=super(SaleOrderTax, self).write(vals)
        return res
        
        
    order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade', index=True)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax')
    account_id = fields.Many2one('account.account', string='Tax Account', domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Float(string='amount')
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True, readonly=True)

    
class kts_purchase_order(models.Model):
    _inherit = 'purchase.order' 
    
    @api.depends('order_line.price_subtotal','freight_charges','packing_charges','fiscal_position_id','order_line.discount',)
    def _compute_order_tax(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        
    
    @api.depends('order_line.price_subtotal','tax_line_ids.amount', 'currency_id', 'company_id','freight_charges','packing_charges',)
    def _amount_all(self ):
        self.amount_untaxed = sum(line.price_subtotal for line in self.order_line)
        packing_charges=self.packing_charges if ( self.packing_charges_type =='fixed' or self.packing_charges_type =='variable') else 0.0

        freight_charges=self.freight_charges if ( self.freight_charges_type =='fixed' or self.freight_charges_type =='variable') else 0.0
        if self.packing_charges_type =='variable':
            packing_charges=round(self.amount_untaxed*packing_charges/100.0) 
        if self.freight_charges_type =='variable':
            freight_charges=round(self.amount_untaxed*freight_charges/100.0)   
        
        self.freight_and_packing = packing_charges + freight_charges
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax +self.freight_and_packing
    
    
                
    packing_account=fields.Many2one('account.account', 'Packing Account', readonly=True, states={'draft': [('readonly', False)]})
    freight_account=fields.Many2one('account.account', 'Freight Account', readonly=True, states={'draft': [('readonly', False)]})   
    packing_charges= fields.Float('Packing charges', readonly=True, states={'draft': [('readonly', False)]})            
    freight_charges= fields.Float('Freight charges', readonly=True, states={'draft': [('readonly', False)]})
    tax_type = fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service')], 'Tax Type', default='no_tax',readonly=True,states={'draft': [('readonly', False)],'sent': [('readonly', False)]})  
    
    packing_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'Packing Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    freight_charges_type= fields.Selection([('fixed','Fixed'), ('variable','Percentage'),('nil','Nil')], 'Freight Charges Type', readonly=True, states={'draft': [('readonly', False)]})
    tax_line_ids = fields.One2many('purchase.order.tax', 'order_id', string='Tax Lines', store=True,
        readonly=True, states={'draft': [('readonly', False)]}, copy=True,compute= _compute_order_tax)
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position',domain=[('type','=','in_invoice')],readonly=True,states={'draft': [('readonly', False)],'sent': [('readonly', False)]} )
    freight_and_packing = fields.Monetary('Freight And Packing',digits=dp.get_precision('account'), compute='_amount_all') 
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines', copy=True, required=True)
    date_planned = fields.Datetime(string='Scheduled Date', inverse='', required=True, index=True, oldname='minimum_planned_date') 
    note=fields.Text('Notes')
    
#     @api.onchange('tax_type')
#     def tax_type_onchange(self):
#         self.ensure_one()
#         if not self.tax_type:
#             return
#         type='in_invoice'
#         tax_type=self.tax_type
#         fspo = self.env['account.fiscal.position'].search(['&',('tax_type','=',tax_type),('type','=',type)])  
#         return {'domain':{'fiscal_position_id':[('id','in',fspo.ids)]  } }        
#         
    @api.onchange('fiscal_position_id')
    def fiscal_position_change(self):
        """Updates taxes and accounts on all invoice lines"""
        self.ensure_one()
        res = {}
        lines_without_product = []
        fp = self.fiscal_position_id
        inv_type = 'in_invoice'
        for line in self.order_line:
            if line.product_id:
                product = line.product_id
                if inv_type in ('in_invoice', 'in_refund'):
                    taxes = product.taxes_id
                    taxes = product.supplier_taxes_id
                    taxes = taxes 
                if fp:
                    
                    taxes = fp.map_tax(taxes)

                line.taxes_id = [(6, 0, taxes.ids)]
                
            else:
                lines_without_product.append(line.name)

        if lines_without_product:
            res['warning'] = {'title': _('Warning')}
            if len(lines_without_product) == len(self.order_line):
                res['warning']['message'] = _(
                    "The invoice lines were not updated to the new "
                    "Fiscal Position because they don't have products.\n"
                    "You should update the Account and the Taxes of each "
                    "invoice line manually.")
            else:
                res['warning']['message'] = _(
                    "The following invoice lines were not updated "
                    "to the new Fiscal Position because they don't have a "
                    "Product:\n- %s\nYou should update the Account and the "
                    "Taxes of these invoice lines manually."
                ) % ('\n- '.join(lines_without_product))
        return res
                
    @api.multi
    def  get_taxes_values(self): 
        tax_line={}   
        for line in self.order_line:
            for tax in line.taxes_id:
                if tax in tax_line: 
                    tax_line.update({tax:{'val':tax_line[tax]['val']+(line.price_unit*(1-(line.discount or 0.0)/100.0)*line.product_qty), 'order_line':line}})
                else:
                    tax_line.update({tax:{'val':(line.price_unit *(1-(line.discount or 0.0)/100.0)*line.product_qty), 'order_line':line}})
        tax_independent=[]
        tax_with_sub_taxes=[]
        
        for key, value in tax_line.iteritems():
            if len(key.sub_tax_ids)>0:
                tax_with_sub_taxes.append({'order_line':value['order_line'], 'tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False})
            else:
                value=calculate_base(self, key, value )
                tax_independent.append({'order_line':value['order_line'], 'tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False})

        #step 3: calculate tax for both types of taxes
        calculated_taxes=[]                    
        for line in tax_independent:
            val=self.calculate_tax(line['order_line'],line['tax_id'], line['price_unit'], line['quantity'], line['product_id'])
            calculated_taxes.append(val)
                                    
        for line in tax_with_sub_taxes:
            sub_taxt_base=0.0
            for tax_id in line['tax_id'].sub_tax_ids:
                base_sub_tax=calculate_base(self, tax_id, {'val':line['price_unit']})
                val=self.calculate_tax(line['order_line'],tax_id, base_sub_tax['val'], line['quantity'], line['product_id'])
                sub_taxt_base=sub_taxt_base+ val['amount']
            base=calculate_base(self,line['tax_id'], {'val':line['price_unit']})['val']+sub_taxt_base
            val=self.calculate_tax(line['order_line'],line['tax_id'], base, line['quantity'], line['product_id'])
            calculated_taxes.append(val)
            
        #step 4: group taxes and return
        tax_grouped = {}
        for tax in calculated_taxes:
            key = tax['id']
            if key not in tax_grouped:
                tax_grouped[key] =  tax
            else:
                tax_grouped[key]['amount'] += tax['amount']   
            del tax['id']
        return tax_grouped
    
    def calculate_tax(self,line,tax_ids,price_unit,quantity, product_id ):
        taxes = tax_ids.compute_all(price_unit, self.currency_id, quantity, product_id, self.partner_id)['taxes']
        for tax in taxes:
            val = {
                'id': tax['id'],
                'order_id': self.id,
                'name': tax['name'],
                'tax_id': tax['id'],
                'amount': tax['amount'],
                'manual': False,
                'sequence': tax['sequence'],
                'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
                }

            # If the taxes generate moves on the same financial account as the invoice line,
            # propagate the analytic account from the invoice line to the tax line.
            # This is necessary in situations were (part of) the taxes cannot be reclaimed,
            # to ensure the tax move is allocated to the proper analytic account.
           
        return val
    
    @api.multi
    def action_view_invoice(self):
        result = super(kts_purchase_order, self).action_view_invoice()
        if self.amount_tax:
            result['context']['default_amount_tax']=self.amount_tax
        if self.packing_charges > 0.0:
            result['context']['default_packing_charges_type'] = self.packing_charges_type
            result['context']['default_packing_charges'] = self.packing_charges
        if self.freight_charges > 0.0:
            result['context']['default_freight_charges_type'] = self.freight_charges_type
            result['context']['default_freight_charges'] = self.freight_charges
        if self.tax_type:
            result['context']['default_tax_type'] = self.tax_type
        if self.fiscal_position_id:
            result['context']['default_fiscal_position_id'] = self.fiscal_position_id.id
        return result
        
            
    
class kts_purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    supplier_schedule_date= fields.Datetime(string='Supplier Schedule Date', )
    #new field is add here
    
    @api.onchange('product_qty', 'product_uom', 'price_unit')
    def _onchange_quantity(self):
        if not self.product_id:
            return

        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order[:10],
            uom_id=self.product_uom)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.supplier_schedule_date=self._get_supplier_schedule_date(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if not seller:
            return

        price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, self.product_id.supplier_taxes_id, self.taxes_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id.compute(price_unit, self.order_id.currency_id)

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = self.env['product.uom']._compute_price(seller.product_uom.id, price_unit, to_uom_id=self.product_uom.id)

        self.price_unit = price_unit

    
  
    @api.depends('product_qty', 'discount', 'price_unit', 'taxes_id', 'product_uom', )
    def _compute_amount(self):
        for line in self:
                 if line.product_id: 
                    price=line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
                    line.price_subtotal = taxes['total_excluded']
                    
    
    @api.model
    def _get_date_planned(self, seller, po=False):
        date_order = po.date_order if po else self.order_id.date_order
        if po:
           po_incoterms_flag=po.incoterm_id.trans_supplier_lead_sep  
        elif self.order_id.incoterm_id.id:
             if self.order_id.incoterm_id.trans_supplier_lead_sep:
                 po_incoterms_flag=True
             else:
                   po_incoterms_flag=False
        else:
             po_incoterms_flag=False
        
        if po_incoterms_flag and date_order:
            return datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=seller.delay if seller else 0) +relativedelta(days=seller.trans_lead_time if seller else 0)  
        elif date_order:
            return datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)


    
    @api.model
    def _get_supplier_schedule_date(self, seller, po=False):
        
        date_order = po.date_order if po else self.order_id.date_order
        if date_order:
            return datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)

    
    
   


class PurchaseOrderTax(models.Model):
    _name = "purchase.order.tax"
    _description = "purchase order Tax"
    _order = 'sequence'

    order_id = fields.Many2one('purchase.order', string='Purchase Order', ondelete='cascade', index=True)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax')
    account_id = fields.Many2one('account.account', string='Tax Account', domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Monetary()
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True, readonly=True)

class kts_product_default_taxes(models.Model):
    
    _inherit = 'product.template' 
    serial_sequence=fields.Many2one('ir.sequence', string='Serial Sequnce')
    
    @api.model
    def default_get(self, fields):
        if self._context:  
           res = super(kts_product_default_taxes, self).default_get(fields)
           taxes_id = self.env['account.tax'].search([('tax_type','=','sales_tax')])
           supplier_taxes_id = self.env['account.tax'].search([('tax_type','=','purchase_tax')])
           both = self.env['account.tax'].search([('tax_type','=','sales_purchase_tax')])
           tax_obj = self.env['account.tax'].search([])
           for tax in tax_obj:                     
               if tax.tax_type == 'sales_tax':
                     res.update({'taxes_id':taxes_id.ids})
               if tax.tax_type == 'purchase_tax':
                     res.update({'supplier_taxes_id':supplier_taxes_id.ids})   
               if tax.tax_type == 'sales_purchase_tax':
                     res.update({'taxes_id':both.ids,
                               'supplier_taxes_id':both.ids})           
           return res
       
class kts_payment(models.Model):
    _inherit = 'account.payment'
    note = fields.Char('Note')
    cheque_no = fields.Char('Cheque No')
    cheque_date = fields.Date('Cheque Date')
    Payee_name = fields.Char('Payee Name')
    
    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Set partner_id domain
        if self.partner_type:
            return {'domain': {'partner_id': [(self.partner_type, '=', True),('parent_id','=',False)]}}

            
class kts_bank_statement(models.Model):
    _inherit='account.bank.statement'
    note = fields.Char('Note')
    cheque_no = fields.Char('Cheque No')
    cheque_date = fields.Date('Cheque Date')
    Payee_name = fields.Char('Payee Name')

class kts_product_template(models.Model):
    _inherit='product.template'
    serialno = fields.Boolean('Auto Generate Serialno')

class kts_control_account(models.Model):
    _name='kts.control.account'
    name=fields.Char(string="Name")
    emp_flag = fields.Boolean('Employee Tags',default=False)
    creditor_acc_tag_ids = fields.Many2many('account.account.tag', 'kts_control_account_tag', string='Creditor Tags', help="Optional tags you may want to assign for custom reporting(Vendor)")
    debitor_acc_tag_ids = fields.Many2many('account.account.tag', 'kts_control_account_tag1', string='Debitor Tags', help="Optional tags you may want to assign for custom reporting(customer)")
    creditor_ledger_tag_id= fields.Many2one('account.account.tag',  string='Creditor Ledger Tags', help="Optional tags you may want to assign for custom reporting(Vendor)")
    debtor_ledger_tag_id= fields.Many2one('account.account.tag' , string='Debtor Ledger Tags', help="Optional tags you may want to assign for custom reporting(customer)")
    creditor_bal_sheet_tag_id= fields.Many2one('account.account.tag', string='Creditor Balance Sheet Tags', help="Optional tags you may want to assign for custom reporting(Vendor)")
    debtor_bal_sheet_tag_id= fields.Many2one('account.account.tag', string='Debtor Balance Sheet Tags', help="Optional tags you may want to assign for custom reporting(customer)")
    ledger_report_type=fields.Selection([
        ('summ', 'Summary'),
        ('detailed', 'Detailed'),
        ('tag_summ', 'Tag Summary')
        ], string='Ledger Report Type', default='summ')   

class kts_res_partner(models.Model):
    _inherit='res.partner'
    
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable", oldname="property_account_payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=False)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable", oldname="property_account_receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=False)
     
    
    @api.model
    def create(self,vals):
         
        if not vals.get('parent_id'):
           if vals.get('name'):
              obj_acc = self.env['account.account']
              emp_tags=False 
              customer=vals.get('customer') if vals.get('customer')==True else False
              supplier=vals.get('supplier') if vals.get('supplier')==True else False
              
              if customer==False and supplier==False:
                  emp_tags=True
                  code_payable = self.env['ir.sequence'].next_by_code('kts.account.account.code.payable.emp')
                  code_receivable = self.env['ir.sequence'].next_by_code('kts.account.account.code.receivable.emp')
              else:
                  emp_tags=False
                  code_payable = self.env['ir.sequence'].next_by_code('kts.account.account.code.payable')
                  code_receivable = self.env['ir.sequence'].next_by_code('kts.account.account.code.receivable')
              
              vals1={
                    'name': vals.get('name') + ' Payable',       
                    'code':code_payable,
                    'user_type_id': 2,       
                    'reconcile':True,
                    'tag_ids':[(6,0,self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).creditor_acc_tag_ids.ids)],
                    'ledger_tag':self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).creditor_ledger_tag_id.id,
                    'bal_sheet_tag':self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).creditor_bal_sheet_tag_id.id,                                   
                    'ledger_report_type':self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).ledger_report_type,
                    }
              
              vals2={
                    'name':vals.get('name')+' Receivable',       
                    'code':code_receivable,
                    'user_type_id': 1,
                    'reconcile':True,
                    'tag_ids':[(6,0,self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).debitor_acc_tag_ids.ids)],       
                    'ledger_tag':self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).debtor_ledger_tag_id.id,
                    'bal_sheet_tag':self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).debtor_bal_sheet_tag_id.id,                                     
                    'ledger_report_type':self.env['kts.control.account'].search([('emp_flag','=',emp_tags)],limit=1).ledger_report_type,
                    }
              obj1=obj_acc.create(vals1)
              obj2=obj_acc.create(vals2)
              property_account_payable_id = obj1.id
              property_account_receivable_id = obj2.id 
              
              vals.update({
                        'property_account_payable_id':obj1.id,
                        'property_account_receivable_id':obj2.id,
                        })            
              return super(kts_res_partner, self).create(vals)
        return super(kts_res_partner, self).create(vals)   

class kts_account_level(models.Model):
    _name='kts.account.level'
    name=fields.Char('Name', required=True)
    order=fields.Integer('Order')
    note=fields.Integer('Note')
    account_ids=fields.Many2many('account.account','account_level_account_tag_rel',string='Account Lines', )
    tag_ids=fields.Many2many('account.account.tag','account_level_account_tag1_rel',string='Tag Lines', )
    level1=fields.Selection([
        ('1', 'EQUITY AND LIABILITIES'),
        ('2', 'ASSETS'),
        ], string='Level1', default='1')
    level2=fields.Selection([
        ('1', 'Shareholder\'s Fund'),
        ('2', 'Non Current Liabilities'),
        ('3','Current liabilities'),
        ('4','Non Current Assets'),
        ('5','Current assets'),
        ], string='Level2', default='1')

    @api.model
    def create(self,vals):
        if not vals.get('account_ids') and not vals.get('tag_ids'):
            raise UserError(_('Please select Account or Tag'))
        return super(kts_account_level, self).create(vals)
    
    @api.multi
    def write(self,vals):
        account_ids=vals.get('account_ids')
        tag_ids=vals.get('tag_ids')
        if vals.get('account_ids') and not account_ids[0][2] and len(self.tag_ids.ids) <= 0:
            raise UserError(_('Please select Account or Tag to save'))
        
        elif vals.get('tag_ids') and not tag_ids[0][2] and len(self.account_ids.ids) <= 0:
            raise UserError(_('Please select Account or Tag to save'))
        
        elif vals.get('tag_ids') and not tag_ids[0][2] and vals.get('account_ids') and not account_ids[0][2]:
            raise UserError(_('Please select Account or Tag to save'))
        
        return super(kts_account_level, self).write(vals)
          
class kts_account_account_tag(models.Model):
    _inherit='account.account.tag'
    
class kts_account_account(models.Model):
    _inherit='account.account'
    ledger_report_type=fields.Selection([
        ('summ', 'Summary'),
        ('detailed', 'Detailed'),
        ('tag_summ', 'Tag Summary')
        ], string='Ledger Report Type', default='summ')
    ledger_tag=fields.Many2one('account.account.tag', string='Ledger Tag')
    bal_sheet_tag=fields.Many2one('account.account.tag', string='Balance Sheet')

class kts_stock_picking(models.Model):
    _inherit='stock.picking' 
    sale_id = fields.Many2one(comodel_name='sale.order', string="Sale Order", compute='_compute_sale_id',store=True)
    purchase_new_id = fields.Many2one('purchase.order', string="Purchase Order",)


class kts_purchase_order_id(models.Model):
      _inherit='purchase.order'
      
      @api.onchange('incoterm_id')
      def onchange_incoterm_id(self):
          if (self.order_line.ids)>0:
             for line in self.order_line:
                 seller = line.product_id._select_seller(
                                                 partner_id=line.partner_id,
                                                 quantity=line.product_qty,
                                                 date=line.order_id.date_order and line.order_id.date_order[:10],
                                                 uom_id=line.product_uom)

                 if seller or not line.date_planned:
                    line.date_planned=line._get_date_planned(seller,self).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    line.supplier_schedule_date=line._get_supplier_schedule_date(seller,self).strftime(DEFAULT_SERVER_DATETIME_FORMAT)              
                 
      @api.model
      def _prepare_picking(self):
          res =super(kts_purchase_order_id, self)._prepare_picking()
          res.update({
                    'purchase_new_id':self.id,
                    }) 
          return res

class kts_product_supplierinfo(models.Model):    
    _inherit='product.supplierinfo'
    trans_lead_time=fields.Integer(string='Transport Lead Time')

class kts_stock_incoterms(models.Model):
    _inherit='stock.incoterms'
    trans_supplier_lead_sep=fields.Boolean('Separater transport and supplier lead time',default=False)
    
    
        