from datetime import datetime, timedelta, time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import random
import re
import operator
import pytz
import json
import urllib
import urllib2
from itertools import izip


def get_time_now_obj(context):
    tz=context.get('tz',False) if context else 'Asia/Kolkata'
    return datetime.now(pytz.timezone(tz or 'Asia/Kolkata'))

class kts_fieldforce_stock_location(models.Model):
    _inherit='stock.location'
    emp_id = fields.Many2one('hr.employee','Employee')

class kts_fieldforce_employee(models.Model):
    _name = "kts.fieldforce.employee"
    _rec_name = 'name'
    _order = "last_location desc"    
    
    
    employee_device = fields.Many2one('kts.fieldforce.employee.device', 'Device', readonly=True)
    employee = fields.Many2one(related='employee_device.employee',string='Employee', store=True, readonly=True)
    name = fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    last_location = fields.Char('Last Location', readonly=True)
               
    location_latitude =  fields.Float('Latitude', digits=(12,6))
    location_longitude = fields.Float('Longitude', digits=(12,6))
    on_leave = fields.Boolean(compute='_get_leave_status',string='Employee Leave Status')                
    previous_locations = fields.One2many('kts.fieldforce.employee.location', 'employee_location_rel', 'Previous Locations')
    create_date = fields.Datetime('Last Seen', readonly=True)                
    device_state = fields.Boolean(related='employee_device.gprs_state',string='GPS Sate', readonly=True, store=True)
    #filter_date = fields.Date('Filter Date',default=fields.Datetime.now())
    filter_date1 = fields.Date('Filter Date',compute='compute_date',readonly=False) 
    last_update_date=fields.Datetime('Last Seen')
    
    def compute_date(self):
        for record in self:
            record.filter_date1=fields.Datetime.now()
    @api.one
    def get_address(self,addr):
            url = 'http://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s&sensor=true' %(addr['location_latitude'],addr['location_longitude'])
            try:
                result = json.load(urllib2.urlopen(url))
               
            except Exception, e:
                raise UserError(_('Cannot contact geolocation servers. Please make sure that your internet connection is up and running (%s).') % e)
            if result['status'] != 'OK':
                return False
        
            try:
                if result['results'][0]['formatted_address']: 
                   res = result['results'][0]['formatted_address']
                   return res.encode("utf-8")
                else:
                    return ''
            except (KeyError, ValueError):
                return False
    @api.model
    def create(self,vals):
        if vals.get('employee_id'):
           device_id = self.env['kts.fieldforce.employee.device'].search([('employee','=',vals.get('employee_id'))])
           vals.update({'employee_device':device_id.id})
        
        if vals.get('location_latitude'):
            lat = vals.get('location_latitude')
        if vals.get('location_longitude'):
            lon=vals.get('location_longitude')
        if vals.get('location_latitude') and vals.get('location_longitude'):
            addr = self.get_address({'location_latitude':lat,'location_longitude':lon})
            vals.update({'last_location':addr})      
            loc_id=self.env['kts.fieldforce.employee.location'].create({'location_latitude':lat,'location_longitude':lon,'employee_device':device_id.id,'employee_location_rel':self.id,'last_location':addr})        
        vals.update({'last_update_date':fields.Datetime.now(),})
        return super(kts_fieldforce_employee, self).create(vals)    
    
    
    @api.multi
    def write(self,vals):
        if vals.get('location_latitude'):
            lat = vals.get('location_latitude')
        if vals.get('location_longitude'):
            lon=vals.get('location_longitude')
        if vals.get('location_latitude') and vals.get('location_longitude'):
            addr = self.get_address({'location_latitude':lat,'location_longitude':lon})
            vals.update({'last_location':addr})      
            loc_id=self.env['kts.fieldforce.employee.location'].create({'location_latitude':lat,'location_longitude':lon,'employee_device':self.employee_device.id,'employee_location_rel':self.id,'last_location':addr})        
        if vals.get('employee_id'):
            del vals['employee_id'] 
        vals.update({'last_update_date':fields.Datetime.now(),})
        return super(kts_fieldforce_employee, self).write(vals)    
        
    
    
    
    @api.multi
    def _get_leave_status(self):
        self.ensure_one()
        if self.employee:
            if self.employee.current_leave_state == 'validate':
               self.on_leave = True
        else:
            self.on_leave = False    
        

