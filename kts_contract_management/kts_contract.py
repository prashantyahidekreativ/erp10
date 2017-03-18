from odoo import models, fields, api, _
from lxml import etree
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class Kts_contract(models.Model):
    _name = 'kts.contract'
    _order = 'id desc' 
    
    name = fields.Char('Name', required=True)
    type = fields.Selection([('warranty','Warranty'),('amc','AMC')],'Type')
    val_duration = fields.Integer('Validity Duration(Months)', default=0)
    val_duration_date = fields.Date('Validity Date')
    no_proac_visit = fields.Integer('Proactive Visit', help='Give Number of proactive visit',default=0)
    no_ins_visit = fields.Boolean('Installation Visit', help='Give Number of Installation visit',default=False)
    due_days = fields.Integer('Due days(Installation)')   
    no_free_visit = fields.Integer('Free Visit',help='Give Number of free visit',default=0)
    fre_pro_visit = fields.Selection([('yearly','Yearly'),('semiyearly','Semiyearly'),('quat','Quarterly'),('monthly','Monthly')],'Proactive Frequency visit')
    contract_line = fields.One2many('kts.contract.line', 'contract_id','Contract Line' )
    product_contract_line = fields.One2many('kts.product.contract.line','contract_id')
    note=fields.Text('Note')  

class Kts_contract_line(models.Model):
    _name='kts.contract.line'
    product_id = fields.Many2one('product.product','Product')
    no_to_replace = fields.Integer('Number of free replacement')    
    contract_id = fields.Many2one('kts.contract', required=True, index=True,string='Contract Reference')

class Kts_product_master(models.Model):
    _inherit='product.template'
    contract_line_ids = fields.One2many('kts.product.contract.line','product_id',string='Contract Line')
    
    @api.model
    def create(self,vals):
        if vals.get('contract_line_ids'):
           contract_line=vals.get('contract_line_ids') 
           for line in contract_line:
               if line[2]: 
                  if line[2].has_key('val_duration_date'):
                     if fields.Datetime.from_string(str(line[2]['val_duration_date'])) < fields.datetime.now():
                        raise UserError(_('Please Select valid date contract on Product'))
        return super(Kts_product_master, self).create(vals)
    
    @api.multi
    def write(self,vals):
        if vals.get('contract_line_ids'):
           contract_line=vals.get('contract_line_ids') 
           for line in contract_line:
               if line[2]: 
                  if line[2].has_key('val_duration_date'):
                     if fields.Datetime.from_string(str(line[2]['val_duration_date'])) < fields.datetime.now():
                        raise UserError(_('Please Select valid date contract on Product'))
        
        return super(Kts_product_master, self).write(vals)
                    
    
    @api.onchange('contract_line_ids')
    def _onchange_default_contract(self):
        res=False
        for line in self.contract_line_ids:
            if line.default_contract:
                if res:
                    raise  UserError(_('Select 1 default contract only'))
                else:
                    res=True
            if line.val_duration_date < fields.Datetime.now():
               return {'warning':{'title':'UserError', 'message':'Please select valid date contract!'}}
               
class Kts_contract_line(models.Model):
    _name='kts.product.contract.line'    
    name= fields.Char('Description')
    product_id = fields.Many2one('product.template',string='Product Reference', ondelete='cascade', index=True)
    contract_id = fields.Many2one('kts.contract','Contract')
    val_duration_date = fields.Date(related='contract_id.val_duration_date',string='Validity Date')
    default_contract = fields.Boolean('Default')
            

class Kts_sale_order_contract(models.Model):
    _inherit = 'sale.order.line'
    contract_id=fields.Many2one('kts.contract',string='Contract',)
    
    
    @api.onchange('product_id')
    def product_id_change_contract(self):
        vals={}
        if not self.product_id and not self.product_id.contract_line_ids:
            return {'domain': {'contract_id':[]}}
        for line in self.product_id.contract_line_ids:
            if line.default_contract:
                if  fields.Datetime.from_string(line.val_duration_date) < fields.datetime.now():
                     self.update({'contract_id':False})
                     return {'value':{'contract_id':False},'warning':{'title':'UserError', 'message':'Please select valid date contract!'}}
                  
                res = line.contract_id     
                vals['contract_id']=res.id
                self.update(vals)
                return {'value':vals,}  
        
    @api.onchange('contract_id')
    def onchange_contract_master(self):
        if self.contract_id:
            if  fields.Datetime.from_string(self.contract_id.val_duration_date) < fields.datetime.now():
                self.update({'contract_id':False})
                return {'value':{'contract_id':False},'warning':{'title':'UserError', 'message':'Please select valid date contract!'}}
                          

