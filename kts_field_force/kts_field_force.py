from datetime import datetime, timedelta
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import random
import re

class kts_fieldforce_employee(models.Model):
    _name = "kts.fieldforce.employee"
    _rec_name = 'last_location'
    _order = "last_location desc"    
    
    employee_device = fields.Many2one('kts.fieldforce.employee.device', 'Device', readonly=True)
    employee = fields.Many2one(related='employee_device.employee',string='Employee', store=True, readonly=True)
    name = fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    last_location = fields.Char('Last Location', readonly=True)
    write_date = fields.Datetime('Last Seen', readonly=True)              
    location_latitude =  fields.Float('Latitude', digits=(12,6),readonly=True)
    location_longitude = fields.Float('Longitude', digits=(12,6),readonly=True)
    # 'the_point': fields.geo_point('Last Location',nolabel=1,dim=2,srid=4326),
    #the_point = fields.geo_point('Last Location',nolabel=1),
    
    #on_leave = fields.function(_get_leave_status,method=True, string='Employee Leave Status',type='boolean'),                
    previous_locations = fields.One2many('kts.fieldforce.employee.location', 'employee_location_rel', 'Previous Locations', readonly=True)
    create_date = fields.Datetime('Last Seen', readonly=True)                
    device_state = fields.Boolean(related='employee_device.gprs_state',string='GPS Sate', readonly=True, store=True)
    
class kts_fieldforce_employee_location(models.Model):
    _name = 'kts.fieldforce.employee.location'
    _rec_name = 'last_location'
    _order = "last_location desc"    
    
    employee_device = fields.Many2one('kts.fieldforce.employee.device', 'Device', readonly=False)
    employee = fields.Many2one(related='employee_device.employee',string='Employee', store=True, readonly=True)
    name = fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    last_location = fields.Char('Last Location', readonly=True)
    write_date = fields.Datetime('Last Updated', readonly=True)                
    location_latitude = fields.Float('Latitude', digits=(12,6),readonly=True)
    location_longitude = fields.Float('Longitude', digits=(12,6),readonly=True)
    # 'the_point': fields.geo_point('Last Location',nolabel=1,dim=2,srid=4326),
    #the_point = fields.geo_point('Last Location',nolabel=1),
    employee_location_rel = fields.Many2one('kts.fieldforce.employee', 'Employee Track')
    #on_leave = fields.function(_get_leave_status,method=True, string='Employee Leave Status',type='boolean'),                
    create_date = fields.Datetime('Last Seen', readonly=True)                
    device_state = fields.Boolean(related='employee_device.gprs_state', string='GPS Sate', readonly=True, store=True)


class kts_fieldforce_employee_device(models.Model):     
    _name = 'kts.fieldforce.employee.device'
    _rec_name='name'   
    employee = fields.Many2one('hr.employee', 'Employee')
    name = fields.Char(related='employee.name',string='Name', readonly=True, store=True)
    device_id = fields.Char('Device ID', required=True)
    gprs_note = fields.Char('GPS Note', readonly=True)
    gprs_state = fields.Boolean('GPS State', readonly=True)      
    state = fields.Selection([('draft','Draft'),('requested','Requested'),('approved','Approved'),('cancel','Cancel')],string='State',default='draft')
    active = fields.Boolean('IsActive', defualt=True)                 
            
    _sql_constraints = [
        ('name_uniq', 'unique (name)','Device with this name already exists!'),
        ('device_id_uniq', 'unique (device_id)','Device with this device id already exists!'),
        ]     
    
    @api.model             
    def create(self,vals):
        employee=vals.get('employee',False)
        if employee==False:
            employee=self.env['hr.employee'].search([('user_id','=',self._uid)])
            employee=employee[0]
            
        device=self.search([('employee','=',employee)])
        vals.update({'employee':employee})
        
        if len (device)>0:
            device=self.browse(device[0])
            employee=self.env['hr.employee'].browse(employee)
            raise UserError (_("Device \"%s\" is already assigned to \"%s\"!") % (device.device_id,employee.name))

        return super(kts_fieldforce_employee_device, self).create(vals)
        
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
    
    employee= fields.Many2one('hr.employee', 'Employee', required=True)
    name= fields.Char(related='employee.name', string='Name', readonly=True, store=True)
    mobile_phone= fields.Char(related='employee.mobile_phone', string='Mobile No', readonly=True, store=True)
    work_email= fields.Char(related='employee.work_email', string='Email Id', readonly=True, store=True)
    job_id= fields.Many2one(related='employee.job_id',string='Position', store=True, readonly=True)
    parent_id= fields.Many2one(related='employee.parent_id',string='Manager', store=True, readonly=True)
    
    device_id= fields.Many2one('kts.fieldforce.employee.device', 'Device Id',readonly=True)
    device_state= fields.Boolean(related='device_id.active', string='Device Active', readonly=True, store=True)
    
    #on_leave= fields.function(_get_leave_status,method=True, string='Employee Leave Status',type='boolean')
    #current_track_frq= fields.function(_get_current_tracking_frq,method=True, string='Current Tracking Frq.',type='integer')
    #current_state= fields.function(_get_current_state,method=True, string='Tracking Shift',type='char',size=26)
    field_shift_employee_rel= fields.Many2one('kts.fieldforce.employee.tracking.shift', 'Shift Employees')


        