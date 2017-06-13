# -*- coding: utf-8 -*-
from openerp import api, fields, models

class SmsMessage(models.Model):

    _name = "sms.message"
    _order = "message_date desc"
    
    record_id = fields.Integer(readonly=True, string="Record")
    account_id = fields.Many2one('sms.account', readonly=True, string="SMS Account")
    model_id = fields.Many2one('ir.model', readonly=True, string="Model")
    by_partner_id = fields.Many2one('res.partner', string="By")
    from_mobile = fields.Char(string="From Mobile", readonly=True)
    to_mobile = fields.Char(string="To Mobile", readonly=True)
    sms_content = fields.Text(string="SMS Message", readonly=True)
    record_name = fields.Char(string="Record Name", compute="_compute_record_name")
    status_string = fields.Char(string="Response String", readonly=True)
    status_code = fields.Selection((('RECEIVED','Received'), ('failed', 'Failed to Send'), ('queued', 'Queued'), ('successful', 'Sent'), ('DELIVRD', 'Delivered'), ('EXPIRED','Timed Out'), ('UNDELIV', 'Undelivered')), string='Delivary State', readonly=True)
    sms_gateway_message_id = fields.Char(string="SMS Gateway Message ID", readonly=True)
    direction = fields.Selection((("I","INBOUND"),("O","OUTBOUND")), string="Direction", readonly=True)
    message_date = fields.Datetime(string="Send/Receive Date", readonly=True, help="The date and time the sms is received or sent")
    
    @api.one
    @api.depends('to_mobile', 'model_id', 'record_id')
    def _compute_record_name(self):
        """Get the name of the record that this sms was sent to"""
        if self.model_id.model != False and self.record_id != False:
            my_record_count = self.env[self.model_id.model].search_count([('id','=',self.record_id)])
            if my_record_count > 0:
                my_record = self.env[self.model_id.model].search([('id','=',self.record_id)])
                self.record_name = my_record.name
            else:
                self.record_name = self.to_mobile
                
    def find_owner_model(self, sms_message):
        """Gets the model and record this sms is meant for"""
        #look for a partner with this number
        partner_id = self.env['res.partner'].search([('mobile','=', sms_message.find('From').text)])
    	if len(partner_id) > 0:
    	    return {'record_id': partner_id[0], 'target_model': "res.partner"}
    	else:
    	    return {'record_id': 0, 'target_model': ""}
