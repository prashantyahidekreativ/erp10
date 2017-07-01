from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from datetime import datetime
from odoo import SUPERUSER_ID

class kts_gst_partner(models.Model):
    _inherit='res.partner'
    partner_type = fields.Selection([('gst','GST'), ('uid','UID'),('gdi','GDI'),('no_app','Not Applicable')], 'Partner Type',default='no_app',required=True) 
    gstin = fields.Char('GSTIN')
    file = fields.Binary('GSTIN File')
    uid = fields.Char('UID')
    gdi = fields.Char('GDI')

class kts_gst_res_company(models.Model):
    _inherit='res.company'
    gstin = fields.Char('GSTIN',required=True)
    gstin_file = fields.Binary('GSTIN File')
    state_code = fields.Char('State Code')
    composition_flag = fields.Boolean('Composition', default=False)
    manufacturer_flag = fields.Boolean('Is Manufacturer', default=False)    
    gst_forced = fields.Boolean('GST Forced')
    gst_payment_flag = fields.Boolean('GST Advance Payment')
    
    @api.onchange('state_id')
    def onchange_state(self):
        if self.state_id:
            self.state_code = self.state_id.code
            self.update({'state_code':self.state_id.code})
            return {'value':{'state_code':self.state_id.code}}    

class kts_gst_account(models.Model):
    _name='kts.gst.account'
    name = fields.Char('Name',required=True)
    cgst = fields.Float('CGST Rate %',required=True)
    igst = fields.Float('IGST Rate %',required=True)
    sgst = fields.Float('SGST Rate %',required=True)

class kts_hsn_master(models.Model):
    _name='kts.hsn.master'
    name = fields.Char('Name',required=True)
    hsn_code = fields.Char('HSN Code',required=True)
    gst_account_id = fields.Many2one('kts.gst.account','GST Account Code',required=True)   

class kts_gst_product_product(models.Model):
    _inherit='product.template'
    hsn_id = fields.Many2one('kts.hsn.master', 'HSN Code')

class kts_gst_product_category(models.Model):
    _inherit='product.category'
    hsn_id = fields.Many2one('kts.hsn.master', 'HSN Code',required=True)
        
    
class kts_gst_master(models.Model):
    _name='kts.gst.master'
    
    name = fields.Char('Name')
    igst_in_acc_id = fields.Many2one('account.account','IGST Input Account')
    igst_out_acc_id = fields.Many2one('account.account','IGST output Account')
    cgst_in_acc_id = fields.Many2one('account.account','CGST Input Account')
    cgst_out_acc_id = fields.Many2one('account.account','CGST output Account')
    sgst_in_acc_id = fields.Many2one('account.account','SGST Input Account')
    sgst_out_acc_id = fields.Many2one('account.account','SGST output Account')
    
    igst_adv_acc_id = fields.Many2one('account.account','IGST Advance Account')
    sgst_adv_acc_id = fields.Many2one('account.account','SGST Advance  Account')
    cgst_adv_acc_id = fields.Many2one('account.account','CGST Advance Account')
    gst_paid_acc_id = fields.Many2one('account.account','GST Paid  Account')

class kts_gst_account_tax(models.Model):
    _inherit='account.tax'
    tax_category =  fields.Selection(selection_add=[('gst', 'GST')],required=True)
    gst_type = fields.Selection([('igst','IGST'),('cgst','CGST'),('sgst','SGST'), ], 'GST Type')
    gst_account_code_id = fields.Many2one('kts.gst.account','GST Account Code')
    
    @api.onchange('gst_type','type_tax_use')
    def onchange_gst_type(self):
        if not self.gst_type:
            return
        if self.type_tax_use and self.gst_type:
            res = self.env['kts.gst.master'].search([])
            gst_account = self.gst_type
            if res:
                if self.type_tax_use == 'sale':
                    gst_account +='_out_acc_id'
                elif self.type_tax_use == 'purchase':
                    gst_account +='_in_acc_id'
                account_id=getattr(res[0],gst_account)                      
                self.update({'account_id':account_id.id,
                             'refund_account_id':account_id.id
                             })
                return {'value':{'account_id':account_id.id,
                             'refund_account_id':account_id.id
                             }}
    @api.onchange('amount')
    def onchange_gst_tax(self):
        if self.tax_category =='gst':
            if not self.gst_type:
                raise UserError(_('Please Select Gst Type'))
            if not self.gst_account_code_id:
                raise UserError(_('Please Select Gst Account Code'))
            if self.gst_type and self.gst_account_code_id:
                if self.amount:
                    gst_type = str(self.gst_type)
                    rate = getattr(self.gst_account_code_id,gst_type)
                    if self.amount != rate:
                        return{'value':{'amount':0.0},
                               'warning':{'title':'UserError', 'message':'Please Insert correct rate as per GST Account Code Rate'}}

                              
                                        
        
        
