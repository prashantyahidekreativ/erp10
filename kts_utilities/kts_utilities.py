from datetime import datetime, timedelta
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class kts_utilities_conf(models.Model):
    _name='kts.utilities.conf'
    name=fields.Char('Name')
    product_id=fields.Many2one('product.template','Product')
    life_time=fields.Integer('Life of product(Months)')
    part_lines=fields.One2many('kts.utilities.line','utilities_id',string='Part Lines')

class kts_utilties_product_part(models.Model):
    _name='kts.utilities.line'
    product_id=fields.Many2one('product.template','Product')
    expiry=fields.Integer('Expiry Duration (Months)')
    intimation_days=fields.Integer('Intimation Days')
    utilities_id=fields.Many2one('kts.utilities.conf','utility Id')
    onetime_flag=fields.Boolean('One time to notify',default=False)

class kts_utility_calendar_event(models.Model):
    _inherit='calendar.event'
    contract_ids=fields.Many2many('kts.contract.customer','calendar_contract_rel','event_id','contract_id',string='contract')
    utility_event_flag=fields.Boolean('Utility Event',default=False)

class kts_contract_customer_utilities(models.Model):
    _inherit='kts.contract.customer'
    utility_flag=fields.Boolean('Utility To Enable',default=False)
    

    @api.multi
    def action_activate(self):
        self.ensure_one()
        ret=super(kts_contract_customer_utilities, self).action_activate()
        utility_obj=False
        if not self.team_id:
            UserError(_('Please select Sale team in contract'))
        saleteam_ids=[]
        for line in self.team_id.member_ids:
            saleteam_ids.append(line.partner_id.id)     
        saleteam_ids.append(self.partner_id.id)
        if self.utility_flag:
            if self.product_id:
                utility_obj=self.env['kts.utilities.conf'].search([('product_id','=',self.product_id.id)])
            if not utility_obj:
                raise UserError(_('Please Configure utility for product'))
            cal_event=self.env['calendar.event']
        
            
            cal_alarm={
                        'name':'2 Days',
                        'type':'email',
                        'interval':'days',
                        'duration':2,  

                          }
            
            cal_event.sudo().create({
                             'name':'Product life is over (%s) having serial No %s of contract %s'%(self.product_id.name,self.lot_ids.name,self.name),
                             'start_date':self.val_duration_date,
                             'stop_date':self.val_duration_date,
                             'allday':True,
                             'alarm_ids':[(0,0,cal_alarm)], 
                             'user_id':self._uid,
                             'partner_ids':[(4,saleteam_ids)],
                             'contract_ids':[(4,[self.id])], 
                             'utility_event_flag':True, 
                             'class':'confidential',
                             'show_as':'free' 
                              })
        
            for line in utility_obj[0].part_lines:
                if line.onetime_flag:
                   date=fields.Datetime.to_string(fields.Datetime.from_string(self.date_activation)+relativedelta(months=line.expiry))
                   
                   cal_alarm={
                            'name':'%s Days'%(line.intimation_days),
                            'type':'email',
                            'interval':'days',
                            'duration':line.intimation_days,  
                             
                              }

                   cal_event.sudo().create({
                             'name':'Product life is over (%s) having main product serial No %s of contract %s'%(line.product_id.name,self.lot_ids.name,self.name),
                             'start_date':date,
                             'stop_date':date,
                             'allday':True,
                             'alarm_ids':[(0,0,cal_alarm)], 
                             'user_id':self._uid,
                             'partner_ids':[(4,saleteam_ids)],
                             'contract_ids':[(4,[self.id])],
                             'utility_event_flag':True,
                             'class':'confidential',
                             'show_as':'free' 
                             
                              })
                else:
                   date=fields.Datetime.to_string(fields.Datetime.from_string(self.date_activation)+relativedelta(months=line.expiry))
                   
                   cal_alarm={
                            'name':'%s Days'%(line.intimation_days),
                            'type':'email',
                            'interval':'days',
                            'duration':line.intimation_days,  
                              }

                   cal_event.sudo().create({
                             'name':'Product life is over (%s) having main product serial No %s of contract %s'%(line.product_id.name,self.lot_ids.name,self.name),
                             'start_date':date,
                             'stop_date':date,
                             'allday':True,
                             'alarm_ids':[(0,0,cal_alarm)], 
                             'user_id':self._uid,
                             'partner_ids':[(4,saleteam_ids)],
                             'recurrency':True,
                             'interval':line.expiry,
                             'rrule_type':'monthly',
                             'month_by':'date',
                             'day':int(fields.Datetime.from_string(date).strftime('%d')),
                             'end_type':'end_date',
                             'final_date':self.val_duration_date, 
                             'contract_ids':[(4,[self.id])], 
                             'utility_event_flag':True, 
                             'class':'confidential',
                             'show_as':'free' 
                             
                              })
      
        return ret
    
        
                 
