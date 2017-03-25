from odoo import fields,models,api,_


class kts_city_master(models.Model):
    _name='kts.city.master'
    name=fields.Char('City Name', required=True) 
    state_id=fields.Many2one('res.country.state',string='State',)    
    country_id=fields.Many2one('res.country','Country')
    zip=fields.Char('Zip')
    
class kts_area_master(models.Model):
    _name='kts.area.master'
    name=fields.Char('Area Name', required=True)
    zonecode=fields.Char('ZoneCode')

class kts_res_partner(models.Model):
    _inherit='res.partner'
    city_id=fields.Many2one('kts.city.master',string='City')
    area_id=fields.Many2one('kts.area.master',string='Area')
    
    @api.onchange('city_id')
    def onchange_city(self):
        if self.city_id:
            self.city = self.city_id.name
            self.update({'city':self.city_id.name})
            return{'value':{'city':self.city_id.name}}        