class kts_gst_fiscal_position(models.Model):
    _inherit='account.fiscal.position'
    tax_type = fields.Selection(selection_add=[('gst', 'GST')],required=True)
    gst_apply = fields.Selection([('inter','Inter State'),('intra','Intra State'),('na','Not Applicable') ], 'GST Apply') 
    
    @api.model     # noqa
    def map_tax(self, taxes, product=None, partner=None):
        result = self.env['account.tax'].browse()
        for tax in taxes:
            tax_count = 0
            for t in self.tax_ids:
                if t.tax_src_id == tax:
                    tax_count += 1
                    if t.tax_dest_id:
                        result |= t.tax_dest_id
            if not tax_count:
                result |= tax
        if result and self.tax_type == 'gst' and product:
            for line in result:
                if not product.categ_id.hsn_id:
                    raise UserError(_('Product %s not having hsn code please add hsn code')% product.name)
                if (line.gst_account_code_id.id != product.hsn_id.gst_account_id.id): 
                   tax_obj=self.env['account.tax']
                   gst_acc_code=product.hsn_id.gst_account_id if product.hsn_id else product.categ_id.hsn_idgst_account_id  
                   
                   cgst=gst_acc_code.cgst
                   sgst=gst_acc_code.sgst
                   igst=gst_acc_code.igst
                   if self.gst_apply == 'inter' and  self.type=='out_invoice':    
                       domain=[('type_tax_use','=','sale'),
                               ('gst_account_code_id','=',gst_acc_code.id),
                               ('gst_type','in',['sgst','cgst']),('amount','=',sgst)]
                       tax_add_ids = tax_obj.search(domain)
                       return tax_add_ids
                   elif self.gst_apply == 'intra' and  self.type=='out_invoice':
                        domain=[('type_tax_use','=','sale'),
                               ('gst_account_code_id','=',gst_acc_code.id),
                               ('gst_type','=','igst'),('amount','=',igst)]
                        tax_add_ids = tax_obj.search(domain)    
                        return tax_add_ids
                   elif self.gst_apply == 'inter' and  self.type=='in_invoice':    
                       domain=[('type_tax_use','=','purchase'),
                               ('gst_account_code_id','=',gst_acc_code.id),
                               ('gst_type','in',['sgst','cgst']),('amount','=',sgst)]
                       tax_add_ids = tax_obj.search(domain)
                       return tax_add_ids
                   elif self.gst_apply == 'intra' and  self.type=='in_invoice':
                        domain=[('type_tax_use','=','purchase'),
                               ('gst_account_code_id','=',gst_acc_code.id),
                               ('gst_type','=','igst'),('amount','=',igst)]
                        tax_add_ids = tax_obj.search(domain)    
                        return tax_add_ids

        return result

class kts_gst_account_configuration(models.TransientModel):
    _inherit='account.config.settings'
    gst_forced = fields.Boolean('GST Forced at Account',default=False)    
    
    @api.onchange('gst_forced')
    def onchange_gst_forced(self):
        self.company_id.write({'gst_forced':self.gst_forced})  
        
        
