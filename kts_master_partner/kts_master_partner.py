from odoo import fields,models,api,_

class kts_master_partner(models.Model):
    _inherit='res.partner'
    pan_no=fields.Char('PAN NO')
    ecc_no=fields.Char('ECC NO')
    service_tax_no=fields.Char('Service Tax No')
    vat_tin_no=fields.Char('VAT TIN NO')
    cst_tin_no=fields.Char('CST TIN NO')
    ssi_no=fields.Char('SSI NO')
    excise_reg_no=fields.Char('Excise Reg. No')
    
