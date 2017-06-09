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

def get_time_now_obj(context):
    tz=context.get('tz',False) if context else 'Asia/Kolkata'
    return datetime.now(pytz.timezone(tz or 'Asia/Kolkata'))

class kts_fieldforce_employee(models.Model):
    _name = "kts.fieldforce.employee"
    _rec_name = 'last_location'
    _order = "last_location desc"    
    
    
    employee_device = fields.Many2one('kts.fieldforce.employee.device', 'Device', readonly=True)
    employee = fields.Many2one(related='employee_device.employee',string='Employee', store=True, readonly=True)
    name = fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    last_location = fields.Char('Last Location', readonly=True)
    write_date = fields.Datetime('Last Seen', readonly=True)              
    location_latitude =  fields.Float('Latitude', digits=(12,6))
    location_longitude = fields.Float('Longitude', digits=(12,6))
    on_leave = fields.Boolean(compute='_get_leave_status',string='Employee Leave Status')                
    previous_locations = fields.One2many('kts.fieldforce.employee.location', 'employee_location_rel', 'Previous Locations')
    create_date = fields.Datetime('Last Seen', readonly=True)                
    device_state = fields.Boolean(related='employee_device.gprs_state',string='GPS Sate', readonly=True, store=True)
    filter_date = fields.Date('Filter Date',default=fields.Datetime.now())
    live_track = fields.Boolean('Live Track', default=False)
    
    @api.one
    def get_address(self,addr):
            url = 'http://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s&sensor=true' %(addr['location_latitude'],addr['location_longitude'])
            try:
                result = json.load(urllib.urlopen(url))
                print result
            except Exception, e:
                raise UserError(_('Cannot contact geolocation servers. Please make sure that your internet connection is up and running (%s).') % e)
            if result['status'] != 'OK':
                return False
        
            try:
                return result['results'][0]['formatted_address']
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
            vals.update({'last_location':addr[0].encode('UTF8')})      
            loc_id=self.env['kts.fieldforce.employee.location'].create({'location_latitude':lat,'location_longitude':lon,'employee_device':device_id.id,'employee_location_rel':self.id,'last_location':addr[0].encode('UTF8')})        
        return super(kts_fieldforce_employee, self).create(vals)    
    
    
    @api.multi
    def write(self,vals):
        if vals.get('location_latitude'):
            lat = vals.get('location_latitude')
        if vals.get('location_longitude'):
            lon=vals.get('location_longitude')
        if vals.get('location_latitude') and vals.get('location_longitude'):
            addr = self.get_address({'location_latitude':lat,'location_longitude':lon})
            vals.update({'last_location':addr[0].encode('UTF8')})      
            loc_id=self.env['kts.fieldforce.employee.location'].create({'location_latitude':lat,'location_longitude':lon,'employee_device':self.employee_device.id,'employee_location_rel':self.id,'last_location':addr[0].encode('UTF8')})        
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
        self.create({'employee':emp_id.id,'device_id':device_id,'user_id':user_id})
        return True        



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
    
        