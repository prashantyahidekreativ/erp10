from odoo import api, fields, models, _

class kts_res_bank(models.Model):
    _inherit='res.bank'
    branch=fields.Char('Branch Name')
    mirc_code=fields.Char('MICR code')  
    ifsc_code=fields.Char('IFSC code')
    swift_code=fields.Char('Swift code')
    city_id=fields.Many2one('kts.city.master',string='City')
    

class kts_bank_acc_type(models.Model):
    _name='kts.bank.acc.type'
    name=fields.Char('Name', required=True)
    code=fields.Char('Code')    

class kts_res_partner_bank(models.Model):
    _inherit='res.partner.bank'
    acc_type_id=fields.Many2one('kts.bank.acc.type','Account Type')    