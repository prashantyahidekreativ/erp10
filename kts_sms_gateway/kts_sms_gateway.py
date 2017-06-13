from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import urllib
import requests
from urllib2 import Request, urlopen, URLError
from datetime import datetime, timedelta
class sms_response():
     delivary_state = ""
     response_string = ""
     human_read_error = ""
     mms_url = ""
     message_id = ""

class SmsGatewayGupshup(models.Model):
    _name = "sms.gateway.gupshup"
    _description = "Gupshup SMS Gateway"
    
    api_url = fields.Char(string='API URL')
    def send_message(self,sms_gateway_id, from_number, to_number, message, my_model_name='', my_record_id=0, media=None):
        sms_account = self.env['sms.account'].search([('id','=',sms_gateway_id)])
        username=sms_account.username
        pwd=sms_account.password
        msg=urllib.quote_plus(message.encode('utf8'))
        #msg="medxfinder+verification+code+-+"+str(345678)
        #call="http://enterprise.smsgupshup.com/GatewayAPI/rest?method=sendMessage&send_to=" +to_number+'&msg='+msg+'&mask=ERP'+'&userid='+str(username)+'&password='+str(pwd)+"&msg_type=TEXT"+"&auth_scheme=PLAIN"
        #request = Request(call)
        request = Request("http://www.smscountry.com/smscwebservice_bulk.aspx?"+'&User='+str(username)+'&passwd='+str(pwd)+'&mobilenumber='+to_number+'&message='+msg+'&sid=OSHINP'+'&mtype=N&DR=Y')
        
        try:
           response = urlopen(request)
           response_string = response.read()
        except URLError, e:
               print 'No kittez. Got an error code:', e
        #response_string = requests.get("http://enterprise.smsgupshup.com/GatewayAPI/rest?method=sendMessage&send_to=" +to_number+'&msg='+msg+'&mask=ERP'+'&userid='+str(username)+'&password='+str(pwd)+"&msg_type=TEXT"+"&auth_scheme=PLAIN" )
        if response_string:
            delivary_state='successful'
            sms_gateway_message_id=1  
            human_read_error=""
        my_sms_response = sms_response()
        my_sms_response.delivary_state = delivary_state
        my_sms_response.response_string = response_string 
        my_sms_response.human_read_error = human_read_error
        my_sms_response.message_id = sms_gateway_message_id
        
        return my_sms_response    
        
class SmsAccountGupshup(models.Model):
      _inherit = "sms.account"
      username=fields.Char('User Name')
      password=fields.Char('Password')
      mask=fields.Char('Mask')

class kts_msg_template(models.Model):
    _name='kts.msg.template'
    
    @api.model
    def _referencable_models(self):
        models=self.env['res.request.link'].search([])
        return [(x.object, x.name) for x in models]
    
    def _get_state(self):
        state=[]
        state.append(('new', 'Problem Logged'),)
        state.append(('assigned', 'Problem Assigned'),)
        state.append(('done', 'Problem Done'),)    
        state.append(('sale','Sale Order'),)
        state.append(('open','Invoice open'),)
        state.append(('post','Payment Post'),)
        state.append(('done','Delivery or receipt'),)
        
        return state
    
    name=fields.Char('Name')
    msg=fields.Text('Message')
    model_id=fields.Selection(_referencable_models,string='Reference Document')
    state=fields.Selection(_get_state,string='State')
    partner=fields.Selection([('cust','Customer'),('sup','Supplier'),('credit','Credit Note'),('debit','Debit Note')],string='Partner')
    payment_mode = fields.Selection([('cheque','Cheque'),('cash','Cash'),('NEFT','NEFT')],string='Payment Mode')