class kts_fieldforce_employee_location(models.Model):
    _name = 'kts.fieldforce.employee.location'
    _rec_name = 'last_location'
    _order = "create_date desc"    
    
    employee_device = fields.Many2one('kts.fieldforce.employee.device', 'Device', readonly=False)
    employee = fields.Many2one(related='employee_device.employee',string='Employee', store=True, readonly=True)
    name = fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    last_location = fields.Char('Last Location', readonly=True)
    write_date = fields.Datetime('Last Updated', readonly=True)                
    location_latitude = fields.Float('Latitude', digits=(12,6),readonly=True)
    location_longitude = fields.Float('Longitude', digits=(12,6),readonly=True)
    employee_location_rel = fields.Many2one('kts.fieldforce.employee', 'Employee Track')
    on_leave = fields.Boolean(compute='_get_leave_status',string='Employee Leave Status')                
    create_date = fields.Datetime('Last Seen', readonly=True)                
    device_state = fields.Boolean(related='employee_device.gprs_state', string='GPS Sate', readonly=True, store=True)
    
    @api.model
    def create(self,vals):
        res=super(kts_fieldforce_employee_location, self).create(vals)
        if res:
            self._cr.commit()
        channel = '["%s","%s"]' %('erp10', 'gps.coords.set')
        msg='{"employee_device":"%s","lat":"%s","long":"%s"}' %(vals.get('employee_device'),vals.get('location_latitude'),vals.get('location_longitude'))
        
        self.env['bus.bus'].sendone(channel, msg)
        return res

    @api.multi
    def _get_leave_status(self):
        for rec in self:
           if rec.employee:
              if rec.employee.current_leave_state == 'validate':
                  rec.on_leave = True
              else:
                  rec.on_leave = False    
   

class kts_fieldforce_employee_device(models.Model):     
    _name = 'kts.fieldforce.employee.device'
    _rec_name='name'   
    
    employee = fields.Many2one('hr.employee', 'Employee')
    name = fields.Char(related='employee.name',string='Name', readonly=True, store=True)
    device_id = fields.Char('Device ID', required=True)
    gprs_note = fields.Char('GPS Note', readonly=True)
    gprs_state = fields.Boolean('GPS State', readonly=True)      
    state = fields.Selection([('draft','Draft'),('requested','Requested'),('approved','Approved'),('cancel','Cancel')],string='State',default='draft')
    active = fields.Boolean('IsActive', default=True)                 
    user_id = fields.Many2one(related='employee.user_id',string='User', store=True)        
    _sql_constraints = [
        ('name_uniq', 'unique (name)','Device with this name already exists!'),
        ('device_id_uniq', 'unique (device_id)','Device with this device id already exists!'),
        ]     
    
    @api.model
    def create_device(self, user_id, device_id):
        user_id = int(user_id)
        emp_id = self.env['hr.employee'].search([('user_id','=',user_id)])       
        self.create({'employee':emp_id.id,'device_id':device_id,'user_id':user_id,'gprs_state':True})
        self.env['stock.location'].create({'name':emp_id.name,'usage':'internal','location_id':11,'emp_id':emp_id.id})
        return True        
    
    @api.model
    def get_gprs_state(self,val):
        uid=self._uid
        emp_id = self.env['hr.employee'].search([('user_id','=',uid)])       
        ret=self.search([('employee','=',emp_id.id)])
        ret.write({'gprs_state':val})
        return {'key':True}

class kts_fieldforce_employee_tracking_shift(models.Model):
    _name = 'kts.fieldforce.employee.tracking.shift'
    _rec_name = 'name'
    
    name = fields.Char('Shift Name',required=True)
    time_start= fields.Float('Start Time(24 Hrs)', digits=(12,6), required=True)
    time_stop =fields.Float('Stop Time(24 Hrs)', digits=(12,6), required=True)
    tracking_frq_office= fields.Integer('Tracking Frequency (Office Hour)', help='Frequency value in Minutes', required=True)
    tracking_frq_non_office= fields.Integer('Tracking Frequency (Non Office Hour)', help='Frequency value in Minutes', required=True)
    task_dist_range= fields.Float('Task Distance Range', digits=(12,2), help='Distance in Meter')
    track_shift_office= fields.Boolean('Allow tracking during office hour',default=True, help="Allow tracking for this shift during office hours.")
    track_shift_non_office= fields.Boolean('Allow tracking during non office hour',default=True, help="Allow tracking for this shift. During non-office hours.")
    shift_line= fields.One2many('kts.fieldforce.employee.tracking.shift.line', 'field_shift_employee_rel', 'Employee Details',ondelete='cascade')
    start_ampm= fields.Selection([('am', 'AM'), ('pm', 'PM')], 'Time',default='am')
    stop_ampm= fields.Selection([('am', 'AM'), ('pm', 'PM')], 'Time',default='pm')
    stop_tracking= fields.Boolean('Stop Tracking', help="Stop Tracking this set of employee.")
    current_date= fields.Datetime(string='Current Time',default=fields.Datetime.now())
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)','This shift is already defined!'),
        ]     
    
