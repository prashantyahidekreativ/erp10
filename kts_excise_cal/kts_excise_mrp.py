from odoo import models, fields, api,_
import odoo.addons.decimal_precision as dp
from odoo import exceptions, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class kts_abatement_master(models.Model):
    _name='kts.abatement.master'
    name=fields.Char('Name', required=True)
    perc=fields.Float('Percentage',required=True,default=0.0)

class kts_product_template_excise(models.Model):
    _inherit='product.template'
    mrp_price = fields.Float(string='Maximum Retail Price',digits=dp.get_precision('Product Price'),default=0.0)
    excise_app = fields.Boolean(string='Excise Applicable',default=False)
    abatement_id = fields.Many2one('kts.abatement.master',string='Excise Abatement')
  
class kts_sale_order_line_excise(models.Model):
    _inherit='sale.order.line'

    @api.depends( 'mrp_price','abatement_perc','product_uom_qty','product_id',)
    def _compute_net_mrp(self):
        for line in self:
            price = line.mrp_price * (1 - (line.abatement_perc or 0.0) / 100.0)
            net_mrp = price*line.product_uom_qty
            line.update({
                         'net_mrp':net_mrp
                         })
    
    mrp_price=fields.Float('MRP',digits=dp.get_precision('Product Price'),store=True,default=0.0)
    abatement_perc=fields.Float(string='Abatement',default=0.0)
    net_mrp=fields.Monetary(string='NetMRP',compute='_compute_net_mrp',readonly=True ,)
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not (self.product_uom and (self.product_id.uom_id.category_id.id == self.product_uom.category_id.id)):
            vals['product_uom'] = self.product_id.uom_id

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['name'] = name

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
        if self.product_id.excise_app:
            vals['mrp_price']= self.product_id.mrp_price
            vals['abatement_perc'] = self.product_id.abatement_id.perc
        self.update(vals)
        return {'domain': domain}
    
    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(kts_sale_order_line_excise, self)._prepare_invoice_line(qty)
        res.update({
                    'mrp_price':self.mrp_price,
                    'abatement_perc':self.abatement_perc,
                    'net_mrp':self.net_mrp,
                    })
        return res