class kts_sale_order_sms(models.Model):
    _inherit='sale.order'
    sms_send=fields.Boolean('SMS Enabled',default=False)
    
    @api.multi
    def action_confirm(self):
        res=super(kts_sale_order_sms, self).action_confirm()
        if self.sms_send:
           
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           msg_template=self.env['kts.msg.template'].search([('model_id','=','sale.order'),('state','=','sale')])
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
           msg_template=msg_template.msg %(self.name,self.partner_id.name,self.amount_total)    
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg_template, 'sale.order', self.id,)
           my_model = self.env['ir.model'].search([('model','=','sale.order')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        
        return res          
class kts_account_invoice_sms(models.Model):
    _inherit='account.invoice'
    sms_send=fields.Boolean('SMS Enabled',default=False)
    
    @api.multi
    def invoice_validate(self):
        res=super(kts_account_invoice_sms, self).invoice_validate()
        
        if self.sms_send:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           if self.type=='out_invoice':
              msg_template=self.env['kts.msg.template'].search([('model_id','=','account.invoice'),('state','=','open'),('partner','=','cust')])
           elif self.type=='in_invoice':
              msg_template=self.env['kts.msg.template'].search([('model_id','=','account.invoice'),('state','=','open'),('partner','=','sup')])
           elif self.type=='out_refund':
              msg_template=self.env['kts.msg.template'].search([('model_id','=','account.invoice'),('state','=','open'),('partner','=','credit')])
           elif self.type=='in_refund':
              msg_template=self.env['kts.msg.template'].search([('model_id','=','account.invoice'),('state','=','open'),('partner','=','debit')])
           
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
           if self.type=='out_invoice':
               date=datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%y')
               msg_template=msg_template.msg %(self.partner_id.name,self.number,self.amount_total,date)    
           elif self.type=='in_invoice':
               date=datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%y')
               msg_template=msg_template.msg %(self.number,self.partner_id.name,self.amount_total)
           else:
               date=datetime.strptime(self.date_invoice, '%Y-%m-%d').strftime('%d/%m/%y')
               msg_template=msg_template.msg %(self.number, date, self.partner_id.name,self.amount_total)
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg_template, 'account.invoice', self.id,)
           my_model = self.env['ir.model'].search([('model','=','account.invoice')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        
        return res   
class kts_receipt_payment(models.Model):
    _inherit='account.payment'
    sms_send=fields.Boolean('SMS Enabled',default=False)
    
    @api.multi
    def post(self):
        res=super(kts_receipt_payment, self).post()
        if self.sms_send:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           if self.partner_type == 'customer':
              if self.type == 'Cash':
                  msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','cust'),('payment_mode','=','cash'),])
              elif self.type == 'NEFT':
                  msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','cust'),('payment_mode','=','NEFT'),])
              elif self.type == 'Cheque':
                  msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','cust'),('payment_mode','=','cheque'),])
              else:
                  msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','cust'),('payment_mode','=',False),])
           elif self.partner_type == 'supplier':
                  if self.type == 'Cash':
                     msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','sup'),('payment_mode','=','cash'),])
                  elif self.type == 'NEFT':
                      msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','sup'),('payment_mode','=','NEFT'),])
                  elif self.type == 'Cheque':
                      msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','sup'),('payment_mode','=','cheque'),])
                  else:
                      msg_template=self.env['kts.msg.template'].search([('model_id','=','account.payment'),('state','=','post'),('partner','=','sup'),('payment_mode','=',False),])   
           
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
           
           if self.type=='Cheque':
              msg_template=msg_template.msg %(self.amount, self.journal_id.name, self.cheque_no, self.partner_id.name)
           elif self.type=='NEFT':
               msg_template=msg_template.msg %(self.amount, self.journal_id.name, self.communication, self.partner_id.name)
           elif self.type =='Cash':
               msg_template=msg_template.msg %(self.amount,self.partner_id.name)
           else:
               msg_template=msg_template.msg %(self.amount,self.journal_id.name,self.partner_id.name)
           
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg_template, 'account.payment', self.id,)
           my_model = self.env['ir.model'].search([('model','=','account.payment')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        return res  
    
class kts_stock_picking_sms(models.Model):
    _inherit='stock.picking'
    sms_send=fields.Boolean('SMS Enabled',default=False)
    
    @api.multi
    def do_new_transfer(self):
        res=super(kts_stock_picking_sms, self).do_new_transfer()  
        if self.sms_send and self.picking_type_id.code in ['incoming','outgoing']:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           msg_template=self.env['kts.msg.template'].search([('model_id','=','stock.picking'),('state','=','done')])
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
               
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg_template.msg.encode('utf-8'), 'stock.picking', self.id,)
           my_model = self.env['ir.model'].search([('model','=','stock.picking')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        
        return res  

class kts_service_management_sms(models.Model):
    _inherit='kts.service.management'
    sms_send = fields.Boolean('SMS Send To Customer',default=False) 
    
    @api.multi
    def action_assign_problem(self):
        res=super(kts_service_management_sms, self).action_assign_problem()
        if self.sms_send:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           msg_template=self.env['kts.msg.template'].search([('model_id','=','kts.service.management'),('state','=','assigned')])
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
               
           msg_template = msg_template.msg %(self.partner_id.name, self.assigned_to.name, self.internal_closure_code) 
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg_template.encode('utf-8'), 'kts.service.management', self.id,)
           my_model = self.env['ir.model'].search([('model','=','kts.service.management')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        return res
    @api.multi
    def action_log_problem(self):
        res=super(kts_service_management_sms, self).action_log_problem()
        
        if self.sms_send:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           msg_template=self.env['kts.msg.template'].search([('model_id','=','kts.service.management'),('state','=','new')])
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
               
           msg = msg_template.msg %(self.partner_id.name, self.name) 
           
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg.encode('utf-8'), 'kts.service.management', self.id,)
           my_model = self.env['ir.model'].search([('model','=','kts.service.management')])
        
                #for single smses we only record succesful sms, failed ones reopen the form with the error message
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass 
        
        return res
    
    @api.multi
    def action_done_problem(self):
        res=super(kts_service_management_sms, self).action_done_problem()
        if self.sms_send:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           msg_template=self.env['kts.msg.template'].search([('model_id','=','kts.service.management'),('state','=','done')])
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template:
               raise UserError(_('Please provide msg Template'))
           if not self.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
           
           msg_template = msg_template.msg %(self.partner_id.name, self.name) 
               
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.partner_id.mobile, msg_template.encode('utf-8'), 'kts.service.management', self.id,)
           my_model = self.env['ir.model'].search([('model','=','kts.service.management')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        
        return res
    
    
class res_partner_sms(models.Model):               
    _inherit='res.partner'
    sms_send = fields.Boolean('Bulk SMS Send To Customer',default=False) 

class kts_bulk_sms(models.Model):
    _name='kts.bulk.sms'
    _inherit = ['mail.thread']
    name=fields.Char('Name')
    
    @api.multi
    def action_send_sms(self):
        self.ensure_one()
        move_lines_partner=self.env['res.partner'].search([('customer','=',True),('sms_send','=',True)])
        for line in move_lines_partner:
            if line.credit != 0.00 and not line.parent_id.id: 
               partner_id=line    
               account_id = line.property_account_receivable_id    
               if line.credit>0.00:
                   form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
                   msg_template=self.env['kts.msg.template'].search([('model_id','=','kts.bulk.sms')])
                   
                   if not form_mob_no:
                        raise UserError(_('Please configure Sender Mobile No'))
                   if not msg_template:
                       raise UserError(_('Please provide msg Template'))
                   
                   if not line.mobile:
                       raise UserError(_('Please give Customer Mobile No'))
                   msg_template=msg_template.msg %(line.credit,fields.Datetime.now())
                   my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, line.mobile, msg_template, 'kts.bulk.sms', self.id,)
                   my_model = self.env['ir.model'].search([('model','=','kts.service.management')])
                   sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': line.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                        
                   try:
                        discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                        self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
                   except:
                        #Message post only works if CRM module is installed
                        pass              
        return True
        
class kts_service_visit_details_sms(models.Model):
    _inherit='kts.visit.details'
    
    @api.multi
    def action_assign(self):
        res=super(kts_service_visit_details_sms, self).action_assign()
        if self.service_management_id.sms_send:
           form_mob_no=self.env['sms.number'].search([('mobile_number','=','8888348966')])
           msg_template=self.env['kts.msg.template'].search([('model_id','=','kts.visit.details'),('state','=','assigned')])
           msg_template1=self.env['kts.msg.template'].search([('model_id','=','kts.visit.details'),('state','=','done')])
           
           if not form_mob_no:
                raise UserError(_('Please configure Sender Mobile No'))
           if not msg_template and msg_template1:
               raise UserError(_('Please provide msg Template'))
           if not self.service_management_id.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
           if not self.service_management_id.partner_id.mobile:
               raise UserError(_('Please give Customer Mobile No'))
           if not self.emp_id.mobile_phone:
               raise UserError(_('Please give Employee Work Mobile No'))
           
           area = self.service_management_id.partner_id.area_id.name if self.service_management_id.partner_id.area_id else 'NA'
           msg_template = msg_template.msg %(self.service_management_id.partner_id.name, self.service_management_id.name,self.emp_id.name, self.emp_id.mobile_phone) 
           msg_template1 = msg_template1.msg %(self.emp_id.name, self.service_management_id.partner_id.name, area, self.service_management_id.partner_id.mobile, self.service_management_id.name, self.note) 
               
           my_sms=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.service_management_id.partner_id.mobile, msg_template.encode('utf-8'), 'kts.service.management', self.id,)
           my_sms1=form_mob_no.account_id.send_message(form_mob_no.mobile_number, self.emp_id.mobile_phone, msg_template1.encode('utf-8'), 'kts.service.management', self.id,)
           
           my_model = self.env['ir.model'].search([('model','=','kts.service.management')])
           sms_message = self.env['sms.message'].create({'record_id': self.id,'model_id':my_model[0].id,'account_id':form_mob_no.account_id.id,'from_mobile':form_mob_no.mobile_number,'to_mobile': self.service_management_id.partner_id.mobile,'sms_content':msg_template,'status_string':my_sms.response_string, 'direction':'O','message_date':datetime.utcnow(), 'status_code':my_sms.delivary_state, 'sms_gateway_message_id':my_sms.message_id, 'by_partner_id':self.env.user.partner_id.id})
                
           try:
                discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
                self.env[self.model].search([('id','=', self.id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=discussion_subtype.id)
           except:
                #Message post only works if CRM module is installed
                pass
        
        return res
                

    