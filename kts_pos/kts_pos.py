from odoo import api, fields, models, _
from datetime import datetime
from odoo import SUPERUSER_ID


class kts_pos_product_category(models.Model):
    _inherit='product.category'
    pos_taxes_ids=fields.Many2many('account.tax',string='Pos Taxes',compute='_compute_pos_taxes_ids',
        readonly=True)
    
    @api.one
    def _compute_pos_taxes_ids(self):
    
       vals={}
       tax_add_ids=False
       if self.hsn_id:
           gst_acc_code=self.hsn_id.gst_account_id
           tax_obj=self.env['account.tax']
           
           #self._cr.execute("select id from account_tax where type_tax_use='sale' and gst_account_code_id = %s and gst_type in ('sgst','cgst') and (amount =%s or amount =%s) or price_include='t' ")
           domain=[('type_tax_use','=','sale'),
                               ('gst_account_code_id','=',gst_acc_code.id),
                               ('gst_type','in',['sgst','cgst']),]
           tax_add_ids = tax_obj.search(domain)
       
       if tax_add_ids:
          self.pos_taxes_ids=tax_add_ids
       else:
           self.pos_taxes_ids=False   
class kts_pos_product_template(models.Model):
         _inherit='product.template'
         pos_taxes_ids = fields.Many2many(
                relation="account.tax", string="Pos taxes",
                related='categ_id.pos_taxes_ids')
  
# class kts_pos_product_product(models.Model):
#          _inherit='product.product'
#          pos_taxes_ids = fields.Many2many(
#                 relation="account.tax", string="Pos taxes",
#                 related='categ_id.pos_taxes_ids')