class kts_fieldforce_employee_tracking_shift_line(models.Model):
    _name = 'kts.fieldforce.employee.tracking.shift.line'
    _rec_name = 'name'
    
    @api.model
    def get_tracking_frequency(self,employee_id):
        employee=employee_id
        employee_id1=False
        if employee==0:
            employee_id1=self.env['hr.employee'].search([('user_id','=',self._uid)])[0]
        if employee_id1:
            employee_id= employee_id1.id
        query='SELECT field_shift_employee_rel from kts_fieldforce_employee_tracking_shift_line where employee=%s'% str(employee_id)
        self._cr.execute(query)
        lines = self._cr.fetchall()  
        shifts = map(operator.itemgetter(0), lines) if lines else []
        frq={}
        for shift in shifts:
            ret=self._calculate_tracking_frq(shift)
            if frq.get('office_time',False):
                if frq.get('office_time',False)>ret['office_time'] and ret['office_time']>0:
                    frq['office_time']=ret['office_time']
            else:
                frq['office_time']=ret['office_time']
                
            if frq.get('nonoffice_time',False):
                if frq.get('nonoffice_time',False)>ret['nonoffice_time'] and ret['nonoffice_time']>0:
                    frq['nonoffice_time']=ret['nonoffice_time']
            else:
                frq['nonoffice_time']=ret['nonoffice_time']     
                
        if frq.get('office_time',False):
            return  'Office Hour', frq.get('office_time',False)
        else:
            fq = frq['nonoffice_time'] if frq.get('nonoffice_time',False) else 0
            return 'Non Office Hour', fq

    def _calculate_tracking_frq(self,shift_id):
        res={'office_time':0,'nonoffice_time':0}
        shift=self.env['kts.fieldforce.employee.tracking.shift'].browse(shift_id)
        online_frq=shift.tracking_frq_office
        ofline_frq=shift.tracking_frq_non_office
        tracking_state=shift.stop_tracking

        if shift.stop_tracking:
            return res
       
        office_hr=self._is_office_hr(shift)
        if office_hr and shift.track_shift_office:
            res['office_time']=online_frq
        elif not office_hr and shift.track_shift_non_office:
            res['nonoffice_time']=ofline_frq
        return res       
    
    def _is_office_hr(self,shift):
        office_hr=True
        
        start=shift.time_start
        stop=shift.time_stop
        
        start_hr,start_mins = divmod(start, 1)
        start_hr=int(start_hr)
        start_mins=int(round(start_mins,2))
        
        stop_hr,stop_mins = divmod(stop, 1)
        stop_hr=int(stop_hr)
        stop_mins=int(round(stop_mins,2))
                        
        now=get_time_now_obj(self._context)
        
        if start<=stop:
            if  time(start_hr,start_mins) <= now.time() <= time(stop_hr,stop_mins):        
                office_hr=True
            else:
                office_hr=False
        else:
            if  (time(start_hr,start_mins) <= now.time() <= time(23,59)) or (time(0,0) <= now.time() <= time(stop_hr,stop_mins)):        
                office_hr=True
            else:
                office_hr=False
        return office_hr
    
    @api.multi
    def _get_current_tracking_frq(self):
        res = {}
        for record in self:
             state,frq=record.get_tracking_frequency(record.employee.id)            
             record.current_track_frq = frq
             res[record.id]=frq
        return res

    @api.multi
    def _get_current_state(self):
        if not self.ids:
            return {}
        
        res = {}
        for record in self:
             state,frq=record.get_tracking_frequency(record.employee.id)            
             record.current_state = state 
             res[record.id]=state
        return res
    
    
    @api.multi
    def _get_leave_status(self):
        if self.employee:
            if self.employee.current_leave_state == 'validate':
               self.on_leave = True
        else:
            self.on_leave = False    
    employee= fields.Many2one('hr.employee', 'Employee', required=True)
    name= fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    mobile_phone= fields.Char(related='employee.mobile_phone', string='Mobile No', readonly=True, store=True)
    work_email= fields.Char(related='employee.work_email', string='Email Id', readonly=True, store=True)
    job_id= fields.Many2one(related='employee.job_id',string='Position', store=True, readonly=True)
    parent_id= fields.Many2one(related='employee.parent_id',string='Manager', store=True, readonly=True)  
    device_id= fields.Many2one('kts.fieldforce.employee.device', 'Device Id',readonly=True)
    device_state= fields.Boolean(related='device_id.active', string='Device Active', readonly=True, store=True)
    on_leave= fields.Boolean(compute='_get_leave_status',string='Employee Leave Status')
    current_track_frq= fields.Integer(compute='_get_current_tracking_frq',string='Current Tracking Frq.',)
    current_state= fields.Char(compute='_get_current_state', string='Tracking Shift',)
    field_shift_employee_rel= fields.Many2one('kts.fieldforce.employee.tracking.shift', 'Shift Employees')
    
    @api.model
    def create(self,vals):
        device=self.env['kts.fieldforce.employee.device'].search([('employee','=',vals['employee'])])
        vals.update({'device_id':( device.id if device else False)})        
        return super(kts_fieldforce_employee_tracking_shift_line, self).create(vals)
        
    @api.multi
    def write(self, vals):
        if 'employee' in vals:
            device=self.env['kts.fieldforce.employee.device'].search([('employee','=',vals['employee'])])
            vals.update({'device_id':( device.id if device else False)})         
        return super(kts_fieldforce_employee_tracking_shift_line, self).write(vals)  

