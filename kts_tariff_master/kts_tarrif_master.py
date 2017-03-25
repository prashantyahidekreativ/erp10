from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class kts_tarrif_master(models.Model):
    _name='kts.tarrif.master'
    name=fields.Char('Name', required=True)
    code=fields.Char('code', required=True)
    description=fields.Text('Description') 
    
class kts_product_tarrif(models.Model):
    _inherit='product.template'
    tarrif_id=fields.Many2one('kts.tarrif.master',string='Tarrif Code')    

class kts_account_invoice_line_tarrif(models.Model):
    _inherit='account.invoice.line'
    
    tarrif_id=fields.Many2one('kts.tarrif.master',string='Tarrif Code')
    
    @api.onchange('product_id')
    def _onchange_product_id_tarrif(self):
        if not self.invoice_id:
            return
        self.update({'tarrif_id':self.product_id.tarrif_id.id})
        
        return {'value':{'tarrif_id':self.product_id.tarrif_id.id} 
                }

class kts_sale_order_tarrif(models.Model):
    _inherit='sale.order.line'
    
    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(kts_sale_order_tarrif, self)._prepare_invoice_line(qty)
        res.update({
                    'tarrif_id':self.product_id.tarrif_id.id,
                    })
        return res