class kts_gst_account_invoice(models.Model):
    _inherit='account.invoice'
    
    @api.model
    def _default_get_tax_type(self):
        if self.env.user.company_id.gst_forced:
            return 'gst'
        else:
            return 'no_tax'
    
    @api.model
    def _default_fiscal_position_id(self):
        if self._context.get('default_fiscal_position_id', False):
            return self.env['account.fiscal.position'].browse(self._context.get('default_fiscal_position_id'))
         
        inv_type = self._context.get('type') 
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        if self.env.user.company_id.gst_forced:
            domain = ['&',('type', '=', inv_type),('tax_type','=','gst')]
        else:
            domain = [('type', '=', inv_type)]
        res = self.env['account.fiscal.position'].search(domain)
        return {'domain':{'default_fiscal_position_id':[('id','in',res.ids)]} } 
  
    
    tax_type = fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service'),('gst','GST')], string='Tax Type',default=_default_get_tax_type,readonly=True,states={'draft': [('readonly', False)]})  
     
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
        readonly=True, states={'draft': [('readonly', False)]},default = _default_fiscal_position_id,)                                
    
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current sales order.")
    partner_state_code = fields.Char(related='partner_shipping_id.state_id.code',string='State Code',store=True)
    partner_type = fields.Selection(related='partner_id.partner_type',string='Partner Type',store=True)
    partner_gstin = fields.Char(related='partner_id.gstin',string='GSTIN',store=True)
    partner_udi = fields.Char(related='partner_id.uid',string='UIDN',store=True)
    partner_gdi = fields.Char(related='partner_id.gdi',string='GDIN',store=True)
    
    
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        
        delivery_addr=self.env['res.partner'].browse(addr['delivery'])
        
        
        if self.env.user.company_id.gst_forced:
           if self.partner_id.partner_type != 'gst':
               inv_type = self.type
               domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','na')]
           
               res = self.env['account.fiscal.position'].search(domain)
               self.update(values)
               return {'value':values,'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
           
           elif self.company_id.state_code != delivery_addr.state_id.code:   
              inv_type = self.type
              domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','intra')]
           
              res = self.env['account.fiscal.position'].search(domain)
              self.update(values)
              return {'value':values,'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
           else:
               inv_type = self.type
               domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','inter')]
           
               res = self.env['account.fiscal.position'].search(domain)
               self.update(values)
               return {'value':values,'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
                
        
        self.update(values)
    
    
    @api.onchange('tax_type','partner_shipping_id')
    def  onchange_tax_type(self):
          
         if self.tax_type:
             if self.company_id.gst_forced:
                if self.tax_type !='gst':
                   return{'value':{'tax_type':'gst'},
                               'warning':{'title':'UserError', 'message':'Comapny Tax Type is GST Forced please select Tax Type GST'}}
         
         if self.partner_shipping_id and self.tax_type == 'gst':
                  inv_type = str(self.type)
                  delivery_addr = self.partner_shipping_id
                  if self.company_id.state_code != delivery_addr.state_id.code:   
                      domain = [('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','intra')]
                   
                      res = self.env['account.fiscal.position'].search(domain)
                      return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
                  else:
                       inv_type = self.type
                       domain = [('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','inter')]
                   
                       res = self.env['account.fiscal.position'].search(domain)
                       return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
         
         else: 
             today=datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
             tax_type=self.tax_type
             type = self.type
             fspo = self.env['account.fiscal.position'].search(['&',('tax_type','=',tax_type),('type','=',type)])
             warn = False
             res=[]
             for i in fspo:
                   if i.end_date and self.date_invoice and i.end_date > self.date_invoice:
                      res.append(i.id)  
                   elif i.end_date and self.date_invoice and i.end_date < self.date_invoice:
                        warn= {'warning': {
                            'title': _('Warning'),
                            'message':  (_('%s This fiscal position is not valide for upto this date')% i.name)
                             } }
                      
                   else: res.append(i.id)
             if warn:
                 return  warn 
             return {'domain':{'fiscal_position_id':[('id','in',res)]  } }        
                          
    def _prepare_invoice_line_from_po_line(self, line):
        res = super(kts_gst_account_invoice, self)._prepare_invoice_line_from_po_line(line)
        res.update({'hsn_code':line.hsn_code}) 
        return res 

class kts_gst_account_inv_lines(models.Model):
    _inherit = 'account.invoice.line' 
    hsn_code = fields.Char(related='product_id.categ_id.hsn_id.hsn_code',string='HSN Code', store=True)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.invoice_id:
            return
        if not self.invoice_id.fiscal_position_id:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a Fiscal position!'),
                }
            return {'warning': warning}
        
        return super(kts_gst_account_inv_lines, self)._onchange_product_id() 

class kts_gst_stock_picking(models.Model):
    _inherit='stock.picking' 
    partner_state_code = fields.Char(related='partner_id.state_id.code',string='Partner State Code',store=True)
    partner_gstin = fields.Char(related='partner_id.gstin',string='Partner GSTIN',store=True)

class kts_gst_sale_order(models.Model):
    _inherit='sale.order'
    
    @api.model
    def _default_get_tax_type(self):
        if self.env.user.company_id.gst_forced:
            return 'gst'
        else:
            return 'no_tax'
    
    @api.model
    def _default_fiscal_position_id(self):
        if self._context.get('default_fiscal_position_id', False):
            return self.env['account.fiscal.position'].browse(self._context.get('default_fiscal_position_id'))
        inv_type='out_invoice'  
        if self.env.user.company_id.gst_forced:
            domain = ['&',('type', '=', inv_type),('tax_type','=','gst')]
        else:
            domain = [('type', '=', inv_type)]
        res = self.env['account.fiscal.position'].search(domain)
        return {'domain':{'default_fiscal_position_id':[('id','in',res.ids)]} } 
  
    
    tax_type = fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service'),('gst','GST')], string='Tax Type',default=_default_get_tax_type,readonly=True,states={'draft': [('readonly', False)],'sent': [('readonly', False)]})  
     
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
        readonly=True, states={'draft': [('readonly', False)],'sent': [('readonly', False)]},default = _default_fiscal_position_id,)                                
    
    partner_state_code = fields.Char(related='partner_shipping_id.state_id.code',string='State Code',store=True)
    partner_type = fields.Selection(related='partner_id.partner_type',string='Partner Type',store=True)
    partner_gstin = fields.Char(related='partner_id.gstin',string='GSTIN',store=True)
    partner_udi = fields.Char(related='partner_id.uid',string='UIDN',store=True)
    partner_gdi = fields.Char(related='partner_id.gdi',string='GDIN',store=True)
    
    
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                
            })
            return
        
        inv_type='out_invoice'  
   
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        
        delivery_addr=self.env['res.partner'].browse(addr['delivery'])
        
        
        if self.env.user.company_id.gst_forced:
           if self.partner_id.partner_type != 'gst':
               inv_type = 'out_invoice'
               domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','na')]
           
               res = self.env['account.fiscal.position'].search(domain)
               self.update(values)
               return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
           
           elif self.company_id.state_code != delivery_addr.state_id.code:   
              inv_type='out_invoice'  
   
              domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','intra')]
           
              res = self.env['account.fiscal.position'].search(domain)
              self.update(values)
              return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
           else:
               inv_type='out_invoice'  
   
               domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','inter')]
           
               res = self.env['account.fiscal.position'].search(domain)
               self.update(values)
               return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
                
        
        self.update(values)
    
    
    @api.onchange('tax_type','partner_shipping_id')
    def  onchange_tax_type(self):
          
         if self.tax_type:
             if self.company_id.gst_forced:
                if self.tax_type !='gst':
                   return{'value':{'tax_type':'gst'},
                               'warning':{'title':'UserError', 'message':'Comapny Tax Type is GST Forced please select Tax Type GST'}}
         
         if self.partner_shipping_id and self.tax_type == 'gst':
                  inv_type='out_invoice'  
   
                  delivery_addr = self.partner_shipping_id
                  if self.company_id.state_code != delivery_addr.state_id.code:   
                      domain = [('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','intra')]
                   
                      res = self.env['account.fiscal.position'].search(domain)
                      return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
                  else:
                    
                       domain = [('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','inter')]
                   
                       res = self.env['account.fiscal.position'].search(domain)
                       return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
         
         else: 
             tax_type=self.tax_type
             inv_type='out_invoice'  
             warn = False
             fspo = self.env['account.fiscal.position'].search(['&',('tax_type','=',tax_type),('type','=',inv_type)])
             res=[]
             for i in fspo:
                   if i.end_date and self.validity_date and i.end_date > self.validity_date:
                      res.append(i.id)  
                   elif i.end_date and self.validity_date and i.end_date < self.validity_date:
                        warn= {'warning': {
                            'title': _('Warning'),
                            'message':  (_('%s This fiscal position is not valide for upto this date')% i.name)
                             } }
                      
                   else: res.append(i.id)
             if warn:
                 return  warn 
             return {'domain':{'fiscal_position_id':[('id','in',res)]  } }        
    @api.multi
    def _prepare_invoice(self):
        res = super(kts_gst_sale_order, self)._prepare_invoice()
        res.update({
                    'partner_invoice_id':self.partner_invoice_id.id,
                    'partner_shipping_id':self.partner_shipping_id.id,
                    'partner_state_code':self.partner_state_code
                    })    
        return res
    @api.model
    def _prepare_procurement_group(self):
        res = super(kts_gst_sale_order, self)._prepare_procurement_group()
        res.update({'partner_state_code':self.partner_state_code,
                    'partner_gstin':self.partner_gstin})
        return res