class kts_sale_order_excise(models.Model):
    _inherit='sale.order'
    
    @api.multi
    def  get_taxes_values(self):
        tax_line={}
        
        for line in self.order_line:
            for tax in line.tax_id:
                if tax in tax_line:
                    if tax.price_include:
                       tax_line.update({tax:{'val':tax_line[tax]['val']+line.price_subtotal, 'order_line':line}})  
                    elif tax.applicable_mrp and line.product_id.excise_app:
                        tax_line.update({tax:{'val':tax_line[tax]['val']+(line.mrp_price* (1-(line.abatement_perc)/100.0)*line.product_uom_qty), 'order_line':line}})
                    else:
                        tax_line.update({tax:{'val':tax_line[tax]['val']+(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.product_uom_qty), 'order_line':line}})
                else:
                    if tax.price_include:
                      tax_line.update({tax:{'val':line.price_subtotal, 'order_line':line}}) 
                    
                    elif tax.applicable_mrp and line.product_id.excise_app:
                        tax_line.update({tax:{'val':(line.mrp_price* (1-(line.abatement_perc)/100.0)*line.product_uom_qty), 'order_line':line}})
                    else:
                        tax_line.update({tax:{'val':(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.product_uom_qty), 'order_line':line}})
        
        tax_independent=[]
        tax_with_sub_taxes=[]
        
        for key, value in tax_line.iteritems():
            if len(key.sub_tax_ids)>0:
                tax_with_sub_taxes.append({'order_line':value['order_line'], 'tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False})
            else:
                #value=calculate_base(self, key, value )
                tax_independent.append({'order_line':value['order_line'], 'tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False})

        #step 3: calculate tax for both types of taxes
        calculated_taxes=[]                    
                                    
        for line in tax_with_sub_taxes:
            sub_taxt_base=0.0
            for tax_id in line['tax_id'].sub_tax_ids: 
                    sub_tax_line={}
                    for line1 in self.order_line:
                        for line2 in line1.tax_id:
                            for tax in line2.sub_tax_ids:
                                    if tax in sub_tax_line:
                                       if tax.price_include:
                                          sub_tax_line.update({tax:{'val':sub_tax_line[tax]['val']+line1.price_subtotal, 'order_line':line1}})

                                       elif tax.applicable_mrp and line1.product_id.excise_app:
                                          sub_tax_line.update({tax:{'val':sub_tax_line[tax]['val']+(line1.mrp_price* (1-(line1.abatement_perc)/100.0)*line1.product_uom_qty), 'order_line':line1}})                   
                                       else:
                                          sub_tax_line.update({tax:{'val':sub_tax_line[tax]['val']+(line1.price_unit* (1-(line1.discount or 0.0)/100.0)*line1.product_uom_qty), 'order_line':line1}})

                                    else:
                                        if tax.price_include:
                                          sub_tax_line.update({tax:{'val':line1.price_subtotal, 'order_line':line1}})
                                        elif tax.applicable_mrp and line1.product_id.excise_app:
                                           sub_tax_line.update({tax:{'val':(line1.mrp_price* (1-(line1.abatement_perc)/100.0)*line1.product_uom_qty), 'order_line':line1}})   
                                        else:
                                            sub_tax_line.update({tax:{'val':(line1.price_unit* (1-(line1.discount or 0.0)/100.0)*line1.product_uom_qty), 'order_line':line1}}) 
                    for key, value in sub_tax_line.iteritems():
                        amount=value['val']
                    base_sub_tax=calculate_base(self, tax_id, {'val':amount})

               # if tax_id.applicable_mrp and line['product_id'].excise_app:
                #    base_sub_tax=calculate_base(self, tax_id, {'val':line['order_line'].mrp_price* (1-(line['order_line'].abatement_perc)/100.0)*line['order_line'].product_uom_qty})
                #else:  
                #   base_sub_tax=calculate_base(self, tax_id, {'val':line['price_unit']})
                    val=self.calculate_tax(line['order_line'],tax_id, base_sub_tax['val'], line['quantity'], line['product_id'])
                    sub_taxt_base=sub_taxt_base+ val['amount']
            base=calculate_base(self,line['tax_id'], {'val':line['price_unit']})['val']+sub_taxt_base
            val=self.calculate_tax(line['order_line'],line['tax_id'], base, line['quantity'], line['product_id'])
            calculated_taxes.append(val)
        
        for line in tax_independent:
            base=calculate_base(self,line['tax_id'], {'val':line['price_unit']})['val']
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
    
    
class kts_invoice_line_excise(models.Model):
    _inherit='account.invoice.line'
    
    @api.depends( 'mrp_price','abatement_perc','quantity','product_id',)
    def _compute_net_mrp(self):
        for line in self:
            price = line.mrp_price * (1 - (line.abatement_perc or 0.0) / 100.0)
            net_mrp = price*line.quantity
            line.update({
                         'net_mrp':net_mrp
                         })
    
    mrp_price=fields.Float('MRP',digits=dp.get_precision('Product Price'))
    abatement_perc=fields.Float(string='Abatement',)
    net_mrp=fields.Monetary(string='NetMRP',compute='_compute_net_mrp',store=True,readonly=True ,)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        vals={}
        if not self.invoice_id:
            return
        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        type = self.invoice_id.type

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id

            self.name = product.partner_ref
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()

            if type in ('in_invoice', 'in_refund'):
                if product.description_purchase:
                    self.name += '\n' + product.description_purchase
            else:
                if product.description_sale:
                    self.name += '\n' + product.description_sale

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:
                if company.currency_id != currency:
                    self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.invoice_id.date_invoice)).rate

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = self.env['product.uom']._compute_price(
                        product.uom_id.id, self.price_unit, self.uom_id.id)
            if type in ('out_invoice','in_refund') and self.product_id.excise_app:  
               vals['mrp_price']= self.product_id.mrp_price
               vals['abatement_perc'] = self.product_id.abatement_id.perc
               self.update(vals)
               domain['mrp_price']= self.product_id.mrp_price
               domain['abatement_perc'] = self.product_id.abatement_id.perc     
        return {'value':vals,
                'domain': domain}

class kts_account_invoice_excise(models.Model):
    _inherit='account.invoice'
    
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
                    if tax.price_include:
                       if tax.tax_category=='gst':
                           price= line.price_unit* (1-(line.discount or 0.0)/100.0)*line.quantity
                       else:
                           price= line.price_subtotal
                       tax_line.update({tax:{'val':tax_line[tax]['val']+price, 'order_line':line}}) 
                    elif tax.applicable_mrp and line.product_id.excise_app:
                        tax_line.update({tax:{'val':tax_line[tax]['val']+(line.mrp_price* (1-(line.abatement_perc)/100.0)*line.quantity), 'order_line':line}})
                    else:
                        tax_line.update({tax:{'val':tax_line[tax]['val']+(line.price_unit* (1-(line.discount or 0.0)/100.0)*line.quantity), 'order_line':line}})
                else:
                    if tax.price_include:
                        if tax.tax_category=='gst':
                           price= line.price_unit* (1-(line.discount or 0.0)/100.0)*line.quantity
                        else:
                           price= line.price_subtotal
                        tax_line.update({tax:{'val':price, 'order_line':line}}) 
                    elif tax.applicable_mrp and line.product_id.excise_app:
                        tax_line.update({tax:{'val':(line.mrp_price* (1-(line.abatement_perc)/100.0)*line.quantity), 'order_line':line}})
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
                #value=calculate_base(self, key, value )
                tax_independent.append({'invoice_line':value['order_line'], 'invoice_line_tax_id':key, 'quantity':1, 'product_id':value['order_line']['product_id'],
                            'price_unit':value['val'],'account_id':False,'tax_type':key.tax_category})

        #step 3: calculate tax for both types of taxes
        calculated_taxes=[]                                                
        for line in tax_with_sub_taxes:
            sub_taxt_base=0.0
            for tax_id in line['invoice_line_tax_id'].sub_tax_ids:
                #if tax_id.applicable_mrp and line['product_id'].excise_app:
                    sub_tax_line={}
                    for line1 in self.invoice_line_ids:
                        for line2 in line1.invoice_line_tax_ids:
                            for tax in line2.sub_tax_ids:
                                    if tax in sub_tax_line:
                                       if tax.price_include:
                                           sub_tax_line.update({tax:{'val':sub_tax_line[tax]['val']+line1.price_subtotal, 'order_line':line1}})
                                       elif tax.applicable_mrp and line1.product_id.excise_app:
                                          sub_tax_line.update({tax:{'val':sub_tax_line[tax]['val']+(line1.mrp_price* (1-(line1.abatement_perc)/100.0)*line1.quantity), 'order_line':line1}})                   
                                       else:
                                          sub_tax_line.update({tax:{'val':sub_tax_line[tax]['val']+(line1.price_unit* (1-(line1.discount or 0.0)/100.0)*line1.quantity), 'order_line':line1}})

                                    else:
                                        if tax.price_include:
                                          sub_tax_line.update({tax:{'val':line1.price_subtotal, 'order_line':line1}})
                                       
                                        elif tax.applicable_mrp and line1.product_id.excise_app:
                                           sub_tax_line.update({tax:{'val':(line1.mrp_price* (1-(line1.abatement_perc)/100.0)*line1.quantity), 'order_line':line1}})   
                                        else:
                                            sub_tax_line.update({tax:{'val':(line1.price_unit* (1-(line1.discount or 0.0)/100.0)*line1.quantity), 'order_line':line1}}) 
                    for key, value in sub_tax_line.iteritems():
                        amount=value['val']
                    base_sub_tax=calculate_base(self, tax_id, {'val':amount})
                #else: 
                   #base_sub_tax=calculate_base(self, tax_id, {'val':line['price_unit']})
                    
                    val=self.calculate_tax(line['invoice_line'],tax_id, base_sub_tax['val'], line['quantity'], line['product_id'])
                    
                    sub_taxt_base=sub_taxt_base+ val['amount']
            
            #if self.fiscal_position_id.price_include:
            #   sub_taxt_base=-sub_taxt_base
            base=calculate_base(self,line['invoice_line_tax_id'], {'val':line['price_unit']})['val']+sub_taxt_base #+sub_taxt_base
            
                    
            val=self.calculate_tax(line['invoice_line'],line['invoice_line_tax_id'], base, line['quantity'], line['product_id'])
            val.update({'tax_type':line['tax_type']})
            calculated_taxes.append(val)
        
        for line in tax_independent:
            base=calculate_base(self,line['invoice_line_tax_id'], {'val':line['price_unit']})['val']
                  
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

class kts_account_tax_excise(models.Model):
    _inherit='account.tax'
    applicable_mrp = fields.Boolean(string='Applicable on MRP',)  
    
    @api.onchange('price_include','packing_charges','freight_charges','applicable_mrp')
    def onchange_price_include_reset(self):
        if self.price_include:
           if self.packing_charges or self.freight_charges or self.applicable_mrp:
               self.update({'packing_charges':False,'freight_charges':False,'applicable_mrp':False})
               return {'value':{'packing_charges':False,'freight_charges':False,'applicable_mrp':False},
                       'warning':{'title':'UserError', 'message':'If price Include in tax you cannot select freight/packing/MRP on tax!'}}
          