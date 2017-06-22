from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class kts_gst_partner(models.Model):
    _inherit='res.partner'
    gstin = fields.Char('GSTIN')
    gstin_file = fields.Binary('GSTIN File')
    uid = fields.Char('UID')
    gdi = fields.Char('GDI')

class kts_gst_res_company(models.Model):
    _inherit='res.company'
    gstin = fields.Char('GSTIN')
    gstin_file = fields.Binary('GSTIN File')
    state_code = fields.Char('State Code')
    composition_flag = fields.Boolean('Composition', default=False)
    manufacturer_flag = fields.Boolean('Is Manufacturer', default=False)    
    
class kts_gst_account(models.Model):
    _name='kts.gst.account'
    name = fields.Char('Name')
    cgst = fields.Float('CGST Rate')
    igst = fields.Float('IGST Rate')
    sgst = fields.Float('SGST Rate')

class kts_hsn_master(models.Model):
    _name='kts.hsn.master'
    name = fields.Char('Name')
    hsn_code = fields.Char('HSN Code')
    gst_account_id = fields.Many2one('kts.gst.account')   

class kts_gst_product_product(models.Model):
    _inherit='product.template'
    hsn_id = fields.Many2one('kts.hsn.master', 'HSN Code')

class kts_gst_product_category(models.Model):
    _inherit='product.category'
    hsn_id = fields.Many2one('kts.hsn.master', 'HSN Code')
        
    
class kts_gst_master(models.Model):
    _name='kts.gst.master'
    
    name = fields.Char('Name')
    igst_in_acc_id = fields.Many2one('account.account','IGST Input Account')
    igst_out_acc_id = fields.Many2one('account.account','IGST output Account')
    cgst_in_acc_id = fields.Many2one('account.account','CGST Input Account')
    cgst_out_acc_id = fields.Many2one('account.account','CGST output Account')
    sgst_in_acc_id = fields.Many2one('account.account','SGST Input Account')
    sgst_out_acc_id = fields.Many2one('account.account','SGST output Account')
    gst_adv_in_acc_id = fields.Many2one('account.account','GST Advance Input Account')
    gst_adv_out_acc_id = fields.Many2one('account.account','GST Advance output Account')
    gst_paid_in_acc_id = fields.Many2one('account.account','GST Paid Input Account')
    gst_paid_out_acc_id = fields.Many2one('account.account','GST Paid output Account')

class kts_gst_account_tax(models.Model):
    _inherit='account.tax'
    tax_type =  fields.Selection(selection_add=[('gst', 'GST')])
    igst_flag = fields.Boolean('IGST',default=False)
    cgst_flag = fields.Boolean('CGST',default=False)
    sgst_flag = fields.Boolean('SGST',default=False)
                         