class kts_gst_sale_order_line(models.Model):
    _inherit='sale.order.line'
    hsn_code = fields.Char(related='product_id.categ_id.hsn_id.hsn_code')
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.order_id:
            return
        if not self.order_id.fiscal_position_id:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a Fiscal position!'),
                }
            return {'warning': warning}
        
        return  
    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(kts_gst_sale_order_line, self)._prepare_invoice_line(qty)
        res.update({
                    'hsn_code':self.hsn_code,
                    })
        return res
    
class kts_gst_purchase_order(models.Model):
    _inherit='purchase.order'
    
    @api.model
    def _default_get_tax_type(self):
        if self.env.user.company_id.gst_forced:
            return 'gst'
        else:
            return 'no_tax'
    
    @api.model
    def _default_fiscal_position_id(self):
        if self._context.get('default_fiscal_position_id', False):
            return self.env['account.fiscal.position'].browse(self._context.get('default_fiscal_position_id'))
        inv_type='out_invoice'  
        if self.env.user.company_id.gst_forced:
            domain = ['&',('type', '=', inv_type),('tax_type','=','gst')]
        else:
            domain = [('type', '=', inv_type)]
        res = self.env['account.fiscal.position'].search(domain)
        return {'domain':{'default_fiscal_position_id':[('id','in',res.ids)]} } 
  
    
    tax_type = fields.Selection([('no_tax','No Tax'),('cenvat','Cenvat'), ('mvat','MVAT'), ('cst','CST'), 
                ('cenvat_mvat','Cenvat+MVAT'), ('cenvat_cst','Cenvat+CST'),('service','Service'),('gst','GST')], string='Tax Type',default=_default_get_tax_type,readonly=True,states={'draft': [('readonly', False)],'sent': [('readonly', False)]})  
     
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
        readonly=True, states={'draft': [('readonly', False)],'sent': [('readonly', False)]},default = _default_fiscal_position_id,)                                
    partner_invoice_id = fields.Many2one('res.partner',string='Partner Invoice Address',readonly=True, states={'draft': [('readonly', False)],'sent': [('readonly', False)]})
    partner_shipping_id = fields.Many2one('res.partner',string='Partner Shipping Address',readonly=True, states={'draft': [('readonly', False)],'sent': [('readonly', False)]})    
    partner_state_code = fields.Char(related='partner_shipping_id.state_id.code',string='State Code',store=True)
    partner_type = fields.Selection(related='partner_id.partner_type',string='Partner Type',store=True)
    partner_gstin = fields.Char(related='partner_id.gstin',string='GSTIN',store=True)
    partner_udi = fields.Char(related='partner_id.uid',string='UIDN',store=True)
    partner_gdi = fields.Char(related='partner_id.gdi',string='GDIN',store=True)
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                
            })
            return
        
        inv_type='in_invoice'  
   
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        
        delivery_addr=self.env['res.partner'].browse(addr['delivery'])
        
        
        if self.env.user.company_id.gst_forced:
           if self.partner_id.partner_type != 'gst':
               inv_type = 'in_invoice'
               domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','na')]
           
               res = self.env['account.fiscal.position'].search(domain)
               self.update(values)
               return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
           
           elif self.company_id.state_code != delivery_addr.state_id.code:   
              inv_type='in_invoice'  
   
              domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','intra')]
           
              res = self.env['account.fiscal.position'].search(domain)
              self.update(values)
              return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
           else:
               inv_type='in_invoice'  
   
               domain = ['&',('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','inter')]
           
               res = self.env['account.fiscal.position'].search(domain)
               self.update(values)
               return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
                
        
        self.update(values)
    
    
    @api.onchange('tax_type','partner_shipping_id')
    def  onchange_tax_type(self):
          
         if self.tax_type:
             if self.company_id.gst_forced:
                if self.tax_type !='gst':
                   return{'value':{'tax_type':'gst'},
                               'warning':{'title':'UserError', 'message':'Comapny Tax Type is GST Forced please select Tax Type GST'}}
         
         if self.partner_shipping_id and self.tax_type == 'gst':
                  inv_type='in_invoice'  
   
                  delivery_addr = self.partner_shipping_id
                  if self.company_id.state_code != delivery_addr.state_id.code:   
                      domain = [('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','intra')]
                   
                      res = self.env['account.fiscal.position'].search(domain)
                      return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
                  else:
                    
                       domain = [('type', '=', inv_type),('tax_type','=','gst'),('gst_apply','=','inter')]
                   
                       res = self.env['account.fiscal.position'].search(domain)
                       return {'domain':{'fiscal_position_id':[('id','in',res.ids)]} }
         
         else: 
             tax_type=self.tax_type
             inv_type='in_invoice'  
             warn = False
             res=[]
             fspo = self.env['account.fiscal.position'].search(['&',('tax_type','=',tax_type),('type','=',inv_type)])
             for i in fspo:
                   if i.end_date and self.date_order and i.end_date > self.date_order:
                      res.append(i.id)  
                   elif i.end_date and self.date_order and i.end_date < self.date_order:
                        warn= {'warning': {
                            'title': _('Warning'),
                            'message':  (_('%s This fiscal position is not valide for upto this date')% i.name)
                             } }
                      
                   else: res.append(i.id)
             if warn:
                 return  warn 
             return {'domain':{'fiscal_position_id':[('id','in',res)]  } }        
    
    @api.multi
    def action_view_invoice(self):
        result = super(kts_gst_purchase_order, self).action_view_invoice()
        if self.partner_invoice_id:
            result['context']['default_partner_invoice_id'] = self.partner_invoice_id.id
        if self.partner_shipping_id:
            result['context']['default_partner_shipping_id'] = self.partner_shipping_id.id
        if self.partner_state_code:
            result['context']['default_partner_state_code'] = self.partner_state_code
        
        return result
    
    @api.model
    def _prepare_picking(self):
          res =super(kts_gst_purchase_order, self)._prepare_picking()
          res.update({
                    'partner_state_code':self.partner_state_code,
                    'partner_gstin':self.partner_gstin
                    }) 
          return res
    
class kts_gst_purchase_order_line(models.Model):
    _inherit='purchase.order.line'
    hsn_code = fields.Char(related='product_id.categ_id.hsn_id.hsn_code')
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.order_id:
            return
        if not self.order_id.fiscal_position_id:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a Fiscal position!'),
                }
            return {'warning': warning}
        
        return 
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context({
            'lang': self.partner_id.lang,
            'partner_id': self.partner_id.id,
        })
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        fpos = self.order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id),self.product_id)
        else:
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id,self.product_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result

        
    