class Kts_contract_so_invoice(models.Model):
    _inherit='sale.order'
    contract_inv_ids = fields.Many2one('kts.contract.customer',string='Contracts',) 
    contract_count = fields.Integer(string='Contract count',readonly=True,default=1)
    
    @api.multi
    def action_view_contract(self):
        contract_inv_ids=self.env['kts.contract.customer'].search([]) 
        action = self.env.ref('kts_contract_management.action_kts_contract_customer') 
        list_view_id = self.env.ref('kts_contract_management.kts_contract_customer_tree')
        form_view_id = self.env.ref('kts_contract_management.kts_contract_customer_form')
        
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type':action.view_type,
            'view_mode':action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        return result
        
class Kts_contract_invoice(models.Model):
     _name='kts.contract.customer'
     _inherit='kts.contract'
                 
     name=fields.Char('Name',required=False,)
     contract_id = fields.Many2one('kts.contract',string='Contract Ref')
     product_id = fields.Many2one('product.product',string='Product')
     partner_id = fields.Many2one('res.partner','Customer')   
     origin = fields.Many2one('sale.order','Source Document')
     date_creation = fields.Datetime('Date of Creation', default=fields.Datetime.now())
     date_activation = fields.Datetime('Date of Activation', default=fields.Datetime.now())
     team_id = fields.Many2one('crm.team', string='Sales Team',)
     serial_no =fields.Char('Serial No')
     lot_ids = fields.Many2one('stock.production.lot',string='Serial No',)
     #service_ids = fields.One2many('kts.service.management','invcontract_id',string='Service Line', index=True)
     state = fields.Selection([
        ('draft', 'new'),
        ('inprocess', 'In process'),
        ('act','Activated'),
        ('cancel', 'Cancelled'),
        
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')    
     _defaults = {
             'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').next_by_code(cr, uid, 'kts.contract.customer') or _('Unknown Pack')
            }               
     
      
     @api.multi
     def action_inprocess(self):
         self.ensure_one()
         self.write({'state':'inprocess'})
     
     @api.multi
     def action_activate(self):
         self.ensure_one()
         if not self.lot_ids and self.type=='warranty':
             raise UserError(_('Please give serial number'))
         if self.date_activation < fields.Datetime.now():
             self.date_activation=fields.Datetime.now()
             date_creation_dt = fields.Datetime.from_string(self.date_activation)
             dt = date_creation_dt + relativedelta(months=self.val_duration)
             self.val_duration_date = fields.Datetime.to_string(dt)
                    
         self.write({'state':'act'})
     
     @api.multi
     def action_cancel(self):
         self.ensure_one()
         self.write({'state':'cancel'})
         
     @api.onchange('date_creation','date_activation','val_duration')
     def onchange_for_validity_duration(self):
          if self.date_creation == self.date_activation:
              date_creation_dt = fields.Datetime.from_string(self.date_creation)
              dt = date_creation_dt + relativedelta(months=self.val_duration)
              self.val_duration_date = fields.Datetime.to_string(dt) 
          else:
              date_activation_dt = fields.Datetime.from_string(self.date_activation)
              dt = date_activation_dt + relativedelta(months=self.val_duration)
              self.val_duration_date = fields.Datetime.to_string(dt)
     
     
     @api.multi
     @api.onchange('origin','state')  
     def onchange_serial_no(self):
         lot_ids=[]
         vals=[]
         if self._context:
             so = self.origin.name  
             SO = self.env['sale.order'].search([('name','=',so)])
             for pick in SO.picking_ids:
                     if pick.state=='done':
                         for line in pick.pack_operation_product_ids:
                              if line.pack_lot_ids:
                                  for lot in line.pack_lot_ids:
                                      lot_ids.append({'lot_ids':lot.lot_id.id})
             for lot_id in lot_ids:
                 vals.append(lot_id['lot_ids'])
             return {'domain':{'lot_ids':[('id','in',vals)]} } 
         else:
             return
    
    