class kts_fieldforce_visit_details(models.Model):
    _inherit='kts.visit.details'
    
    
    @api.model
    def get_visit_lines(self):
        uid = self._uid
        emp_id = self.env['hr.employee'].search([('user_id','=',uid)])
        assigned_lines=self.search_read([('emp_id','=',emp_id.id),('state','=','assigned')],limit=20,order='id desc')
        accepted_lines = self.search_read([('emp_id','=',emp_id.id),('state','=','accepted')],limit=20,order='id desc')
        in_progress_lines=self.search_read([('emp_id','=',emp_id.id),('state','=','in_progress')],limit=20,order='id desc')
        
        postpone_lines=self.search_read([('emp_id','=',emp_id.id),('state','=','postpone')],limit=20,order='id desc')
        done_lines=self.search_read([('emp_id','=',emp_id.id),('state','=','done')],limit=20,order='id desc')
        cancel_lines=self.search_read([('emp_id','=',emp_id.id),('state','=','done')],limit=20,order='id desc')
        records=assigned_lines+accepted_lines+in_progress_lines+postpone_lines+done_lines+cancel_lines
        length=len(records)
        return {
            'length': length,
            'records': records
        }
    
    @api.multi
    def consume_product(self):
        self.ensure_one()
        location_id = self.env['stock.location'].search([('emp_id','=',self.emp_id.id)])
        
        subquery='Order by aa.location_id, aa.product '
        if location_id.id:
              stock_location=location_id.id
              subquery=' where aa.location_id=%s '%(stock_location)
              subquery+='Order by aa.location_id, aa.product, aa.categ_id '
               
        self.env.cr.execute('select aa.qty, ' 
                            'aa.reserve_qty, ' 
                            'aa.product_id, ' 
                            'aa.location_id, '
                            'aa.uom_id, '
                            'aa.uom, '
                            'aa.location, '
                            'aa.product, '
                            'bb.prod_incoming_qty_done, '
                            'aa.category, '
                            'aa.categ_id '
                            'from '
                            '(select sum(COALESCE(a.qty,0)) as qty, ' 
                            'sum(case when a.reservation_id is NULL then 0 else COALESCE(a.qty,0) end) as reserve_qty, '
                            'a.product_id, ' 
                            'a.location_id, '
                            'd.id as uom_id, '
                            'd.name as uom, '
                            'e.name as location, '
                            'c.name as product, '
                            'f.name as category, '
                            'c.categ_id '
                            'from '
                            'stock_quant a, '
                            'product_product b, ' 
                            'product_template c, '
                            'product_uom d, '
                            'stock_location e, '
                            'product_category f '
                            'where '
                            'a.product_id=b.id and '
                            'b.product_tmpl_id=c.id and '
                            'c.uom_id=d.id and '
                            'a.location_id=e.id and '
                            'e.usage=\'internal\' and '
                            'c.categ_id=f.id '
                            'group by a.product_id, a.location_id, c.categ_id, e.name, d.id, d.name, c.name, f.name) aa '
                            'left outer join '
                            '(select '
                            'a1.product_id, ' 
                            'sum(a1.product_qty * a1.dfactor/a1.efactor) as prod_incoming_qty_done, ' 
                            'a1.uom_id  ' 
                            'from( '
                            'select a.product_id, ' 
                            'a.product_qty, '
                            'd.factor as dfactor, e.factor as efactor, ' 
                            'c.uom_id ' 
                            'from  '
                            'stock_move a, ' 
                            'product_product b, ' 
                            'product_template c, ' 
                            'product_uom d, '
                            'product_uom e, '
                            'stock_picking g, ' 
                            'stock_picking_type h ' 
                            'where '
                            'a.product_id=b.id and ' 
                            'b.product_tmpl_id=c.id and ' 
                            'c.uom_id=d.id and ' 
                            'a.state in (\'assigned\') and ' 
                            'a.product_uom=e.id and ' 
                            'g.id=a.picking_id and ' 
                            'g.picking_type_id=h.id and ' 
                            'h.code=\'incoming\' and g.state=\'assigned\') a1 ' 
                            'group by a1.product_id, a1.uom_id) bb on aa.product_id=bb.product_id '+subquery) 
        
        move_lines=self.env.cr.fetchall()
        i=0
        lines=[]
        for line in move_lines:     
             i+=1
             free_qty=line[0]-line[1]            
             if free_qty > 0:
                lines.append({
                          'id':line[2],
                          'product':line[7],
                          'unit':line[5]
                          })        
        
        return {'products':lines}
    
    @api.multi
    def create_picking_visit(self,vals):
        self.ensure_one()
        if type(vals) != 'list':
            vals=eval(vals)
        location_id = self.env['stock.location'].search([('emp_id','=',self.emp_id.id)])
        service_obj = self.service_management_id
        picking_type=self.env['stock.picking.type'].search([('service_flag','=',True)])
        picking_id = self.env['stock.picking'].create({
                                                       'picking_type_id':picking_type.id,
                                                       'partner_id':service_obj.partner_id.id,
                                                       'service_id':service_obj.id,
                                                       'location_id':location_id.id,
                                                       'location_dest_id':picking_type.default_location_dest_id.id,
                                                       'move_type':'direct'
                                                       })
        for product,qty in izip(vals[0],vals[1]):
             obj = self.env['product.product'].browse(product)
             self.env['stock.move'].create({'product_id':product,
                                            'picking_type_id':picking_type.id,
                                            'product_uom_qty':qty,
                                            'picking_id':picking_id.id, 
                                            'product_uom': obj.uom_id.id,
                                            'location_id':location_id.id,
                                            'location_dest_id':picking_type.default_location_dest_id.id,
                                            'name':'visit picking'
            
                                            })
        return {'key':True}
    
    @api.multi
    def return_product(self):
        self.ensure_one()
        product_ids=self.env['product.product'].search([('sale_ok','=','True'),('type','=','product')])
        lines=[]
        for line in product_ids:
             lines.append({
                          'id':line.id,
                          'product':line.name,
                          'unit':line.uom_id.name
                          })        
        
        return {'products':lines}    
       
    @api.multi
    def create_return_picking_visit(self,vals):
        self.ensure_one()
        if type(vals) != 'list':
           vals=eval(vals)
        location_id = self.env['stock.location'].search([('usage','=','supplier')])
        service_obj = self.service_management_id
        picking_type=self.env['stock.warehouse'].browse(1).in_type_id
        picking_id = self.env['stock.picking'].create({
                                                       'picking_type_id':picking_type.id,
                                                       'partner_id':service_obj.partner_id.id,
                                                       'service_id':service_obj.id,
                                                       'location_id':location_id[0].id,
                                                       'location_dest_id':picking_type.default_location_dest_id.id,
                                                       'move_type':'direct'
                                                       })
        
        for product,qty in izip(vals[0],vals[1]):
             obj = self.env['product.product'].browse(product)
             self.env['stock.move'].create({'product_id':product,
                                            'picking_type_id':picking_type.id,
                                            'product_uom_qty':qty,
                                            'picking_id':picking_id.id, 
                                            'product_uom': obj.uom_id.id,
                                            'location_id':location_id[0].id,
                                            'location_dest_id':picking_type.default_location_dest_id.id,
                                            'name':'visit picking'
            
                                            })

        
        return {'key':True}
        