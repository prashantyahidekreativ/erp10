from odoo.exceptions import UserError, AccessError, ValidationError
#from odoo.osv import osv,fields
from odoo import SUPERUSER_ID
import odoo.addons.decimal_precision as dp
from datetime import date
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import copy
from odoo.addons.report_aeroo.barcode import barcode
from collections import defaultdict
import odoo.addons
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import locale
from operator import itemgetter
from odoo import netsvc
import os, sys, traceback
import base64 
import re
from odoo.addons.report_aeroo.report_aeroo import Aeroo_report                  
from odoo.addons.report_aeroo.currency_to_text import currency_to_text
import operator
from itertools import *
import cStringIO
from odoo import addons
from odoo.modules import get_module_resource
LENGTH_UOM_CATEGORY_ID = 4
MM_UOM_ID=51
INCH_UOM_ID=68
from odoo import models,api,fields, _
from pytz import timezone
import sys
reload(sys)
sys.setdefaultencoding('utf8')
#define system folders
CUSTOMERS='Customers'
EXPORT_CUSTOMERS='Customers -Export'
SUPPLIERS='Suppliers'
SALE_QUOTATION ='Sale Quotation'
SALE_ORDER ='Sale Order'
CUSTOMER_INVOICE ='Customer Invoice'
CUSTOMER_PROFORMA_INVOICE ='Proforma Invoice'
QA_CERTIFICATES ='QA Certificates'

PURCHASE_ORDER ='Purchase Order'
PURCHASE_QUOTATION ='Purchase Quotation'
INVOICES ='Invoice'
FINANCIAL_REPORTS ='Financial Reports'
SALES_REPORTS ='Sales Report'
INVOICE_SALES_REPORTS ='Invoice Sales Report'
ORDER_STATUS_REPORT ='Order Status Report'
RECEIPTS ='Receipts'
VOUCHERS ='Vouchers'

CERTIFICATE_HEADERS_IMAGE ='Certificate Header Image'
NABL ='NABL Header'
NONNABL ='NON NABL Header'

SELF_COMPANY_FOLDER_OBJ_ID=1
MANUFACTURING_TITLE_RANGE=8
#

keyFilePath='filePath'

max_no_line_first_page_with_row_ht_0_23_with_footer=18
max_no_line_first_page_with_row_ht_0_23_footer_OA=12
rows_for_tax_indication_with_row_ht_0_23=2
number_char_to_split_total_amount_summary=60
number_char_to_split_product_name=51
max_no_line_first_page_with_row_ht_0_23_footer_Purchase_Request=21
max_no_line_first_page_with_row_ht_0_23_footer_purchase_order=18

global_temp_storage={}

global_temp_storage_for_document=[]

pdf_id=4
odt_id=1





class kts_reports(models.Model):
    _name = "kts.report"
    _description = "Reporting Class"
    name= fields.Char('Name', size=256, select=True)
    date_start= fields.Date('Start Date')
    date_stop= fields.Date('End Date')        
    active= fields.Boolean('Active',default= True)  
    batch_mode= fields.Boolean('Batch Mode',help='Schedule this document to be printed in batch mode.')
    differed_print= fields.Boolean('Deferred Document',help='Print in deferred mode')
    direct_print= fields.Boolean('Direct Print',help='Print and save directly')
    attachment= fields.Boolean('Save Document',help='Print and save to local disc',default=lambda *a: 1,)
                
    create_date= fields.Datetime('Date Created', readonly=True)
    create_uid =  fields.Many2one('res.users', 'Creator', readonly=True)
    write_date= fields.Datetime('Date Modified', readonly=True)
    write_uid=  fields.Many2one('res.users', 'Last Modification User', readonly=True)
    out_format=fields.Many2one('report.mimetypes', 'Print Format',)
    use_user_defined_template= fields.Boolean('Use Custom Template',help='use this option to select your woen template.')
    

def formatLang(value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
    """
        Assuming 'Account' decimal.precision=3:
            formatLang(value) -> digits=2 (default)
            formatLang(value, digits=4) -> digits=4
            formatLang(value, dp='Account') -> digits=3
            formatLang(value, digits=5, dp='Account') -> digits=5
    """
    if isinstance(value, (str, unicode)) and not value:
        return ''

    if date:
        if not str(value) or value==False:
            return ''

        date_format = '%d/%m/%Y'
        parse_format = DEFAULT_SERVER_DATE_FORMAT
        if isinstance(value, basestring):
            # FIXME: the trimming is probably unreliable if format includes day/month names
            #        and those would need to be translated anyway. 
            date = datetime.strptime(value[:get_date_length(parse_format)], parse_format)
        elif isinstance(value, time.struct_time):
            date = datetime(*value[:6])
        else:
            date = datetime(*value.timetuple()[:6])
        return date.strftime(date_format)



def do_print_setup(self,vals,attachment=False,partner_id=False):
    report_name = vals['report_name']
    if report_name==False or not report_name:
        report_name = 'kreativ_doc'
    report_name= re.sub('[^a-zA-Z0-9\n]+', '_', report_name)[:35] 
    attachment_str='' 
    report_xml = self.env['ir.actions.report.xml']  
    report_id = report_xml.search([('model','=', vals['model']),('report_name','=', report_name),('report_type','=', 'aeroo')])
    for i in report_id:
        i.write({'report_name':i.name})
        
    report_template = report_xml.search([('model','=', vals['model']),('name','=', vals['name']),('report_type','=', 'aeroo')])
    
    if not report_template:
        raise UserError('Document print \"%s\" of model \"%s\" is not configured!'%(report_name,vals['model']))                    
    
    template=report_template   
    out_format=template.out_format.id
    if report_template:
        template.write({'tml_source':'file','report_name':report_name,'out_format':out_format})
    else:      
        report_name=vals['name']
        raise UserError('Document print \"%s\" of model \"%s\" is not configured!'%(report_name,vals['model']))                    
        
    if partner_id==False:
        partner_id=1 
    
    data = {'model':vals['model'], 'ids':self.ids, 'id':self.id, 'report_type': 'aeroo'}
    return {
        'type': 'ir.actions.report.xml',
        'report_name': report_name,
        'datas': data,     
        'context':self._context
    }

def writeToMemFile(memFile,value):
    memFile.write(value.encode('utf-8'))
    
def get_date_obj(date):     
    if date==False or date==None:
        return None
    from datetime import datetime
    from datetime import timedelta
    return datetime.strptime(date, '%Y-%m-%d')   
        
def first_day_of_month(d,default=False):
    if d==None or d==False:
        return default   
    date_obj=get_date_obj(d)
    first_day= date(date_obj.year, date_obj.month, 1)
    return first_day.strftime('%Y-%m-%d')
    
def last_day_of_month(d,default=False):
    if d==None or d==False:
        return default   
    import calendar
    date_obj=get_date_obj(d)
    last_day=calendar.monthrange(date_obj.year, date_obj.month)[1]
    return '%s-%s-%s'%(date_obj.year,date_obj.month,last_day)
    
def normalize_values(self,cr,uid,value,from_unit,to_unit):
    product_uom_obj = self.pool.get('product.uom')
    return product_uom_obj._compute_unit_value(cr, uid,from_unit,
                         value,to_unit)    

def check_string_if_value(value):
    value=value.split('/') if value else []
    for val in value:
        try:
            value=float(val)
            return True
        except ValueError:
            continue
    return False
    
def transform_value(value,required_plane,value_plane,taper_rate):
    if required_plane == value_plane:
        return value
    try:
        value=float(value)
    except ValueError:
        return value
    
    transformed_value=value+taper_rate*(required_plane-value_plane)
    value=format_value(transformed_value,5)  
    return value          
        

def get_date(date,days):     
    if date==False or date==None:
        return ''
    from datetime import datetime
    from datetime import timedelta
    date_object = datetime.strptime(date, '%Y-%m-%d')     
    EndDate = date_object + timedelta(days=days)
    return EndDate.strftime("%d/%m/%Y")

def get_unit_name(unit):
    name=''
    if unit:
        name = unit.name.replace('Micrometer',u"\u03BC"+'m')
    return name

def upcase_first_letter(s):
    s=s.lower()
    return s[0].upper() + s[1:]

def get_unicode_for_plus_minus(in_string):
    res=in_string.replace('+/-',' '+u"\u00B1"+' ')   
    res=res.replace('-/+',' '+u"\u00B1"+' ')     
    return res

def format_value(value,precision=5):
    if value==0.0 or value=='' or value==None or value==False:
        return ''
    else:
        format = '%'+'.'+'%d' % precision
        format= format +'f'
        val= format % value
        return val
        
def get_string(value):
    if value ==None or value== False:
        return ' '
    value = round(value,2)
    if value ==0.0:
        return ' '
    else:
        return str(value)
    

def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
    return len((datetime.now()).strftime(date_format))



def format_currency(currency,grouping=True,symbol=False, allow_negativ=False):
    if (not allow_negativ and currency< 0.0) or ( currency <0.009 and currency >= 0.0 ) or (currency==None ) or (currency==''):
        return ''
    return locale.currency(currency, symbol, grouping)     

def format_number(number,remove_trailing_zero=False):
    number = format_currency(number,False,False)
    if remove_trailing_zero: 
        number = number.replace('.00','') 
    return number

def format_float(value): #it return 0.0 instead of ''
    return '{0:g}'.format(value)

def get_chars_from_string(text,nb_char,padding=True):
    if len(text) < nb_char:
        return [text]
    x =  text.split()
    j=0
    t=''
    for i in range (0,nb_char):
        if t:
            t = t+' '
        if j>=len(x):
            break            
        t = t+x[j]
        if len(t) >= nb_char:
            break
        j=j+1
    subs = split_string_into_strings(text,j,'left')
    less=1
    if padding:
        less=3
        
    chars = subs[0]
    if len(chars)<nb_char-less:
        chars =  subs[0]+' '+subs[1][:nb_char-len(subs[0])-less] + '..'
    return chars
    
def split_string_into_substrings(text,nb_char,alignment='left'):
    if len(text) < nb_char:
        return [text]
    x =  text.split()
    j=0
    t=''
    for i in range (0,nb_char):
        if t:
            t = t+' '
        t = t+x[j]
        if len(t) >= nb_char:
            break
        j=j+1
    return split_string_into_strings(text,j,alignment)
    
def split_string_into_strings(text,nb_words,alignment='center'):
    if nb_words==0 or nb_words==False:
        return [text]
    words = text.split()
    subs = []
    n = nb_words
    q=0
    for i in range(0, len(words), n):
        p=" ".join(words[i:i+n])
        if q==0:
            q=len(p)
        if alignment=='center':
            p=p.center(q)
        if alignment=='right':
            p=p.rjust(q)
        if alignment=='left':
            p=p.ljust(q)
        subs.append(p)
    return subs

    

def get_report_types(self):
    report_types = []
    report_types.append(('debtors_trial_balance_with_opening_balance','Debtors Trial Balance with Opening Balance'))
    report_types.append(('debtors_trial_balance','Debtors Trial Balance'))
    report_types.append(('creditors_trial_balance','Creditors Trial Balance'))
    report_types.append(('creditors_trial_balance_with_opening_balance','Creditors Trial Balance with Opening Balance'))
    report_types.append(('bank_book','Bank Book')) 
    report_types.append(('bank_book','Bank Book')) 
    report_types.append(('purchase_register','Purchase Register'))
    report_types.append(('sale_register','Sale Register'))
    report_types.append(('creditors_ledger','Creditors Ledger'))
    report_types.append(('debtors_ledger','Debtors Ledger'))
    report_types.append(('pl_and_balance_sheet_compare','Balance Sheet'))
    report_types.append(('receipt','Receipt'))
    report_types.append(('voucher','Voucher'))
    report_types.append(('inventory_incoming_shipments','Inventory Incoming Shipments'))
    report_types.append(('inventory_incoming_shipments','Inventory Incoming Shipments'))
    report_types.append(('Historical Stock List',' Historical Stock List'))
    
    
    report_types.sort()
    only_qury=[]
    if self._uid==SUPERUSER_ID:
        only_qury.append( ('sale_register_summary_01','Sale Register Summary 01') )
        only_qury.append( ('sale_register_summary_02','Sale Register Summary 02') )
        only_qury.append( ('quotation_rejection_analysis','Quotation Rejection Analysis') )
        only_qury.append(('Historical Stock List',' Historical Stock List'))
        
        def getKey(item): 
            return item[0]
        only_qury=sorted(only_qury, key=getKey)
        report_types.append( ('blank_line',' ') )
        report_types.append( ('only_query','-----------------Only Queries---------------------') )
    
    return report_types + only_qury
            
    


def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.fromtimestamp(t)
def getSelectedItem(self,field,value):
    if value=='' or value==False:
        return ''
    return dict(self.fields_get([field])[field]['selection'])[value]

class kts_report_uitlity(models.Model):
    _name = "kts.report_uitlity"
    _description = "Utility Functions for Report"
    _inherit = "kts.report"
    
    @api.model
    def get_report_types(self):
        return get_report_types(self)


class query_model(models.Model):
    _name="kts.report.query"
    
    query_name=fields.Char("Name of Query")
    query =fields.Text("Query")
    
    

class kts_report_aeroo(models.Model):
    
    _inherit = 'ir.actions.report.xml'
    
    
    update_query = fields.Boolean('Update Query')      
    update_info = fields.Text('Update Info')
    create_date = fields.Datetime('Date Created', readonly=True)
    create_uid =  fields.Many2one('res.users', 'Creator', readonly=True)
    write_date = fields.Datetime('Date Modified', readonly=True)
    write_uid =  fields.Many2one('res.users', 'Last Modification User', readonly=True)        
    
    @api.multi 
    def get_update_query(self):
        import glob, os
        import os,sys,os.path, time
        curr_dir = os.path.dirname(os.path.realpath(__file__))  
        curr_dir= curr_dir+'/reports/'
        
        os.chdir(curr_dir)
        for file in glob.glob("*.txt"):
            f=open(curr_dir+file,'r')
            query=f.read()
            name=file.replace(".txt", "")
            
            res=self.env['kts.report.query'].search([('query_name','=',name)])
            if not res:
                self.env['kts.report.query'].create({'query_name':name,'query':query})
            else:
                res.write({'query':query})
  
   
    @api.multi 
    def to_update_file_name(self):
        self.ensure_one()
        report_ids = [] if self.update_query else self.get_report_keys()
        query_ids = get_report_types(self) if self.update_query else []
        
        message='no report found for update/create. \n\n'
        create_report=[]
        for d in report_ids:
            report_id=self.env['ir.actions.report.xml'].search(
                    [('report_type','=','aeroo'),('name','=',d['name']),('model','=',d['model'])])
            report_rml=''
            report_sxw_content_data = get_module_resource('ktssarg_reports', 'reports') + '/'+ d['report_sxw_content_data'] + '.odt'
            report_content = open(report_sxw_content_data, "r")
            if not report_content:
                report_content.close() 
                continue  
            report_rml=report_sxw_content_data  
            create_report.append( d['report_sxw_content_data'])
            report_sxw_content_data = base64.b64encode(report_content.read())
            report_content.close()
             
            report_name=d['name']
            in_format='oo-odt'
            out_format=pdf_id            
            tml_source='file'
            process_sep=True
            d.update({'report_name':report_name,'report_sxw_content_data':report_sxw_content_data,'in_format':in_format,'out_format':out_format,
                      'tml_source':tml_source,'process_sep':process_sep,'report_rml':report_rml})            
            if report_id:
                report_id.write(d)
            else:
                self.env['ir.actions.report.xml'].create(d)
        r='' 
        for i in create_report:
            r = r+'\n'+i
        if create_report:     
            message = 'Following reports created:\n    %s \n'% (r)
        
        self.get_update_query()
        super(kts_report_aeroo, self).write({'update_info':message})
        return True
    
    @api.multi
    def get_report_keys(self):
        report_keys=[
           {'name':'debtors_trial_balance_with_opening_balance', 'report_sxw_content_data':'debtors_trial_balance_with_opening_balance','model':'kts.account.report','deferred':'off',  },                     
           {'name':'creditors_trial_balance', 'report_sxw_content_data':'creditors_trial_balance', 'model':'kts.account.report', 'deferred':'adaptive', },
           {'name':'debtors_trial_balance', 'report_sxw_content_data':'debtors_trial_balance','model':'kts.account.report', 'deferred':'adaptive', },                     
           {'name':'creditors_trial_balance_with_opening_balance', 'report_sxw_content_data':'creditors_trial_balance_with_opening_balance','model':'kts.account.report', 'deferred':'adaptive', },                     
           {'name':'bank_book', 'report_sxw_content_data':'bank_book','model':'kts.account.report', 'deferred':'adaptive', },                     
           {'name':'purchase_register', 'report_sxw_content_data':'purchase_register','model':'kts.account.report', 'deferred':'adaptive', },                     
           {'name':'sale_register', 'report_sxw_content_data':'sale_register','model':'kts.account.report', 'deferred':'adaptive',},                     
           {'name':'creditors_ledger', 'report_sxw_content_data':'creditors_ledger','model':'kts.account.report', 'deferred':'adaptive', },                     
           {'name':'debtors_ledger', 'report_sxw_content_data':'debtors_ledger','model':'kts.account.report', 'deferred':'adaptive', },                            
           {'name':'pl_and_balance_sheet_compare', 'report_sxw_content_data':'pl_and_balance_sheet_compare','model':'kts.account.report', 'deferred':'adaptive', },                     
           {'name':'Receipt', 'report_sxw_content_data':'receipt','model':'account.payment', 'deferred':'adaptive', },                     
           {'name':'Voucher', 'report_sxw_content_data':'voucher','model':'account.payment', 'deferred':'adaptive', },                     
           {'name':'inventory_incoming_shipments', 'report_sxw_content_data':'inventory_incoming_shipments','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'Delivery Chalan', 'report_sxw_content_data':'delivery_chalan','model':'stock.picking', 'deferred':'adaptive',},                     
           {'name':'Barcode', 'report_sxw_content_data':'barcode','model':'stock.picking', 'deferred':'adaptive',},                     
           
           {'name':'Internal Transfer Receipt', 'report_sxw_content_data':'internal_transfer_chalan','model':'stock.picking', 'deferred':'adaptive',},                     
           {'name':'Total Inward Value', 'report_sxw_content_data':'total_inward_value','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'Total Dispatch Summary', 'report_sxw_content_data':'total_dispatch_summary','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'Product Reorder', 'report_sxw_content_data':'reorder_report','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'GRN Register', 'report_sxw_content_data':'grn_register','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'Inward Receipt', 'report_sxw_content_data':'inward_receipt','model':'stock.picking', 'deferred':'adaptive',},                     
           {'name':'Delivery Register', 'report_sxw_content_data':'delivery_chalan_register','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'Scrap Inward Register', 'report_sxw_content_data':'scrap_inward_register','model':'kts.inventory.reports', 'deferred':'adaptive',},                     
           {'name':'Scrap Inward MRP Register', 'report_sxw_content_data':'scrap_inward_mrp_register','model':'kts.mrp.reports', 'deferred':'adaptive',},                     
           {'name':'Raw Material Consumption Summary', 'report_sxw_content_data':'raw_material_consumation_summary','model':'kts.mrp.reports', 'deferred':'adaptive',},                      
           {'name':'Direct Material Cost Summary', 'report_sxw_content_data':'direct_material_summary','model':'kts.mrp.reports', 'deferred':'adaptive',},                      
           {'name':'Material Reservation Status', 'report_sxw_content_data':'material_reservation_status','model':'kts.inventory.reports', 'deferred':'adaptive',},                       
           {'name':'Manufacturing Material Requirement Summary', 'report_sxw_content_data':'mrp_material_req_summary','model':'kts.mrp.reports', 'deferred':'adaptive',},                         
           {'name':'Total Production Summary', 'report_sxw_content_data':'total_production','model':'kts.mrp.reports', 'deferred':'adaptive',},                        
           {'name':'Stock List', 'report_sxw_content_data':'stock_list','model':'kts.inventory.reports', 'deferred':'adaptive',},                         
           {'name':'Historical Stock List', 'report_sxw_content_data':'historical_stock_list','model':'kts.inventory.reports', 'deferred':'adaptive',},                             
           {'name':'Daily Production', 'report_sxw_content_data':'daily_production','model':'kts.mrp.reports', 'deferred':'adaptive',},                     
           {'name':'Daily Production Vs Plan Achieved', 'report_sxw_content_data':'daily_production_vs_plan_achieved','model':'kts.mrp.reports', 'deferred':'adaptive',},                     
           {'name':'Daily Production Plan', 'report_sxw_content_data':'daily_production_plan','model':'kts.mrp.reports', 'deferred':'adaptive',},                     
           {'name':'WIP Stock Register', 'report_sxw_content_data':'wip_stock_register','model':'kts.mrp.reports', 'deferred':'adaptive',},                     
           {'name':'Purchase Pending Order', 'report_sxw_content_data':'purchase_pending_order','model':'kts.purchase.reports', 'deferred':'adaptive',},                     
           {'name':'Purchase Schedule Order', 'report_sxw_content_data':'purchase_schedule_order','model':'kts.purchase.reports', 'deferred':'adaptive',},                     
           {'name':'Purchase Order Register', 'report_sxw_content_data':'po_register','model':'kts.purchase.reports', 'deferred':'adaptive',},                     
           {'name':'Total Purchase Order Summary', 'report_sxw_content_data':'total_po_summary','model':'kts.purchase.reports', 'deferred':'adaptive',},                     
           {'name':'Total Freight Value', 'report_sxw_content_data':'total_freight_value','model':'kts.purchase.reports', 'deferred':'adaptive',},                     
           {'name':'Sale Order', 'report_sxw_content_data':'sale_order','model':'sale.order', 'deferred':'adaptive',},                     
           {'name':'Quotation Sale Order', 'report_sxw_content_data':'quotation_sale_order','model':'sale.order', 'deferred':'adaptive',},                       
           {'name':'Customer Invoice', 'report_sxw_content_data':'customer_invoice','model':'account.invoice', 'deferred':'adaptive',},                     
           {'name':'Job Card', 'report_sxw_content_data':'job_card','model':'mrp.production', 'deferred':'adaptive',},
           {'name':'Partial Job Card', 'report_sxw_content_data':'partial_job_card','model':'mrp.production', 'deferred':'adaptive',},         
           {'name':'Supplier Invoice', 'report_sxw_content_data':'supplier_invoice','model':'account.invoice', 'deferred':'adaptive',},                     
           {'name':'Credit Note', 'report_sxw_content_data':'credit_note','model':'account.invoice', 'deferred':'adaptive',},                     
           {'name':'Debit Note', 'report_sxw_content_data':'debit_note','model':'account.invoice', 'deferred':'adaptive',},                     
           {'name':'envelope_print', 'report_sxw_content_data':'envelope_print','model':'kts.account.report', 'deferred':'adaptive',},                     
           {'name':'Journal Voucher', 'report_sxw_content_data':'journal_voucher','model':'account.move', 'deferred':'adaptive',},
           {'name':'Purchase Order', 'report_sxw_content_data':'purchase_order','model':'purchase.order', 'deferred':'adaptive',},                     
           {'name':'Request For Quotation', 'report_sxw_content_data':'request_for_quotation','model':'purchase.order', 'deferred':'adaptive',},                          
           {'name':'Total Sale Order Summary', 'report_sxw_content_data':'total_so_summary','model':'kts.sale.reports', 'deferred':'adaptive',},                     
           {'name':'Standard Warranty Report', 'report_sxw_content_data':'standard_warranty_report','model':'kts.sale.reports', 'deferred':'adaptive',},
           {'name':'contract', 'report_sxw_content_data':'contract','model':'kts.contract.report', },
           {'name':'product_end_register', 'report_sxw_content_data':'product_end_register','model':'kts.contract.report', },
           {'name':'amc_end_register', 'report_sxw_content_data':'amc_end_register','model':'kts.contract.report',  },
           {'name':'product_amc_register', 'report_sxw_content_data':'product_amc_register','model':'kts.contract.report', },
           {'name':'AMC Contract', 'report_sxw_content_data':'amc_contract','model':'kts.contract.customer',  },
           {'name':'Service Due Register', 'report_sxw_content_data':'service_due','model':'kts.service.report',  },
           {'name':'Visit Material History Report', 'report_sxw_content_data':'visit_material_history_report','model':'kts.service.report',  },
           {'name':'master_contract_report', 'report_sxw_content_data':'master_contract_report','model':'kts.contract.report', },
           {'name':'contract_report', 'report_sxw_content_data':'contract_report','model':'kts.contract.report', },           
           {'name':'product_contract_status_report', 'report_sxw_content_data':'product_contract_status_report','model':'kts.sale.reports',  },
           {'name':'product_contract_expire_status_report', 'report_sxw_content_data':'product_contract_expire_status_report','model':'kts.sale.reports',  },
           {'name':'Service Visit Report', 'report_sxw_content_data':'service_visit_report','model':'kts.service.report',  },
           {'name':'Material Consumtion Report', 'report_sxw_content_data':'material_consumtion_report','model':'kts.service.report',  },
           {'name':'After Sale Service Status Report', 'report_sxw_content_data':'after_sale_service_status_report','model':'kts.service.report',  },
           {'name':'Sale Price Variance Report', 'report_sxw_content_data':'sale_price_variance','model':'kts.sale.reports', 'deferred':'adaptive',}
         ]
    
        return report_keys 

class kts_report_sale_order(models.Model):
    
    _inherit = "sale.order"
    print_header=fields.Boolean('Print Header',default=True)
    
    @api.multi
    def to_print_quotation_sale_order(self):
        self.ensure_one()
        report_name= 'quotation_sale_order'
        name='Quotation Sale Order'          
             
        return do_print_setup(self, {'name':name, 'model':'sale.order','report_name':report_name},
                False,self.partner_id.id)
      
    @api.multi
    def to_print_sale_order(self):
        self.ensure_one()
        report_name= 'sale_order'
        name='Sale Order'          
             
        return do_print_setup(self, {'name':name, 'model':'sale.order','report_name':report_name},
                False,self.partner_id.id)
    
    def dispatch_policy(self):
        if self.picking_policy=='direct':
            return 'Deliver each product when available'
        else:
            return 'Deliver all products at once'
    def print_packing_charges(self):
        packing_charges=self.packing_charges if ( self.packing_charges_type =='fixed' or self.packing_charges_type =='variable') else 0.0
       
        if self.packing_charges_type =='variable':
            packing_charges=round(self.amount_untaxed * packing_charges/100.0) 
        return packing_charges
    
    def print_freight_charges(self):
        freight_charges=self.freight_charges if ( self.freight_charges_type =='fixed' or self.freight_charges_type =='variable') else 0.0
        if self.freight_charges_type =='variable':
            freight_charges=round(self.amount_untaxed*freight_charges/100.0)   
        return freight_charges    
   
    def bank_details(self):
        if  self.company_id.partner_id.bank_ids:
            bank_ids=self.company_id.partner_id.bank_ids
            bank_name=bank_ids[0].bank_id.name if bank_ids[0].bank_id.name else''
            bank_account_no=bank_ids[0].acc_number if bank_ids[0].acc_number else''
            bank_account_holder=bank_ids[0].partner_id.name if bank_ids[0].partner_id.name else ''
            bank_account_type=bank_ids[0].acc_type_id.name if bank_ids[0].acc_type_id.name else''
            ifsc_code=bank_ids[0].bank_id.ifsc_code if bank_ids[0].bank_id.ifsc_code else''
            micr_code=bank_ids[0].bank_id.mirc_code if bank_ids[0].bank_id.mirc_code else''
            return 'Our Bank Details'+'\n'+'Account No: '+str(bank_account_no)+'\n'+bank_account_holder+'\n'+'Account Type: '+bank_account_type \
                 +'\n'+'IFSC Code: '+str(ifsc_code)+'\n'+'MICR Code: '+str(micr_code)
        else:
            return '' 
    
    def get_move_lines(self):
        lines=[]
        i=0
        for line in self.order_line:
              i+=1
              if self.fiscal_position_id.price_include:
                  subtotal = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
              
              lines.append({
                            'sr_no':i,
                            'product':line.product_id.name,
                            'qty':line.product_uom_qty,
                            'price':line.price_unit,
                            'discount':line.discount,
                            'delivery_days':line.customer_lead,
                            'subtotal':line.price_subtotal if not self.fiscal_position_id.price_include else subtotal
                            })
        return lines
            



class kts_account_report(models.Model):
    _name='kts.account.report'                          
    
    def get_move_lines(self,tax_line=False):
        move_obj=[]
        if self.report_type =='debtors_trial_balance_with_opening_balance': 
            move_obj = self.debtors_trial_balance_with_opening_balance()
        elif self.report_type=='debtors_trial_balance':
            move_obj = self._get_debtors_trial_balance_print_lines()
        
        elif self.report_type=='creditors_trial_balance_with_opening_balance':
            move_obj = self.creditors_trial_balance_with_opening_balance()    
        
        elif self.report_type=='creditors_trial_balance':
             move_obj = self._get_creditors_trial_balance_print_lines()
        elif self.report_type=='bank_book':
             move_obj = self._get_bank_book_print_lines()
        
        elif self.report_type=='purchase_register':
             move_obj = self._get_purchase_register_print_lines(tax_line)
        
        elif self.report_type=='sale_register':
             move_obj = self._get_sale_register_print_lines()
       
        elif self.report_type=='creditors_ledger':
             move_obj = self._get_creditors_ledger_print_lines()
        
        elif self.report_type=='debtors_ledger':
             move_obj = self._get_debtors_ledger_print_lines()
        
        elif self.report_type=='pl_and_balance_sheet_compare':
             move_obj = self._get_pl_and_balance_sheet_print_lines()
        
        elif self.report_type=='envelope_print':
             move_obj = self._get_envelope_print_lines()
       
        return move_obj    
    
    
    def _get_report_type(self):
        report_type=[]
        report_type.append(('creditors_trial_balance_with_opening_balance','Creditors Trial Balance with Opening Balance'))
        report_type.append(('creditors_trial_balance','Creditors Trial Balance'))
        report_type.append(('debtors_trial_balance_with_opening_balance','Debtors Trial Balance with Opening Balance'))
        report_type.append(('debtors_trial_balance','Debtors Trial Balance'))
        report_type.append(('trail_balance','Trail Balance'))
        report_type.append(('bank_book','Bank Book'))
        report_type.append(('purchase_register','Purchase Register'))
        report_type.append(('sale_register','Sale Register'))
        report_type.append(('creditors_ledger','Creditors Ledger'))
        report_type.append(('debtors_ledger','Debtors Ledger'))
        report_type.append(('pl_and_balance_sheet_compare','Balance Sheet'))        
        report_type.append(('envelope_print','Envelope Print'))        
        
        return report_type
   
    name=fields.Char('Name')
    date_start=fields.Date(string='Start Date')
    date_stop=fields.Date(string='End Date')
    report_type=fields.Selection(_get_report_type, string='Report Type')
    account_id = fields.Many2one('account.account','Bank Account', domain=[('user_type_id','=',3)])
    partner_id = fields.Many2one('res.partner','Customer/Supplier')
    address_type=fields.Selection([('default','default'),('contact','Contact'),('invoice','Invoice'),('delivery','Delivery'),('other','Others')],string='Address Type')
    address_id = fields.Many2one('res.partner','Address')
    
    @api.onchange('address_type','partner_id')
    def onchange_address_type(self):
        if self.partner_id and self.report_type =='envelope_print':
            if not self.partner_id:
                raise UserError(_('Please Select Partner to get Address'))
            if self.address_type:
                address_ids=self.env['res.partner'].search([('parent_id','=',self.partner_id.id),('type','=',self.address_type)])
                if self.address_type == 'default':
                    return {'domain':{'address_id':[('id','in',[self.partner_id.id]),]}}
                else:
                     address_ids=self.env['res.partner'].search([('parent_id','=',self.partner_id.id),('type','=',self.address_type)])
                     return {'domain':{'address_id':[('id','in',address_ids.ids)]}}  
    
    @api.onchange('report_type')
    def onchanage_report_type_partner_id(self):
        if self.report_type:
            if self.report_type=='creditors_ledger':
                res=self.env['res.partner'].search([('supplier','=',True),('parent_id','=',False)])
                return {'domain':{'partner_id':[('id','in',res.ids),]}}
            elif self.report_type=='debtors_ledger':
                res=self.env['res.partner'].search([('customer','=',True),('parent_id','=',False)])
                return {'domain':{'partner_id':[('id','in',res.ids),]}}
    
    
    @api.onchange('date_start','date_stop')
    def onchange_start_end_date(self):
        if self.date_start and self.date_stop:
           if self.date_start > self.date_stop:
              self.update({'date_stop':False})
              return {'value':{'date_stop':False},'warning':{'title':'User Error','message':'End Date should be greater than Start Date'}}
            
    @api.multi
    def to_print_account(self):
           self.ensure_one()
           if self.report_type=='debtors_trial_balance_with_opening_balance':
               report_name= 'Debtors Trial Balance with Opening Balance'    
               report_name1='debtors_trial_balance_with_opening_balance'
           elif self.report_type=='debtors_trial_balance':
               report_name= 'Debtors Trial Balance'    
               report_name1='debtors_trial_balance'
           elif self.report_type=='creditors_trial_balance_with_opening_balance':
               report_name= 'Creditors Trial Balance with Opening Balance'    
               report_name1='creditors_trial_balance_with_opening_balance'
           elif self.report_type=='creditors_trial_balance':
               report_name= 'Creditors Trial Balance'    
               report_name1='creditors_trial_balance'
           elif self.report_type=='bank_book':
               report_name= 'Bank Book'    
               report_name1='bank_book'     
           elif self.report_type=='purchase_register':
               report_name= 'Purchase Register'    
               report_name1='purchase_register'
           elif self.report_type=='sale_register':
               report_name= 'Sale Register'    
               report_name1='sale_register'
           elif self.report_type=='creditors_ledger':
               report_name= 'Creditors Ledger'    
               report_name1='creditors_ledger'
           elif self.report_type=='debtors_ledger':
               report_name= 'Debtors Ledger'    
               report_name1='debtors_ledger'
           elif self.report_type=='pl_and_balance_sheet_compare':
               report_name= 'Balance Sheet'    
               report_name1='pl_and_balance_sheet_compare'
           elif self.report_type=='envelope_print':
               report_name= 'envelope_print'    
               report_name1='envelope_print'
           elif self.report_type=='trail_balance':
               report_name= 'Trail Balance'    
               report_name1='trail_balance'   
              
           return do_print_setup(self, {'name':report_name1, 'model':'kts.account.report','report_name':report_name},
                False,False)
        
    @api.multi
    def write(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start =  vals['date_start'] if vals.get('date_start') else self.date_start 
           date_stop = vals['date_stop'] if vals.get('date_stop') else self.date_stop
           if date_stop==False:
               date_stop=''
           if date_start==False:
              date_start='' 
           name = name.title() +' From '+date_start+' To '+date_stop
           vals.update({
                       'name':name,
                       })   
        return super(kts_account_report, self).write(vals)
    
    @api.model
    def create(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start = vals.get('date_start')  
           date_stop = vals.get('date_stop') 
           if date_stop==False:
               date_stop=''
           if date_start==False:
              date_start='' 
           name = name.title() +' From '+date_start+' To '+date_stop
           vals['name']=name
                          
        ret = super(kts_account_report, self).create(vals)
        return ret
   
    def _get_envelope_print_lines(self):
        lines=[]
        if not self.partner_id or not self.address_type or not self.address_id:
            raise UserError(_('Please Select Partner,Address Type, Address to print it'))
        lines.append({
                      'name':self.address_id.name if self.address_id.name else self.partner_id.name,
                      'add': (self.address_id.street if self.address_id.street else '')+('\n'+'A/p- '+self.address_id.area_id.name if self.address_id.area_id else '')+('\n'+'Tal- '+self.address_id.city_id.name if self.address_id.city_id else '')+('\n'+'Dist-'+self.address_id.street2 if self.address_id.street2 else '')+('\n'+self.address_id.state_id.name if self.address_id.state_id else '')+' '+('('+self.address_id.country_id.name + ')' if self.address_id.country_id else '')+('\n'+'Mob.- '+self.address_id.mobile if self.address_id.mobile else ''),
                      'pin':self.address_id.zip
                      })
        return lines      
    def debtors_trial_balance_with_opening_balance(self):
        date_start=self.date_start
        date_stop=self.date_stop
                
        self.env.cr.execute( 'Select  ' \
                    'COALESCE(i.name,\'\') as name,  ' \
                    'COALESCE(i.code,\'\') as code,  ' \
                    'COALESCE(d.debit_open,\'0.0\') as debit_open,  ' \
                    'COALESCE(d.credit_open,\'0.0\') as credit_open, ' \
                    'COALESCE(e.debit_transaction,\'0.0\') as debit_transaction, ' \
                    'COALESCE(e.credit_transaction,\'0.0\') as credit_transaction, ' \
                    'COALESCE(f.debit_close,\'0.0\') as debit_close, ' \
                    'COALESCE(f.credit_close,\'0.0\') as credit_close ' \
                    'from  ' \
                    '(select b.id,replace(b.name,\' Receivable\',\'\') as name,b.code  ' \
                    'from account_account b ' \
                    'where ' \
                    'b.internal_type=\'receivable\' )  as i ' \
                    'left outer join  ' \
                    '(select COALESCE(sum(a.debit),\'0\') as debit_open, COALESCE(sum(a.credit),\'0\') as credit_open, a.account_id as account_id from  ' \
                    'account_move_line a, account_move b where a.move_id=b.id and b.date < %s group by a.account_id) as d  ' \
                    'on i.id=d.account_id ' \
                    'left outer join  ' \
                    '(select COALESCE(sum(a.debit),\'0\') as debit_transaction, COALESCE(sum(a.credit),\'0\') as credit_transaction, a.account_id as account_id from  ' \
                    'account_move_line a, account_move b where a.move_id=b.id and b.date >= %s and b.date <= %s group by a.account_id) as e ' \
                    'on i.id=e.account_id ' \
                    'left outer join  ' \
                    '(select COALESCE(sum(a.debit),\'0\') as debit_close, COALESCE(sum(a.credit),\'0\') as credit_close, a.account_id as account_id from  ' \
                    'account_move_line a, account_move b where a.move_id=b.id group by a.account_id) as f ' \
                    'on i.id=f.account_id ' \
                    'Order by i.code ' , (date_start,date_start,date_stop))
     
        lines = self.env.cr.fetchall()
        debtors_trial_balance_with_opening_balance=[]
        for l in lines:
            ac_code=particulars=''
            debit_open=credit_open=debit_transaction=credit_transaction=debit_close=credit_close=0.0   
                   
            particulars=l[0]
            ac_code=l[1]
            debit_open=l[2]
            credit_open=l[3]
            debit_transaction=l[4]
            credit_transaction=l[5]
            debit_close=l[6]            
            credit_close=l[7]            
            
            m={'ac_code':ac_code,'particulars':particulars,'debit_open':debit_open,'credit_open':credit_open,
               'debit_transaction':debit_transaction,'credit_transaction':credit_transaction,'debit_close':debit_close,'credit_close':credit_close}  
            debtors_trial_balance_with_opening_balance.append(m)   
        return debtors_trial_balance_with_opening_balance
    
    def creditors_trial_balance_with_opening_balance(self):
        date_start=self.date_start
        date_stop=self.date_stop
                
        self.env.cr.execute('Select ' 
                    'COALESCE(i.name, \'\') as name, '      
                    'COALESCE(i.code, \'\') as code, '   
                    'case when (COALESCE(d.debit_open,\'0.0\') - COALESCE(d.credit_open,\'0.0\')) >=0  then ' 
                    '(COALESCE (d.debit_open,\'0.0\') - COALESCE(d.credit_open,\'0.0\')) else 0.0 end as debit_open, '  
                    'case when (COALESCE(d.debit_open,\'0.0\') - COALESCE(d.credit_open,\'0.0\')) >=0  then 0.0 else '  
                    '(COALESCE(d.credit_open,\'0.0\') - COALESCE(d.debit_open,\'0.0\')) end as credit_open, ' 
                    'COALESCE(e.debit_transaction,\'0.0\') as debit_transaction, ' 
                    'COALESCE(e.credit_transaction,\'0.0\') as credit_transaction, ' 
                    'case when (COALESCE(f.debit_close,\'0.0\') - COALESCE(f.credit_close,\'0.0\')) >=0  then ' 
                    '(COALESCE(f.debit_close,\'0.0\') - COALESCE(f.credit_close,\'0.0\')) else 0.0 end as debit_close, '  
                    'case when (COALESCE(f.debit_close,\'0.0\') - COALESCE(f.credit_close,\'0.0\')) >=0  then 0.0 else '  
                    '(COALESCE(f.credit_close,\'0.0\') - COALESCE(f.debit_close,\'0.0\')) end as credit_close ' 
                    'from ' 
                    '( ' 
                    'select b.id,replace(b.name,\' Payable\',\'\') as name,b.code ' 
                    'from account_account b ' 
                    'where ' 
                    'b.internal_type=\'payable\')  as i ' 
                    'left outer join '  
                    '(select COALESCE(sum(a.debit),\'0\') as debit_open, COALESCE(sum(a.credit),\'0\') as credit_open, ' 
                    'a.account_id as account_id from '   
                    'account_move_line a, account_move b where a.move_id=b.id and b.state=\'posted\' and ' 
                    'b.date < %s group by a.account_id) as d '  
                    'on i.id=d.account_id ' 
                    'left outer join ' 
                    '(select COALESCE(sum(a.debit),\'0\') as debit_transaction, COALESCE(sum(a.credit),\'0\') as ' 
                    'credit_transaction, a.account_id as account_id from ' 
                    'account_move_line a, account_move b where a.move_id=b.id and b.state=\'posted\' and '  
                    'b.date >=  %s  and b.date <=  %s group by a.account_id) as e ' 
                    'on i.id=e.account_id ' 
                    'left outer join '  
                    '(select COALESCE(sum(a.debit),\'0\') as debit_close, COALESCE(sum(a.credit),\'0\') as credit_close, '  
                    'a.account_id as account_id from '  
                    'account_move_line a, account_move b where a.move_id=b.id and b.state=\'posted\' and '  
                    'b.date <=  %s group by a.account_id) as f ' 
                    'on i.id=f.account_id ' 
                    'where ' 
                    '( case when (COALESCE(d.debit_open,\'0.0\') - COALESCE(d.credit_open,\'0.0\')) >=0  then '  
                    '(COALESCE(d.debit_open,\'0.0\') - COALESCE(d.credit_open,\'0.0\')) else 0.0 end + case when '  
                    '(COALESCE(d.debit_open,\'0.0\') - COALESCE(d.credit_open,\'0.0\')) >=0  then 0.0 else ' 
                    '(COALESCE(d.credit_open,\'0.0\') - COALESCE(d.debit_open,\'0.0\')) end + '  
                    'COALESCE(e.debit_transaction,\'0.0\') + '  
                    'COALESCE(e.credit_transaction,\'0.0\') + case when (COALESCE(f.debit_close,\'0.0\') - '  
                    'COALESCE(f.credit_close,\'0.0\')) >=0  then (COALESCE(f.debit_close,\'0.0\') - '  
                    'COALESCE(f.credit_close,\'0.0\')) else 0.0 end + case when (COALESCE(f.debit_close,\'0.0\') - '  
                    'COALESCE(f.credit_close,\'0.0\')) >=0  then 0.0 else (COALESCE(f.credit_close,\'0.0\') - '  
                    'COALESCE(f.debit_close,\'0.0\')) end) > 0 ' 
                    'Order by i.code',(date_start,date_start,date_stop,date_stop))
        lines = self.env.cr.fetchall()
        creditors_trial_balance_with_opening_balance=[]
        for l in lines:
            ac_code=particulars=''
            debit_open=credit_open=debit_transaction=credit_transaction=debit_close=credit_close=0.0   
                   
            particulars=l[0]
            ac_code=l[1]
            debit_open=l[2]
            credit_open=l[3]
            debit_transaction=l[4]
            credit_transaction=l[5]
            debit_close=l[6]            
            credit_close=l[7]            
            
            m={'ac_code':ac_code,'particulars':particulars,'debit_open':debit_open,'credit_open':credit_open,
               'debit_transaction':debit_transaction,'credit_transaction':credit_transaction,'debit_close':debit_close,'credit_close':credit_close}  
            creditors_trial_balance_with_opening_balance.append(m)   
        return creditors_trial_balance_with_opening_balance
    
    def _get_creditors_trial_balance_print_lines(self,):
        self.env.cr.execute( 'Select COALESCE(i.name,\'\') as name, COALESCE(i.code,\'\') as code,  COALESCE(d.debit_total,\'0.0\'), COALESCE(d.credit_total,\'0.0\') from (select  ' \
                    'b.id,replace(b.name,\' Pyable\',\'\') as name,b.code  ' \
                    'from account_account b ' \
                    'where ' \
                    'b.internal_type=\'payable\' )  as i ' \
                    'left outer join  ' \
                    '(select COALESCE(sum(a.debit),\'0\') as debit_total, COALESCE(sum(a.credit),\'0\') as credit_total, a.account_id as account_id from  ' \
                    'account_move_line a, account_move b where a.move_id=b.id group by a.account_id) as d  ' \
                    'on i.id=d.account_id ' \
                    'Order by i.code ')

        lines = self.env.cr.fetchall()
        line=1
        i=1
        creditors_trial_balance=[]
        date=particulars=''
        credit=debit=debit_sum=credit_sum=sum_d=sum_c=0.0
        for l in lines:
            date=particulars=''
            credit=debit=0.0            
            particulars=l[0]
            ac_code=l[1]
            debit=l[2]
            credit=l[3]
            debit_sum = debit_sum+debit
            credit_sum = credit_sum+credit
            if line == 47 or line ==46*(1+i):
                sum_d = debit_sum
                sum_c = credit_sum
                m={'ac_code':ac_code,'particulars':'c/f','credit':credit,'debit':debit,'credit_sum':sum_c,'debit_sum':sum_d,'rows':0}   
                creditors_trial_balance.append(m)       
                if len(lines)>line:
                    m={'ac_code':ac_code,'particulars':'b/f','credit':credit,'debit':debit,'credit_sum':sum_c,'debit_sum':sum_d,'rows':1}
                    creditors_trial_balance.append(m)       
                credit=debit=sum_d=sum_c=0.0
                if line >47:
                    i=i+1
            else:
                m={'ac_code':ac_code,'particulars':particulars,'credit':credit,'debit':debit,'credit_sum':sum_c,'debit_sum':sum_d,'rows':0}  
                creditors_trial_balance.append(m)       
            line=line+1 
        return creditors_trial_balance    
    
    def _get_debtors_trial_balance_print_lines(self,):
        self.env.cr.execute( 'Select COALESCE(i.name,\'\') as name, COALESCE(i.code,\'\') as code, COALESCE(d.debit_total,\'0.0\'), COALESCE(d.credit_total,\'0.0\') from (select  ' \
                    'b.id,replace(b.name,\' Receivable\',\'\') as name,b.code  ' \
                    'from account_account b ' \
                    'where ' \
                    'b.internal_type=\'receivable\' )  as i ' \
                    'left outer join  ' \
                    '(select COALESCE(sum(a.debit),\'0\') as debit_total, COALESCE(sum(a.credit),\'0\') as credit_total, a.account_id as account_id from  ' \
                    'account_move_line a, account_move b where a.move_id=b.id group by a.account_id) as d  ' \
                    'on i.id=d.account_id ' \
                    'Order by i.code ')
        
        lines = self.env.cr.fetchall()
        line=1
        i=1
        debtors_trial_balance=[]
        date=particulars=''
        credit=debit=debit_sum=credit_sum=sum_d=sum_c=0.0
        for l in lines:
            date=particulars=''
            credit=debit=0.0            
            particulars=l[0]
            ac_code=l[1]
            debit=l[2]
            credit=l[3]
            debit_sum = debit_sum+debit
            credit_sum = credit_sum+credit
            if line == 47 or line ==46*(1+i):
                sum_d = debit_sum
                sum_c = credit_sum
                m={'ac_code':ac_code,'particulars':'c/f','credit':credit,'debit':debit,'credit_sum':sum_c,'debit_sum':sum_d,'rows':0}   
                debtors_trial_balance.append(m)       
                if len(lines)>line:
                    m={'ac_code':ac_code,'particulars':'b/f','credit':credit,'debit':debit,'credit_sum':sum_c,'debit_sum':sum_d,'rows':1}
                    debtors_trial_balance.append(m)       
                credit=debit=sum_d=sum_c=0.0
                if line >47:
                    i=i+1
            else:
                m={'ac_code':ac_code,'particulars':particulars,'credit':credit,'debit':debit,'credit_sum':sum_c,'debit_sum':sum_d,'rows':0}  
                debtors_trial_balance.append(m)       
            line=line+1   

        return debtors_trial_balance
    
    def _get_particulars(self,move_line):
     
        
        line1=move_line.move_id.line_ids[1]
        if line1.account_id.user_type_id.id==3:
            line1=move_line.move_id.line_ids[0]             
        
        if line1.account_id.user_type_id.id==1:
           partner_journal_item= 'To ' + line1.partner_id.name +' '+ line1.name 
        elif line1.account_id.user_type_id.id==2:
           partner_journal_item= 'By ' + line1.partner_id.name +' '+ line1.name 
        return partner_journal_item
        
    
    def _get_bank_book_print_lines(self,):
        move_obj=[]
        account_id=self.account_id
        date_start=self.date_start
        date_stop=self.date_stop
        account_mov_lines= self.env['account.move.line'].search([('account_id','=',account_id.id)])
        
        debit = sum(line.debit for line in account_mov_lines.search([('date','<=',date_start),('account_id','=',account_id.id)]))
        
        credit = sum(line.credit for line in account_mov_lines.search([('date','<=',date_start),('account_id','=',account_id.id)]))
        receipt=payment=0.0
        if debit - credit > 0:
             receipt=debit-credit
             particular='To Balance B/F'
        else:
             payment=credit-debit
             particular='By Balance B/F'
        move_obj.append({
                        'date':date_start,
                        'document_number':'',
                        'particulars':particular,
                        'ac_code':'',
                        'receipt':receipt or '',                             
                        'payment':payment or '', 
                        })
        
        account_mov_line=account_mov_lines.search([('date','>=',date_start),('date','<=',date_stop),('account_id','=',account_id.id)]).sorted(key=lambda r:r.date, reverse=False)
        date_tmp=''
        tmp_debit=tmp_credit=0.0
        for i, j in map(None, account_mov_line, range(0,len(account_mov_line)+1)):
            if i:
               line1=i.move_id.line_ids[1]
                 
               
               if j==0:
                  date_tmp=i.date
               if date_tmp == i.date:
                  if line1.account_id.user_type_id.id==3:
                      move_obj.append({
                               'date':i.date,
                               'document_number':i.move_id.name,
                               'particulars':self._get_particulars(i),
                               'ac_code':i.move_id.line_ids[0].account_id.code,
                               'receipt':i.debit or '',                             
                               'payment':i.credit or '', 
                                })  
                      tmp_debit=tmp_debit+i.debit
                      tmp_credit=tmp_credit+i.credit
                  else:    
                      move_obj.append({
                               'date':i.date,
                               'document_number':i.move_id.name,
                               'particulars':self._get_particulars(i),
                               'ac_code':i.move_id.line_ids[1].account_id.code,
                               'receipt':i.debit or '',                             
                               'payment':i.credit or '', 
                                })
                  tmp_debit=tmp_debit+i.debit
                  tmp_credit=tmp_credit+i.credit
               else:
                   receipt1=payment1=0.0
                   if (receipt+tmp_debit) - (tmp_credit + payment) > 0:
                      payment1 = (receipt + tmp_debit) - (tmp_credit + payment)
                      particular='By Balance C/F'
                      particular1='To Balance B/F'
                      total= tmp_debit+receipt
                   else:
                      receipt1=(tmp_credit + payment) - (tmp_debit + receipt)
                      particular='To Balance C/F'   
                      particular1='By Balance B/F'
                      total= tmp_credit+ payment
                   move_obj.append({
                               'date':date_tmp,
                               'document_number':'',
                               'particulars':particular,
                               'ac_code':'',
                               'receipt':receipt1 or '',                             
                               'payment':payment1 or '', 
                                })
                
                   move_obj.append({
                               'date':date_tmp,
                               'document_number':'',
                               'particulars':'Total',
                               'ac_code':'',
                               'receipt':total or '',                             
                               'payment':total or '', 
                                })
                   move_obj.append({
                               'date':date_tmp,
                               'document_number':'',
                               'particulars':particular1,
                               'ac_code':'',
                               'receipt':payment1 or '',                             
                               'payment':receipt1 or '', 
                                })
                
                   move_obj.append({
                               'date':i.date,
                               'document_number':i.move_id.name,
                               'particulars':self._get_particulars(i),
                               'ac_code':i.move_id.line_ids[1].account_id.code,
                               'receipt':i.debit or '',                             
                               'payment':i.credit or '', 
                                })
               
                   date_tmp=i.date          
                   tmp_debit=tmp_debit+i.debit
                   tmp_credit=tmp_credit+i.credit
        
        
        receipt1=payment1=0.0
        if (receipt+tmp_debit) - (tmp_credit + payment) > 0:
            payment1 = (receipt + tmp_debit) - (tmp_credit + payment)
            particular='By Balance C/F'
            total= tmp_debit+receipt
        else:
            receipt1=(tmp_credit + payment) - (tmp_debit + receipt)
            particular='To Balance C/F'   
            total= tmp_credit+ payment
                
        move_obj.append({
                        'date':date_tmp,
                        'document_number':'',
                        'particulars':particular,
                        'ac_code':'',
                        'receipt':receipt1 or '',                             
                        'payment':payment1 or '', 
                         })
                
        move_obj.append({
                        'date':date_tmp,
                        'document_number':'',
                        'particulars':'Total',
                        'ac_code':'',
                        'receipt':total or '',                             
                        'payment':total or '', 
                                })
        return move_obj
    
    
    def _get_purchage_split_tax_lines(self):
        print_lines=[]
        date_start=self.date_start
        date_stop=self.date_stop        
        
        
        lines = self.env['particularaccount.invoice'].search([('type','=','in_invoice'),('state','in',['open','paid']),('date_invoice','>=',date_start),('date_invoice','<=',date_stop)]) 
           
        for l in lines:
            invoice=l.number
            invoice_date=l.date_invoice
            bill_no=l.move_id.name
            customer=l.partner_id.name
            for tax in l.tax_line_ids:
                tax_type=tax.tax_type
                base_amount=tax.base_amount   
                tax_amount=tax.amount  
                account=tax.account_id.name
                currency=l.currency_id.symbol 
                m={
                  'invoice':invoice,
                  'invoice_date':invoice_date,
                  'bill_no':bill_no,
                  'account':account,
                  'customer':customer,
                  'tax_type':tax_type,
                  'currency':currency,
                  'base_amount':base_amount,
                  'tax_amount':tax_amount
                  }  
                print_lines.append(m)     
        return print_lines

    
    def _get_purchase_register_print_lines(self,tax_line):
       # if tax_line and tax_line=='tax_split':
        #    return self._get_purchage_split_tax_lines()
            
        date_start=self.date_start
        date_stop=self.date_stop        
        m=[]
        lines = self.env['account.invoice'].search([('type','=','in_invoice'),('state','in',['open','paid']),('date_invoice','>=',date_start),('date_invoice','<=',date_stop)],order='date_invoice,number asc')
        journal=''
        sum_freight_charges=sum_packing_charges=sum_net_purchase=sum_total_amount=sum_ecess=sum_s_and_h=sum_mvat_taxable=sum_mvat_tax=sum_cst_taxable=sum_cst_tax=0
        sum_cenvat=sum_service_tax=sum_ecess_service=s_and_h_service=sum_round_off=sum_tds=0.0
        sum_krushi_kalyan_cess=sum_swachh_ecess=0.0
        tmp=False
        for line in lines:
            
            if line.journal_id.name!=journal and tmp==False:  
               journal = line.journal_id.name
               tmp=True            
            else:
                journal= ''
            pv_no = line.number
            bill_date = line.date_invoice
            bill_no = line.reference if line.reference else ''
            customer_name = line.partner_id.name
            currency = line.currency_id.symbol
            amount_total = line.amount_total
            amount_untaxed = line.amount_untaxed
            freight_charges = round(line.amount_untaxed*line.freight_charges/100.0) if line.freight_charges and line.freight_charges_type=='variable' else line.freight_charges
            packing_charges = round(line.amount_untaxed*line.packing_charges/100.0) if line.packing_charges and line.packing_charges_type=='variable' else line.packing_charges
            tds=line.tds_amount if line.tds_amount > 0.0 else 0.0
            tax_details=account='' 
            cenvat=ecess_on_cenvat=swachh_ecess=mvat_base=mvat_tax=0.0
            cst_base=cst_tax=service_tax= ecess_on_service_tax=krushi_kalyan_cess=0.0    
            
            
            for l in line.tax_line_ids:
                tax_details = tax_details + l.name
                if l.tax_type=='cenvat':
                    cenvat = l.amount 
                elif l.tax_type=='mvat':
                    mvat_base = l.base_amount
                    mvat_tax = l.amount
                elif l.tax_type=='cst':
                    cst_base = l.base_amount
                    cst_tax = l.amount
                elif l.tax_type=='service_tax':
                    service_tax = l.amount
                elif l.tax_type=='secess_on_cenvat':
                     swachh_ecess=l.amount   
                elif l.tax_type=='krushi_kalyan_cess':
                     krushi_kalyan_cess=l.amount 
                
                account = account + l.account_id.name if l.account_id.name!=account else l.account_id.name
                
            m.append({
               'journal':journal,
               'pv_no':pv_no,
               'bill_date':bill_date,
               'bill_no':bill_no,
               'customer_name':customer_name ,
               'currency':currency,
               'amount_total':amount_total,
               'amount_untaxed':amount_untaxed,
               'freight_charges':freight_charges,
               'packing_charges':packing_charges,
               'tax_details':tax_details,
               'cenvat':cenvat,
               'mvat_base':mvat_base,
               'mvat_tax':mvat_tax,
               'cst_base':cst_base,
               'cst_tax':cst_tax,
               'service_tax':service_tax,
               'tds':tds,
               'swachh_ecess':swachh_ecess,
               'krushi_kalyan_cess':krushi_kalyan_cess,
               })
            
            sum_total_amount=sum_total_amount+amount_total
            sum_net_purchase=sum_net_purchase+amount_untaxed
            sum_packing_charges=sum_packing_charges+packing_charges
            sum_freight_charges=sum_freight_charges+freight_charges
            sum_cenvat=sum_cenvat+cenvat
            sum_mvat_taxable=sum_mvat_taxable+mvat_base
            sum_mvat_tax=sum_mvat_tax+mvat_tax
            sum_cst_taxable=sum_cst_taxable+cst_base
            sum_cst_tax=sum_cst_tax+cst_tax
            sum_service_tax=sum_service_tax+service_tax
            sum_tds=sum_tds+tds
            sum_krushi_kalyan_cess+=krushi_kalyan_cess
            sum_swachh_ecess+=swachh_ecess
        m.append({
            'journal':'',
            'pv_no':'',
            'bill_date':'',
            'bill_no':'',
            'customer_name':'Total' ,
            'currency':'',
            'amount_total':sum_total_amount,
            'amount_untaxed':sum_net_purchase,
            'freight_charges':sum_freight_charges,
            'packing_charges':sum_packing_charges,
            'tax_details':'',
            'cenvat':sum_cenvat,
            'mvat_base':sum_mvat_taxable,
            'mvat_tax':sum_mvat_tax,
            'cst_base': sum_cst_taxable,
            'cst_tax':sum_cst_tax,
            'service_tax':sum_service_tax,
            'swachh_ecess':sum_swachh_ecess,
            'krushi_kalyan_cess':sum_krushi_kalyan_cess,
            'tds':sum_tds,
            })
                        
        return m  
    
    def _get_sale_register_print_lines(self,):
            
        date_start=self.date_start
        date_stop=self.date_stop        
        m=[]
        lines = self.env['account.invoice'].search([('type','=','out_invoice'),('state','in',['open','paid']),('date_invoice','>=',date_start),('date_invoice','<=',date_stop)],order='date_invoice,number asc')
        journal=''
        sum_freight_charges=sum_packing_charges=sum_net_purchase=sum_total_amount=sum_ecess=sum_s_and_h=sum_mvat_taxable=sum_mvat_tax=sum_cst_taxable=sum_cst_tax=0
        sum_cenvat=sum_service_tax=sum_ecess_service=s_and_h_service=sum_round_off=sum_tds=0.0
        sum_krushi_kalyan_cess=sum_swachh_ecess=0.0
       
        tmp=False
        for line in lines:
            
            if line.journal_id.name!=journal and tmp==False:  
               journal = line.journal_id.name
               tmp=True            
            else:
                journal= ''
            
            bill_date = line.date_invoice
            bill_no = line.number
            customer_name = line.partner_id.name
            currency = line.currency_id.symbol
            amount_total = line.amount_total
            amount_untaxed = line.amount_untaxed
            freight_charges = round(line.amount_untaxed*line.freight_charges/100.0) if line.freight_charges and line.freight_charges_type=='variable' else line.freight_charges
            packing_charges = round(line.amount_untaxed*line.packing_charges/100.0) if line.packing_charges and line.packing_charges_type=='variable' else line.packing_charges
            
            tax_details=account='' 
            cenvat=ecess_on_cenvat=mvat_base=mvat_tax=0.0
            cst_base=cst_tax=service_tax= ecess_on_service_tax=krushi_kalyan_cess=swachh_ecess=0.0    
            
            
            for l in line.tax_line_ids:
                tax_details = tax_details + l.name
                if l.tax_type=='cenvat':
                    cenvat = l.amount 
                elif l.tax_type=='mvat':
                    mvat_base = l.base_amount
                    mvat_tax = l.amount
                elif l.tax_type=='cst':
                    cst_base = l.base_amount
                    cst_tax = l.amount
                elif l.tax_type=='service_tax':
                    service_tax = l.amount
                elif l.tax_type=='secess_on_cenvat':
                     swachh_ecess=l.amount   
                elif l.tax_type=='krushi_kalyan_cess':
                     krushi_kalyan_cess=l.amount 
                                                          
            m.append({
               'journal':journal,
               'bill_date':bill_date,
               'bill_no':bill_no,
               'customer_name':customer_name ,
               'currency':currency,
               'amount_total':amount_total,
               'amount_untaxed':amount_untaxed,
               'freight_charges':freight_charges,
               'packing_charges':packing_charges,
               'tax_details':tax_details,
               'cenvat':cenvat,
               'mvat_base':mvat_base,
               'mvat_tax':mvat_tax,
               'cst_base':cst_base,
               'cst_tax':cst_tax,
               'service_tax':service_tax,
               'swachh_ecess':swachh_ecess,
               'krushi_kalyan_cess':krushi_kalyan_cess,
               })
            
            sum_total_amount=sum_total_amount+amount_total
            sum_net_purchase=sum_net_purchase+amount_untaxed
            sum_packing_charges=sum_packing_charges+packing_charges
            sum_freight_charges=sum_freight_charges+freight_charges
            sum_cenvat=sum_cenvat+cenvat
            sum_mvat_taxable=sum_mvat_taxable+mvat_base
            sum_mvat_tax=sum_mvat_tax+mvat_tax
            sum_cst_taxable=sum_cst_taxable+cst_base
            sum_cst_tax=sum_cst_tax+cst_tax
            sum_service_tax=sum_service_tax+service_tax
            sum_krushi_kalyan_cess+=krushi_kalyan_cess
            sum_swachh_ecess+=swachh_ecess
        m.append({
            'journal':'',
            'bill_date':'',
            'bill_no':'',
            'customer_name':'Total' ,
            'currency':'',
            'amount_total':sum_total_amount,
            'amount_untaxed':sum_net_purchase,
            'freight_charges':sum_freight_charges,
            'packing_charges':sum_packing_charges,
            'tax_details':'',
            'cenvat':sum_cenvat,
            'mvat_base':sum_mvat_taxable,
            'mvat_tax':sum_mvat_tax,
            'cst_base': sum_cst_taxable,
            'cst_tax':sum_cst_tax,
            'service_tax':sum_service_tax,
            'swachh_ecess':sum_swachh_ecess,
            'krushi_kalyan_cess':sum_krushi_kalyan_cess,
            })
                        
        return m  
      
      
    def _get_debtors_ledger_print_lines(self,):
        move_lines=[]
        partner_id=self.partner_id
        account_id = self.partner_id.property_account_receivable_id
        date_start=self.date_start
        date_stop=self.date_stop
        
        if self.partner_id.id:
           partner_id=self.partner_id    
           account_id = self.partner_id.property_account_receivable_id    
           date_start=self.date_start
           date_stop=self.date_stop
           move_lines+=self._get_debtors_ledger_lines(partner_id,account_id,date_start,date_stop)
        else:
            move_lines_partner=self.env['res.partner'].search([('customer','=',True)])
            
            for line in move_lines_partner:
                if line.credit != 0.00 and not line.parent_id.id: 
                   partner_id=line    
                   account_id = line.property_account_receivable_id    
                   date_start=self.date_start
                   date_stop=self.date_stop
                   move_lines+=self._get_debtors_ledger_lines(partner_id,account_id,date_start,date_stop)
        return move_lines
        
    def _get_debtors_ledger_lines(self,partner_id,account_id,date_start,date_stop):
            move_obj=[]
            account_mov_lines= self.env['account.move.line'].search([('account_id','=',account_id.id)])
        
            sum_debit = sum(line.debit for line in account_mov_lines.search([('date','<',date_start),('account_id','=',account_id.id)]))
        
            sum_credit = sum(line.credit for line in account_mov_lines.search([('date','<',date_start),('account_id','=',account_id.id)]))
            debit=credit=0.0
            if sum_debit - sum_credit > 0:
               debit=sum_debit-sum_credit
               particular='To Balance B/F'
            else:
               credit=sum_credit-sum_debit
               particular='By Balance B/F'
            move_obj.append({
                        'date':date_start,
                        'customer':partner_id.name +'  Address :  '+ (partner_id.street if partner_id.street else'')+(' , '+partner_id.street2 if partner_id.street2 else'')+(' , '+partner_id.city if partner_id.city else'')+(' , '+partner_id.state_id.name if partner_id.state_id.name else'') ,
                        'particulars':particular,
                        'code':account_id.code,
                        'credit':credit or '',                             
                        'debit':debit or '', 
                        })
            account_mov_line=account_mov_lines.search([('date','>=',date_start),('date','<=',date_stop),('account_id','=',account_id.id)],order='id asc').sorted(key=lambda r:r.date, reverse=False)
        
            debit1=credit1=0.0
            if account_mov_line:
               for line in account_mov_line:
                
                   particulars=''
                   if line.debit>0:
                      particulars=' To Bill NO '+line.move_id.name
                   else:
                      particulars='By  '+line.journal_id.name+' Doc No '+line.move_id.name+' (Receipt) '+line.name
                   move_obj.append({
                             'date':line.date,
                             'particulars':particulars,
                             'credit':line.credit,
                             'debit':line.debit,
                             'customer':'',
                             'code':''
                             })
                   debit1+=line.debit
                   credit1+=line.credit
        
               if (debit1+debit) - (credit1+credit) > 0:
                  credit=(debit1+debit) - (credit1+credit)
                  particular='By Balance C/F'
                  total=debit1+debit
               else:
                  debit=(credit1+credit) - (debit1+debit)
                  particular='To Balance C/F'
                  total=credit1+credit
               move_obj.append({
                        'date':line.date,
                        'customer':'',
                        'particulars':particular,
                        'code':'',
                        'credit':credit or '',                             
                        'debit':debit or '', 
                        })
       
               move_obj.append({
                        'date':'',
                        'customer':'',
                        'particulars':'Total',
                        'code':'',
                        'credit':total or '',                             
                        'debit':total or '', 
                        })             
        
        
            return move_obj
        
    def _get_creditors_ledger_print_lines(self,):
        move_lines=[]
        if self.partner_id:
           partner_id=self.partner_id    
           account_id = self.partner_id.property_account_payable_id    
           date_start=self.date_start
           date_stop=self.date_stop
           move_lines+=self.get_creditors_ledger_lines(partner_id,account_id,date_start,date_stop)
        else:
            move_lines_partner=self.env['res.partner'].search([('supplier','=',True)])
            
            for line in move_lines_partner:
                if line.debit != 0.00 and not line.parent_id.id: 
                   partner_id=line    
                   account_id = line.property_account_payable_id    
                   date_start=self.date_start
                   date_stop=self.date_stop
                   move_lines+=self.get_creditors_ledger_lines(partner_id,account_id,date_start,date_stop)
                
        return move_lines
    
    def get_creditors_ledger_lines(self,partner_id,account_id,date_start,date_stop):
        move_obj=[]
        
        account_mov_lines= self.env['account.move.line'].search([('account_id','=',account_id.id)])
        sum_debit = sum(line.debit for line in account_mov_lines.search([('date','<',date_start),('account_id','=',account_id.id)]))
        sum_credit = sum(line.credit for line in account_mov_lines.search([('date','<',date_start),('account_id','=',account_id.id)]))
        debit=credit=0.0
        if sum_debit - sum_credit > 0:
             debit=sum_debit-sum_credit
             particular='To Balance B/F'
        else:
             credit=sum_credit-sum_debit
             particular='By Balance B/F'
        move_obj.append({
                        'date':date_start,
                        'customer':partner_id.name+'  Address :  '+ (partner_id.street if partner_id.street else'')+(' , '+partner_id.street2 if partner_id.street2 else'')+(' , '+partner_id.city if partner_id.city else'')+(' , '+partner_id.state_id.name if partner_id.state_id.name else''),
                        'particulars':particular,
                        'code':account_id.code,
                        'credit':credit or '',                             
                        'debit':debit or '', 
                        })
        account_mov_line=account_mov_lines.search([('date','>=',date_start),('date','<=',date_stop),('account_id','=',account_id.id)],order='id asc').sorted(key=lambda r:r.date, reverse=False)
        debit1=credit1=0.0
        if account_mov_line:
           for line in account_mov_line:
               particulars=''
               if line.debit>0:
                  particulars=' To Bill NO '+line.move_id.name
               else:
                  particulars='By  '+line.journal_id.name+' Doc No '+line.move_id.name+' (Receipt) '+line.name
               move_obj.append({
                             'date':line.date,
                             'particulars':particulars,
                             'credit':line.credit,
                             'debit':line.debit,
                             'customer':'',
                             'code':''
                             })
               debit1+=line.debit
               credit1+=line.credit
        
           if (debit1+debit) - (credit1+credit) > 0:
               credit=(debit1+debit) - (credit1+credit)
               particular='By Balance C/F'
               total=debit1+debit
           else:
               debit=(credit1+credit) - (debit1+debit)
               particular='To Balance C/F'
               total=credit1+credit
           move_obj.append({
                        'date':line.date,
                        'customer':'',
                        'particulars':particular,
                        'code':'',
                        'credit':credit or '',                             
                        'debit':debit or '', 
                        })
       
           move_obj.append({
                        'date':'',
                        'customer':'',
                        'particulars':'Total',
                        'code':'',
                        'credit':total or '',                             
                        'debit':total or '', 
                        })             
        return move_obj
        
    def _get_pl_and_balance_sheet_print_lines(self):
        move_obj=[]
        flag_dict={'1':False,'2':False,'3':False,'4':False,'5':False}
        date_start=self.date_start
        date_stop=self.date_stop
        bal_obj=self.env['kts.account.level'].search([],order='order asc')
        amount_total=amount_total1=0.0
        count=0
        move_line1=False
        for line in bal_obj:
            debit=credit=debit1=credit1=0.0
            account_ids =line.account_ids
            if line.tag_ids:
                for t2 in line.tag_ids:
                    account_id= self.env['account.account'].search([('bal_sheet_tag','=',t2.id)])
                    account_ids+=account_id
            account_ids=list(set(account_ids))
            if line.level1=='1':
               for t1 in account_ids:
                   move_line =self.env['account.move.line'].search([('account_id','=',t1.id,),('date','<=',self.date_start)])
                   if self.date_stop:
                      move_line1 =self.env['account.move.line'].search([('account_id','=',t1.id,),('date','<=',self.date_stop)]) 
                   
                   for line1 in move_line:
                         if line1.move_id.state == 'posted':
                            debit+=line1.debit 
                            credit+=line1.credit
                   if move_line1:
                      for line2 in move_line1:
                          if line2.move_id.state == 'posted':
                             debit1+=line2.debit 
                             credit1+=line2.credit
                       
                   
                   total = credit - debit
                   total1 = credit1 - debit1
                   amount_total+= total
                   amount_total1+=total1
            elif line.level1=='2':
               for t1 in account_ids:
                   move_line =self.env['account.move.line'].search([('account_id','=',t1.id,),('date','<=',self.date_start)])
                   if self.date_stop:
                      move_line1 =self.env['account.move.line'].search([('account_id','=',t1.id,),('date','<=',self.date_stop)]) 
                  
                   for line1 in move_line:
                         if line1.move_id.state == 'posted':
                            debit+=line1.debit
                            credit+=line1.credit
                   if move_line1:    
                      for line2 in move_line1:
                          if line2.move_id.state == 'posted':
                             debit1+=line2.debit
                             credit1+=line2.credit
                     
                   total = debit-credit 
                   total1 = debit1-credit1 
                   
                   amount_total+= total
                   amount_total1+= total1
            if line.level1 =='1':
                level1='EQUITY AND LIABILITIES'
                if count==1:
                    level1='1'
                count=1
            elif line.level1 =='2':
                level1='ASSETS'     
                if count==1:
                    move_obj.append({
                             'name_level1':'1',
                             'name_level2':'1',         
                             'name_level3':'Total Amount',
                             'amount1':amount_total,
                             'amount2':amount_total1,
                             })   
                if count==-1:
                    level1='1'
                count=-1 
            
            if line.level2 =='1':
                level2='Shareholder\'s Fund'
                if flag_dict['1']==True:
                    level2='1'        
                flag_dict['1']=True
            elif line.level2 =='2':
                level2='Non Current Liabilities'
                if flag_dict['2']==True:
                    level2='1'        
                flag_dict['2']=True
            
            elif line.level2=='3':
                level2='Current liabilities'
                if flag_dict['3']==True:
                    level2='1'        
                flag_dict['3']=True
            
            elif line.level2=='4':
                level2='Non Current Assets'
                if flag_dict['4']==True:
                    level2='1'        
                flag_dict['4']=True
            
            elif line.level2=='5':
                level2='Current Assets'
                if flag_dict['5']==True:
                    level2='1'        
                flag_dict['5']=True
            
            move_obj.append({
                             'name_level1':level1,
                             'name_level2':level2,         
                             'name_level3':line.name,
                             'amount1':total,
                             'amount2':total1,
                             })  
        move_obj.append({
                         'name_level1':'1',
                         'name_level2':'1',         
                         'name_level3':'Total Amount',
                         'amount1':amount_total,
                         'amount2':amount_total1,
                        })  
         
        return move_obj    
            
class kts_account_payment_report(models.Model):
    _inherit='account.payment'
    type=fields.Selection([
            ('Cash', 'Cash'),
            ('Cheque', 'Cheque'),
            ('Fund Transfer', 'Fund Transfer'),
            ('RTGS', 'RTGS'),
            ('NEFT', 'NEFT'),
            ('IMPS', 'IMPS'),
        ], string='Type',
        help="Select here  related to  payment  type.")
    
    @api.multi
    def to_print_reciept_voucher(self):
        self.ensure_one()
        if self.partner_type=='customer':
           report_name='receipt'
           report_name1='Receipt'
        elif self.partner_type=='supplier':
             report_name='voucher'
             report_name1='Voucher'
            
        return do_print_setup(self,{'name':report_name1, 'model':'account.payment','report_name':report_name},
                False,False)
    
    
    def get_move_lines(self):
              lines=[]
              move_lines=self.env['account.move.line'].search([('payment_id','=',self.id)])
              name=invoice_name=''
              debit1=credit1=sum_debit=sum_credit=total=0.0
              amount_due=False
              for line in move_lines:
                  if line.account_id.user_type_id.id == 3:
                        debit=line.debit
                        credit=line.credit       
                        name=line.name  
                  else:    
                      if line.reconcile:
                         date=formatLang(line.date,date=True)
                         credit1+=line.credit
                         invoice_name+= '\n'+ '('+line.name +' Amount: '+ str(line.credit)+' Date: '+date+')'
                  
                  total+=line.debit
                        
                        
              lines.append({
                            'debit':debit,
                            'credit':credit,
                            'invoice':name+invoice_name,
                            'invoice_amount':line.credit,
                            'amount_due':False
                                    })
                             
                        
              if debit-credit1 > 0.0:
                 amount_due=debit-credit1 
                         
                 lines.append({
                                    'debit':'',
                                    'credit':'',
                                    'invoice':'',
                                    'invoice_amount':'',
                                    'amount_due':amount_due
                                    })
                         
              lines.append({
                            'debit':'total',
                            'credit':'',
                            'total':total,
                            'invoice':'',
                            'invoice_amount':'',
                            'amount_due':False,
                            })  
              return lines             
    
    def get_val_recs(self):
              lines=[]
              move_lines=self.env['account.move.line'].search([('payment_id','=',self.id)])
              name=invoice_name=''
              debit1=credit1=sum_debit=sum_credit=total=0.0
              amount_due=False
              for line in move_lines:
                  if line.account_id.user_type_id.id == 3:
                        debit=line.debit
                        credit=line.credit       
                        name=line.name  
                  else:    
                      if line.reconcile:
                         date=formatLang(line.date,date=True)
                         debit1+=line.debit
                         invoice_name+= '\n'+ '('+line.name +' Amount: '+ str(line.debit)+' Date: '+date+')'
                  
                  total+=line.credit
                        
                        
              lines.append({
                            'debit':debit,
                            'credit':credit,
                            'invoice':name+invoice_name,
                            'invoice_amount':line.debit,
                            'amount_due':False
                                    })
                             
                        
              if credit-debit1 > 0.0:
                 amount_due=credit-debit1 
                         
                 lines.append({
                                    'debit':'',
                                    'credit':'',
                                    'invoice':'',
                                    'invoice_amount':'',
                                    'amount_due':amount_due
                                    })
                         
              lines.append({
                            'debit':'total',
                            'credit':'',
                            'total':total,
                            'invoice':'',
                            'invoice_amount':'',
                            'amount_due':False,
                            })  
              return lines             
    
class kts_inventory_reports(models.Model):
    _name='kts.inventory.reports'
    
    def get_move_lines(self):
        move_obj=[]
        if self.report_type =='inventory_incoming_shipments': 
            move_obj = self.inventory_incoming_shipments()
        elif self.report_type=='reorder_report':
            move_obj = self.reorder_report()
        elif self.report_type=='grn_register':
            move_obj = self.grn_register()
        elif self.report_type=='delivery_chalan_register':
            move_obj = self.delivery_chalan_register()
        elif self.report_type=='scrap_inward_register':
            move_obj = self.scrap_inward_register()
        elif self.report_type=='stock_list':
            move_obj = self.stock_list()
        elif self.report_type=='historical_stock_list':
            move_obj = self.historical_stock_list()
        elif self.report_type=='total_inward_value':
            move_obj = self.total_inward_value()
        elif self.report_type=='total_dispatch_summary':
            move_obj = self.total_dispatch_summary()
        elif self.report_type=='material_reservation_status':
            move_obj = self.material_reservation_status()
        
        return move_obj
    
    def _get_report_type(self):
        report_type=[]
        report_type.append(('inventory_incoming_shipments','Inventory Incoming Shipment Schedule Register'))
        report_type.append(('reorder_report','Product Reorder Report'))
        report_type.append(('grn_register','GRN Register'))
        report_type.append(('delivery_chalan_register','Delivery Challan Register'))
        report_type.append(('scrap_inward_register','Scrap Inward Register'))
        report_type.append(('stock_list','Stock List'))
        report_type.append(('historical_stock_list','Historical Stock List'))
        report_type.append(('total_inward_value','Total Inward Summary'))
        report_type.append(('total_dispatch_summary','Total Dispatch Summary'))
        report_type.append(('material_reservation_status','Material Reservation Status'))
        
        return report_type        
    
    name=fields.Char('Name')
    report_type=fields.Selection(_get_report_type, string='Report Type')
    date_start=fields.Date(string='Start Date')
    date_stop=fields.Date(string='End Date')
    product_id = fields.Many2one('product.product',string='Product')
    location_id = fields.Many2one('stock.location',string='Scrap Location')
    location_id1 = fields.Many2one('stock.location',string='Stock Location')
    categ_id=fields.Many2one('product.category',string='Product Category')
    
    @api.onchange('date_start','date_stop')
    def onchange_start_end_date(self):
        if self.date_start and self.date_stop:
           if self.date_start > self.date_stop:
              self.update({'date_stop':False})
              return {'value':{'date_stop':False},'warning':{'title':'User Error','message':'End Date should be greater than Start Date'}}
    @api.multi
    def to_print_inventory(self):
           self.ensure_one()
           if self.report_type=='inventory_incoming_shipments':
               report_name= 'inventory_incoming_shipments'    
               report_name1='inventory_incoming_shipments'
           elif self.report_type=='reorder_report':
               report_name= 'reorder_report'    
               report_name1='Product Reorder'
           elif self.report_type=='grn_register':
               report_name= 'grn_register'    
               report_name1='GRN Register'
           elif self.report_type=='delivery_chalan_register':
               report_name= 'delivery_chalan_register'    
               report_name1='Delivery Register'
           elif self.report_type=='scrap_inward_register':
               report_name= 'scrap_inward_register'    
               report_name1='Scrap Inward Register'
           elif self.report_type=='stock_list':
               report_name= 'stock_list'    
               report_name1='Stock List'
           elif self.report_type=='historical_stock_list':
               report_name= 'historical_stock_list'    
               report_name1='Historical Stock List'
           elif self.report_type=='total_inward_value':
               report_name= 'total_inward_value'    
               report_name1='Total Inward Value'
           elif self.report_type=='total_dispatch_summary':
               report_name= 'total_dispatch_summary'    
               report_name1='Total Dispatch Summary'
           elif self.report_type=='material_reservation_status':
               report_name= 'material_reservation_status'    
               report_name1='Material Reservation Status'
           
           return do_print_setup(self,{'name':report_name1, 'model':'kts.inventory.reports','report_name':report_name},
                False,False)
       
    @api.model
    def create(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start = formatLang(vals.get('date_start'),date=True) if vals.get('date_start') else formatLang(fields.Datetime.now(),date=True) 
           date_stop = formatLang(vals.get('date_stop'),date=True) if vals.get('date_stop') else False 
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+date_start+' To '+date_stop
           vals['name']=name
                          
        ret = super(kts_inventory_reports, self).create(vals)
        return ret
   
    @api.multi
    def write(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start =  vals['date_start'] if vals.get('date_start') else self.date_start 
           date_stop = vals['date_stop'] if vals.get('date_stop') else self.date_stop
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+formatLang(date_start,date=True)+' To '+formatLang(date_stop,date=True)
           vals.update({
                       'name':name,
                       })   
        return super(kts_inventory_reports, self).write(vals)
    
    def material_reservation_status(self):
        lines=[]
        location_id=self.location_id1.id
        subquery=' order by aaa.product_id '
        if self.product_id.id and self.categ_id:
            subquery='where aaa.product_id=%s and aaa.categ_id=%s'%(self.product_id.id,self.categ_id.id)
            subquery+' order by aaa.product_id ' 
        
        elif self.product_id.id and not self.categ_id:
            subquery='where aaa.product_id=%s '%(self.product_id.id)
            subquery+' order by aaa.product_id '
        
        elif not self.product_id.id and  self.categ_id:
            subquery='where aaa.categ_id=%s '%(self.categ_id.id)
            subquery+' order by aaa.product_id '
        
        self.env.cr.execute('select '
                            'aaa.product_id, '
                            'aaa.product_name, '
                            'aaa.qty, '
                            'aaa.document, ' 
                            'aaa.categ_id '
                            'from '
                            '(select aa.product_id, '
                            'aa.product_name, '
                            'sum(aa.qty) as qty, '
                            'aa.categ_id, '
                            'case when COALESCE(cc.picking,\'NOT\')=\'NOT\' then bb.production_name else cc.picking end as document ' 
                            'from '
                            '(select a.product_id, a.qty, a.reservation_id, b.raw_material_production_id, b.production_id, b.picking_id, c.name_template as product_name, d.categ_id '
                            'from stock_quant a, stock_move b, product_product c, product_template d  where a.location_id=\'%s\' ' 
                            'and reservation_id is not null and a.reservation_id=b.id and a.product_id=c.id and c.product_tmpl_id=d.id) aa '
                            'left outer join '
                            '(select name as production_name, id from mrp_production b) bb on aa.raw_material_production_id=bb.id '
                            'left outer join '
                            '(select name as picking, id  from stock_picking b) cc on aa.picking_id=cc.id ' 
                            'group by aa.product_id, aa.product_name,aa.categ_id, case when COALESCE(cc.picking,\'NOT\')=\'NOT\' then bb.production_name else cc.picking end ) aaa ' 
                             +subquery
                            ,([location_id])) 
         
        move_lines = self.env.cr.fetchall()
        i=0
        total=0.0
        for line in move_lines:
            i+=1
            lines.append({
                         'sr_no':i,
                         'product':line[1],
                         'qty':line[2],
                         'doc':line[3]           
                          }) 
        return lines
    
    
    def total_dispatch_summary(self):
        lines=[]
        self.report_type
        date_start=self.date_start
        date_stop=self.date_stop
        res=self.env['kts.report.query'].search([('query_name','=',self.report_type)])
        query=res.query
        self.env.cr.execute(query,(date_start,date_stop))
#         self.env.cr.execute('select b.name_template, sum(a.product_uom_qty), sum(a.product_uom_qty*a.price_unit) '  
#                                  'from stock_move a, product_product b '  
#                                  'where a.state = \'done\' and a.location_id=12 and a.location_dest_id=9 and a.product_id=b.id  and to_date(to_char(a.date,\'DDMMYYYY\'),\'DDMMYYYY\') >= %s and to_date(to_char(a.date,\'DDMMYYYY\'),\'DDMMYYYY\') <= %s '   
#                                  'group by a.product_id, b.name_template ' 
#                                  'Order by a.product_id ',(date_start,date_stop)) 
        move_lines = self.env.cr.fetchall()
        i=0
        total=0.0
        for line in move_lines:
            i+=1
            total+=float(line[2])
            lines.append({
                         'sr_no':i,
                         'product':line[0],
                         'qty':line[1],
                         'amount':line[2]           
                          })
        lines.append({
                      'sr_no':'',
                      'product':'',
                      'qty':'Total',
                      'amount':total           
                          })
                 
        return lines
    
    def total_inward_value(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        res=self.env['kts.report.query'].search([('query_name','=',self.report_type)])
        query=res.query
        self.env.cr.execute(query,(date_start,date_stop))
        
#         self.env.cr.execute('select b.name_template, sum(a.product_uom_qty), sum(a.product_uom_qty*a.price_unit) '  
#                                  'from stock_move a, product_product b '  
#                                  'where a.state = \'done\' and a.location_id=8 and a.location_dest_id=12 and a.product_id=b.id  and to_date(to_char(a.date,\'DDMMYYYY\'),\'DDMMYYYY\') >= %s and to_date(to_char(a.date,\'DDMMYYYY\'),\'DDMMYYYY\') <= %s '   
#                                  'group by a.product_id, b.name_template ' 
#                                  'Order by a.product_id ',(date_start,date_stop)) 
        move_lines = self.env.cr.fetchall()
        i=0
        total=0.0
        for line in move_lines:
            i+=1
            total+=float(line[2])
            lines.append({
                         'sr_no':i,
                         'product':line[0],
                         'qty':line[1],
                         'amount':line[2]           
                          })
             
        lines.append({
                      'sr_no':'',
                      'product':'',
                      'qty':'Total',
                      'amount':total           
                          })
            
        return lines
        
    
    def get_product_name(self,lines):
        product_name=''
        for i in lines:
            product_name+=i.product_id.name+'\n'
        return product_name    
    
    def get_product_qty(self,lines):
        product_qty=''
        for i in lines:
            product_qty+=str(i.product_uom_qty)+'\n'
        return product_qty    
    
    def get_product_uom(self,lines):
        product_uom=''
        for i in lines:
            product_uom+=i.product_uom.name+'\n'
        return product_uom    
    
    def inventory_incoming_shipments(self):
        date_start=self.date_start
        date_stop=self.date_stop
        lines=[]
        res=self.env['kts.report.query'].search([('query_name','=',self.report_type)])
        query=res.query
        self.env.cr.execute(query,(date_start,date_stop))
        
#         self.env.cr.execute('select ' 
#                             'aa.schedule_date, '
#                             'case when COALESCE(bb.partner,\'NOT\')=\'NOT\' then cc.partner else bb.partner end as partner, '
#                             'COALESCE(bb.po,\'NA\') as po, '
#                             'COALESCE(bb.po_date,\'2000-01-01\') as po_date, '
#                             'aa.shipment, '
#                             'aa.product_name, '
#                             'aa.product_qty, '
#                             'aa.uom  from '
#                             '(select a.purchase_new_id, a.partner_id, a.name as shipment, d.name_template as product_name, b.product_qty, e.name as uom, to_date(to_char(b.date_expected,\'DDMMYYYY\'),\'DDMMYYYY\') ' 
#                             'as schedule_date from stock_picking a, stock_move b, stock_picking_type c, product_product d, product_uom e '
#                             'where '
#                             'a.id=b.picking_id and '
#                             'a.picking_type_id=c.id and '
#                             'c.code=\'incoming\' and '
#                             'b.product_id=d.id and '
#                             'b.product_uom=e.id and '
#                             'a.state not in (\'done\',\'draft\',\'cancel\') and '
#                             'b.state not in (\'done\',\'draft\',\'cancel\') and '
#                             'to_date(to_char(b.date_expected,\'DDMMYYYY\'),\'DDMMYYYY\') between %s and %s) aa '
#                             'left outer join '
#                             '(select a.id, b.name as partner, a.name as po, to_date(to_char(a.date_order,\'DDMMYYYY\'),\'DDMMYYYY\') as po_date  from purchase_order a, res_partner b where a.partner_id=b.id) bb on aa.purchase_new_id = bb.id '
#                             'left outer join '
#                             '(select name as partner, id from res_partner) cc on aa.partner_id=cc.id '
#                             'Order by aa.schedule_date, case when COALESCE(bb.partner,\'NOT\')=\'NOT\' then cc.partner else bb.partner end, COALESCE(bb.po,\'NA\') ',(date_start,date_stop))
#     
        
        
        move_lines=self.env.cr.fetchall() 
        i=0 
        for line in move_lines:
               i+=1
               lines.append({
                          'sr_no':i,   
                          'date':line[0],
                          'supplier':line[1],
                          'po_no':line[2],
                          'po_date':line[3],
                          'receiptno':line[4],
                          'product':line[5],
                          'qty': line[6],
                          'uom':line[7], 
                          })
        return lines    
    
    def reorder_report(self):
        lines=[]
        
        if self.product_id and self.categ_id:
           move_lines= self.env['stock.warehouse.orderpoint'].search([('product_id','=',self.product_id.id),('product_id.categ_id','=',self.categ_id.id)])
        elif self.categ_id and not self.product_id:
            move_lines= self.env['stock.warehouse.orderpoint'].search([('product_id.categ_id','=',self.categ_id.id)])
        
        elif not self.categ_id and self.product_id:
            move_lines= self.env['stock.warehouse.orderpoint'].search([('product_id','=',self.product_id.id)])
        
        else:
            move_lines=self.env['stock.warehouse.orderpoint'].search([])
        i=0
        for line in move_lines:
             i+=1
             lines.append({
                           'sr_no':i,
                           'record_no':line.name,
                           'product':line.product_id.name,
                           'warehouse':line.warehouse_id.name,
                           'location':line.location_id.name,
                           'min_qty':line.product_min_qty,
                           'max_qty':line.product_max_qty,
                           'mul_qty':line.qty_multiple,
                           'product_uom':line.product_uom.name,
                           
                           })
        return lines                    
    
    def delivery_chalan_register(self):
        lines=[]
        if self.date_start and self.date_stop:
            stock_pick_move = self.env['stock.picking'].search([('state','in', ['done']),('date_done','>=',self.date_start),('date_done','<=',self.date_stop)],order='date_done asc')    
        i=0
        for line in stock_pick_move:
            if line.picking_type_id.code=='outgoing':
               i+=1
               lines.append({
                          'sr_no':i,
                          'customer':(line.partner_id.name if line.partner_id.name else '')+('\n'+line.partner_id.street if line.partner_id.street else'')+(','+line.partner_id.city if line.partner_id.city else ''),
                          'date':line.date_done,
                          'product':  self.get_product_name(line.move_lines_related),
                          'qty': self.get_product_qty(line.move_lines_related),
                          'uom':self.get_product_uom(line.move_lines_related),
                          'receiptno':line.name,
                          'so':line.group_id.name,
                          })
        return lines    
    
    
    
    def grn_register(self):
        lines=[] 
        stock_pick_move = self.env['stock.picking'].search([('state','=', ['done']),('date_done','>=',self.date_start),('date_done','<=',self.date_stop)],order='date_done asc')
        i=0
        for line in stock_pick_move:
            if line.picking_type_id.code=='incoming':
               i+=1
               lines.append({
                          'sr_no':i,
                          'po_no':line.group_id.name,
                          'grn_no':line.grn_no,
                          'supplier':line.partner_id.name,
                          'location':line.location_dest_id.name,
                          'date':line.date_done,
                          'product':  self.get_product_name(line.move_lines),
                          'qty': self.get_product_qty(line.move_lines),
                          'receiptno':line.name
                          })
        return lines
    
    def get_scrap_from(self,stock_move):
       if stock_move.picking_id:
           scrap_from = stock_move.picking_id.picking_type_id.name+'\n'+stock_move.picking_id.name+'\n'+ stock_move.picking_id.origin if stock_move.picking_id.origin else ''
       else:
           scrap_from = stock_move.name    
       return scrap_from
    
    def scrap_inward_register(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        
        if self.location_id:
           stock_move_lines= self.env['stock.move'].search([('state','=','done'),('date','>=',date_start),('date','<=',date_stop),('location_dest_id','=',self.location_id.id)],order='date,location_dest_id asc') 
        else:
           stock_move_lines= self.env['stock.move'].search([('state','=','done'),('date','>=',date_start),('date','<=',date_stop)],order='date,location_dest_id asc')
        location=''
        for line in stock_move_lines:
            if line.location_dest_id.scrap_location:
               if line.picking_id:
                    scrap_from = line.picking_id.picking_type_id.name+'\n'+line.picking_id.name+'\n'+ line.picking_id.origin if line.picking_id.origin else ''
                    if line.location_dest_id.name!=location:
                       location=line.location_dest_id.name
                       location1=location
                    else:
                       location1=''    
                    lines.append({
                                 'location':location1,
                                 'product':'',
                                 })
                   
                    lines.append({
                              'location':'',
                              'date':line.date,
                              'product':line.product_id.name,
                              'qty':line.product_qty,
                              'uom':line.product_uom.name,
                              'scrap_from':scrap_from,
                              })
        return lines        
    
    
    def calculate_stock_qty(self,line,product):
        uom_obj=self.env['product.uom']
        qty_receive=0.0
        qty_receive = sum(i.product_uom_qty for i in self.env['stock.move'].search([('product_id','=',product.id),('location_dest_id','=',line.id),('state','=','done')]))        
        qty_done = sum(i.product_uom_qty for i in self.env['stock.move'].search([('product_id','=',product.id),('location_id','=',line.id),('state','=','done')]))
        qty_reserve_quant = sum(i.qty for i in self.env['stock.quant'].search([('product_id','=',product.id),('location_id','=',line.id),('reservation_id','!=',False)]))
        
        self.env.cr.execute('select ' 
                            'a1.product_id, '
                            'sum(a1.product_qty * a1.dfactor/a1.efactor) as prod_incoming_qty_done, '
                            'a1.uom_id '  
                            'from( '
                            'select a.product_id, '
                            'a.product_qty, '
                            'd.factor as dfactor, e.factor as efactor, '
                            'c.uom_id '
                            'from '
                            'stock_move a, '
                            'product_product b, '
                            'product_template c, '
                            'product_uom d, '
                            'product_uom e, '
                            'stock_picking g, '
                            'stock_picking_type h '
                            'where '
                            'a.product_id=b.id and '
                            'a.product_id=\'%s\' and '
                            'b.product_tmpl_id=c.id and '
                            'c.uom_id=d.id and '
                            'a.state in (\'assigned\') and '
                            'a.product_uom=e.id and '
                            'g.id=a.picking_id and '
                            'g.picking_type_id=h.id and '
                            'h.code=\'incoming\' and g.state=\'assigned\') a1 '
                            'group by a1.product_id, a1.uom_id'%(product.id))
        
        total_lines=self.env.cr.fetchall()
        qty_intransit=(total_lines[0][1] if total_lines else 0.0) 
        act_qty=qty_receive-qty_done
        res_qty=qty_reserve_quant
        free_qty=act_qty-res_qty
        
        return{
               'act_qty':act_qty,
               'res_qty':res_qty,
               'free_qty':free_qty,
               'qty_intransit':qty_intransit       
               } 

    def stock_list(self):
        lines=[]
        subquery='Order by aa.location_id, aa.product '
        if self.location_id1.id or self.categ_id.id:
           if self.location_id1.id and not self.categ_id.id:
              stock_location=self.location_id1.id
              subquery=' where aa.location_id=%s '%(stock_location)
              subquery+='Order by aa.location_id, aa.product, aa.categ_id '
           elif not self.location_id1.id and self.categ_id.id:
               categ_id=self.categ_id.id
               subquery=' where aa.categ_id=%s '%(categ_id)
               subquery+='Order by aa.location_id, aa.product, aa.categ_id '
           elif self.location_id1.id and self.categ_id.id:
               categ_id=self.categ_id.id
               stock_location=self.location_id1.id
               subquery=' where aa.location_id=%s and aa.categ_id=%s '%(stock_location,categ_id)
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
        location_name=''
        i=0
        for line in move_lines:     
             i+=1
             free_qty=line[0]-line[1]
             if line[6] != location_name:
                location_name=line[6]
                location_name1=location_name
             else:
                 location_name1=''
             lines.append({
                         'location':location_name1,
                         'product':'',
                          })
                   
             lines.append({
                          'sr_no':i,
                          'location':'',
                          'product':line[7],
                          'act_qty':line[0],
                          'res_qty':line[1],
                          'free_qty':free_qty,
                          'min_qty':self.env['stock.warehouse.orderpoint'].search([('location_id','=',line[3]),('product_id','=',line[2])]).product_min_qty if self.env['stock.warehouse.orderpoint'].search([('location_id','=',line[3]),('product_id','=',line[2])]) else 0.0,
                          'qty_intransit': line[8] if line[8] else 0.0,
                          'category':line[9]
                          })        
    
        return lines        
    
    def historical_stock_list(self):
        lines=[]
        location_name=''
        start_date=self.date_start
        res=self.env['kts.report.query'].search([('query_name','=',self.report_type)])
        query=res.query
        self.env.cr.execute(query,(start_date,start_date,start_date,start_date))
        
#         subquery='Order by aaaa.location_id, aaaa.prod_name '
#         if self.location_id1.id:
#            stock_location=self.location_id1.id
#            subquery=' and aaaa.location_id=%s'%(stock_location)
#            subquery+='Order by aaaa.location_id, aaaa.prod_name '
#         self.env.cr.execute('select ' 
#                             'COALESCE(aaaa.location_id,\'0\') as location_id, ' 
#                             'COALESCE(hhhh.stock_location) as stock_location, '
#                             'COALESCE(aaaa.product_id,\'0\') as product_id, ' 
#                             'COALESCE(aaaa.uom_id,\'0\') as uom_id, ' 
#                             'COALESCE(aaaa.prod_name,\'\') as prod_name, ' 
#                             'COALESCE(aaaa.prod_uom,\'\') as prod_uom, ' 
#                             'COALESCE( COALESCE(eeee.prod_incoming_qty_done,\'0\') - COALESCE(dddd.prod_outgoing_qty_done,\'0\'),\'0\') as prod_qty_done '
#                             'from '
#                             '(select aaa.location_id, aaa.product_id, ccc.uom_id, bbb.name_template as prod_name, ddd.name as prod_uom  from ' 
#                             '(select distinct aa.location_id, aa.product_id from ' 
#                             '(select location_id, product_id, date from stock_move '
#                             'where date <= %s ' 
#                             'union ' 
#                             'select location_dest_id as location_id, product_id, date from stock_move '
#                             'where date <= %s) aa) aaa, ' 
#                             'product_product bbb, product_template ccc, product_uom ddd '
#                             'where aaa.product_id=bbb.id and bbb.product_tmpl_id=ccc.id and ccc.uom_id=ddd.id ) aaaa '
#                             'left outer join '
#                             '( ' 
#                             'select a1.product_id, a1.location_sec_id, sum(a1.product_qty * a1.dfactor/a1.efactor) as prod_outgoing_qty_done, a1.uom_id  from '
#                             '(select a.product_id, a.location_id as location_sec_id, a.product_qty, d.factor as dfactor, e.factor as efactor, c.uom_id, a.picking_id '
#                             'from stock_move a, product_product b, product_template c, product_uom d, product_uom e ' 
#                             'where a.product_id=b.id and '
#                             'b.product_tmpl_id=c.id and '
#                             'c.uom_id=d.id and '
#                             'a.state in (\'done\') and a.date <= %s and a.product_uom=e.id) a1 '
#                             'group by a1.product_id, a1.location_sec_id, a1.uom_id) dddd '
#                             'on aaaa.product_id=dddd.product_id and aaaa.location_id=dddd.location_sec_id ' 
#                             'left outer join '
#                             '(select a1.product_id, a1.location_sec_id, sum(a1.product_qty * a1.dfactor/a1.efactor) as prod_incoming_qty_done, a1.uom_id  from '
#                             '(select a.product_id, a.location_dest_id as location_sec_id, a.product_qty, d.factor as dfactor, e.factor as efactor, c.uom_id, a.picking_id '
#                             'from stock_move a, product_product b, product_template c, product_uom d, product_uom e '
#                             'where a.product_id=b.id and '
#                             'b.product_tmpl_id=c.id and '
#                             'c.uom_id=d.id and '
#                             'a.state in (\'done\') and a.date <= %s and a.product_uom=e.id) a1 '
#                             'group by a1.product_id, a1.location_sec_id, a1.uom_id '
#                             ') eeee '
#                             'on aaaa.product_id=eeee.product_id and aaaa.location_id=eeee.location_sec_id ' 
#                             'inner join '
#                             '(select id,name as stock_location from stock_location where usage=\'internal\') hhhh '
#                             'on  aaaa.location_id=hhhh.id '
#                             +subquery
#                             ,(start_date,start_date,start_date,start_date,))
        
        move_lines=self.env.cr.fetchall() 
        i=0 
        for line in move_lines:
            if line[1]!=location_name:
               location_name=line[1]
               location_name1=location_name       
               i=0
            else:
               location_name1=''
            lines.append({
                   'location':location_name1,
                   'product':'',
                        })
            i+=1
            lines.append({
                      'sr_no':i,
                      'location':'',
                      'product':line[4],
                      'act_qty':line[6],
                      'uom':line[5],
                        })        
                   
        return lines       
      
      
class kts_picking_delivery_chalan(models.Model):
    _inherit='stock.picking'
    
    @api.multi
    def to_print_delivery_chalan(self):
        self.ensure_one()
        if self.picking_type_id.code=='outgoing':
           report_name='delivery_chalan'
           report_name1='Delivery Chalan'
        elif self.picking_type_id.code=='incoming':
            report_name='inward_receipt'
            report_name1='Inward Receipt'    
        elif self.picking_type_id.code=='internal':
            report_name='internal_transfer_chalan'
            report_name1='Internal Transfer Receipt' 
        
        return do_print_setup(self,{'name':report_name1, 'model':'stock.picking','report_name':report_name},
                False,False)
    
    def get_print_delivery_chalan(self):
        lines=[]
        for line in self.pack_operation_product_ids:
            if line.product_id.tracking == 'serial':
                if line.qty_done > 0:   
                   for line1 in line.pack_lot_ids: 
                       lines.append({
                          'product':line.product_id.name,
                          'uom':line.product_uom_id.name,
                          'serialno':line1.lot_id.name,
                          'qty_done':1.0,
                          })
            elif line.product_id.tracking == 'lot':
                if line.qty_done > 0:   
                   for line1 in line.pack_lot_ids: 
                       lines.append({
                          'product':line.product_id.name,
                          'uom':line.product_uom.name,
                          'serialno':line1.lot_id.name,
                          'qty_done':qty,
                              })
            else:
               lines.append({
                          'product':line.product_id.name,
                          'uom':line.product_uom.name,
                          'serialno':line1.lot_id.name,
                          'qty_done':line.product_uom_qty,
                          })
            return lines
    def print_barcode(self, cr, uid, ids, context={}):
        this = self.browse(cr, uid, ids, context=context) 
        report_name='barcode'
        report_name1='Barcode' 
        
        context.update({'this':this, 'uiModelAndReportModelSame':False})
        return do_print_setup(self,cr, uid, ids, {'name':report_name1, 'model':'stock.picking','report_name':report_name},
                False,False,context)
    
    def get_val_recs(self):
        lines=[]
        i=0
        for line in self.pack_operation_product_ids:
                for line1 in line.pack_lot_ids:
                    lines.append({
                             'barcode':barcode.make_barcode(line1.lot_name,'code39'),
                              })          
        return lines
        
    def get_po_qty(self,product_id):
        for line in self.purchase_new_id.order_line:
            if line.product_id.id==product_id.id:
                return line.product_qty
        
    def get_move_lines(self):
        lines=[]
        if self.picking_type_id.code == 'outgoing':
            return self.get_print_delivery_chalan()
            
        i=0
        for line in self.move_lines:
            if line.location_dest_id.id==self.location_dest_id.id:
               i+=1 
               lines.append({
                          'sr_no':i,
                          'product':line.product_id.name,
                          'uom':line.product_uom.name,
                          'qty_done':line.product_uom_qty,
                          'po_qty':self.get_po_qty(line.product_id),
                          })
        return lines
            
class kts_mrp_reports(models.Model):
    _name='kts.mrp.reports'
    
    def get_move_lines(self):
        move_obj=[]
        if self.report_type =='daily_production': 
            move_obj = self.daily_production()
        elif self.report_type=='daily_production_vs_plan_achieved':
            move_obj = self.daily_production_vs_plan_achieved()
        elif self.report_type=='daily_production_plan':
            move_obj = self.daily_production_plan()
        elif self.report_type=='wip_stock_register':
            move_obj = self.wip_stock_register()
        elif self.report_type=='scrap_inward_mrp_register':
            move_obj = self.scrap_inward_mrp_register()
        elif self.report_type=='total_production':
            move_obj = self.total_production()
        elif self.report_type=='raw_material_consumation_summary':
            move_obj = self.raw_material_consumation_summary()
        elif self.report_type=='mrp_material_req_summary':
            move_obj = self.mrp_material_req_summary()
        elif self.report_type=='direct_material_summary':
            move_obj = self.direct_material_summary()
            
        return move_obj
    
    def _get_report_type(self):
        report_type=[]
        report_type.append(('daily_production','Daily Production Report'))
        report_type.append(('daily_production_vs_plan_achieved','Daily Production Vs Plan Achieved Report'))
        report_type.append(('daily_production_plan','Daily Production Plan Report'))
        report_type.append(('wip_stock_register','Work In Process Stock Register'))
        report_type.append(('scrap_inward_mrp_register','Scrap Inward MRP Register'))
        report_type.append(('total_production','Total Production Summary'))
        report_type.append(('raw_material_consumation_summary','Raw Material Consumption Summary'))
        report_type.append(('mrp_material_req_summary','Manufacturing Material Requirement Summary'))
        report_type.append(('direct_material_summary','Direct Material Cost Summary'))
        
        return report_type        

    name=fields.Char('Name')
    report_type=fields.Selection(_get_report_type, string='Report Type')
    date_start=fields.Date(string='Start Date')
    date_stop=fields.Date(string='End Date')
    location_id=fields.Many2one('stock.location',string='Scrap Location')
    categ_id=fields.Many2one('product.category',string='Product Category')
    
    @api.multi
    def to_print_mrp(self,):
           self.ensure_one()
           this = self.browse() 
           if self.report_type=='daily_production':
               report_name= 'daily_production'    
               report_name1='Daily Production'
           elif self.report_type=='daily_production_vs_plan_achieved':
               report_name= 'daily_production_vs_plan_achieved'    
               report_name1='Daily Production Vs Plan Achieved'
           elif self.report_type=='daily_production_plan':
               report_name= 'daily_production_plan'    
               report_name1='Daily Production Plan' 
           elif self.report_type=='wip_stock_register':
               report_name= 'wip_stock_register'    
               report_name1='WIP Stock Register' 
           elif self.report_type=='scrap_inward_mrp_register':
               report_name= 'scrap_inward_mrp_register'    
               report_name1='Scrap Inward MRP Register'
           elif self.report_type=='total_production':
               report_name= 'total_production'    
               report_name1='Total Production Summary'
           elif self.report_type=='raw_material_consumation_summary':
               report_name= 'raw_material_consumation_summary'    
               report_name1='Raw Material Consumption Summary'
           elif self.report_type=='mrp_material_req_summary':
               report_name= 'mrp_material_req_summary'    
               report_name1='Manufacturing Material Requirement Summary'
           elif self.report_type=='direct_material_summary':
               report_name= 'direct_material_summary'    
               report_name1='Direct Material Cost Summary'
           
           return do_print_setup(self,{'name':report_name1, 'model':'kts.mrp.reports','report_name':report_name},
                False,)
    
    @api.onchange('date_start','date_stop')
    def onchange_start_end_date(self):
        if self.date_start and self.date_stop:
           if self.date_start > self.date_stop:
              self.update({'date_stop':False})
              return {'value':{'date_stop':False},'warning':{'title':'User Error','message':'End Date should be greater than Start Date'}}

    
    @api.model
    def create(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start = formatLang(vals.get('date_start'),date=True) if vals.get('date_start') else formatLang(fields.Datetime.now(),date=True) 
           date_stop = formatLang(vals.get('date_stop'),date=True) if vals.get('date_stop') else False 
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+date_start+' To '+date_stop
           vals['name']=name
                          
        ret = super(kts_mrp_reports, self).create(vals)
        return ret
   
    @api.multi
    def write(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start =  vals['date_start'] if vals.get('date_start') else self.date_start 
           date_stop = vals['date_stop'] if vals.get('date_stop') else self.date_stop
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+formatLang(date_start,date=True)+' To '+formatLang(date_stop,date=True)
           vals.update({
                       'name':name,
                       })   
        return super(kts_mrp_reports, self).write(vals)
    
    def direct_material_summary(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        subquery=''
        if self.categ_id.id:
            subquery=' and aa.categ_id=%s'%(self.categ_id.id)
        self.env.cr.execute('select ' \
                            'aa.id, ' \
                            'aa.date_finished, ' \
                            'aa.mo, '
                            'aa.final_product,'
                            'aa.product_qty, '
                            'aa.product_uom, '
                            'aa.direct_material, '
                            'aa.name_template, '
                            'aa.dmc, '
                            'aa.uom, '
                            'case when COALESCE(bb.product_total_qty,\'0\')=0 then 0 else COALESCE(bb.product_total_dmc,\'0\')/bb.product_total_qty end as product_dmc, '
                            'aa.categ_id '
                            'from '
                            '( '
                            'select a.id, '
                            'to_date(to_char(a.date_finished,\'DDMMYYYY\'),\'DDMMYYYY\') as date_finished, '
                            'a.name as mo, '
                            'a.product_id final_product, '
                            'a.product_qty, '
                            'a.product_uom, '
                            'b.direct_material, '
                            'c.name_template, '
                            'case when COALESCE(a.product_qty,\'0\')=0 then 0 else COALESCE(b.direct_material,\'0\')/a.product_qty end as dmc, '
                            'd.name as uom, ' 
                            'e.categ_id '
                            'from mrp_production a, (select sum(product_qty*price_unit) as direct_material,raw_material_production_id   from stock_move where state=\'done\' group by raw_material_production_id ) b, product_product c, product_uom d, product_template e '
                            'where a.state=\'done\' and '
                            'a.id=b.raw_material_production_id  and '
                            'a.product_id=c.id and '
                            'a.product_uom=d.id and '
                            'c.product_tmpl_id=e.id and '
                            'to_date(to_char(date_finished,\'DDMMYYYY\'),\'DDMMYYYY\') between %s and %s ) aa, '
                            '( '
                            'select '
                            'a.product_id final_product, '
                            'sum(a.product_qty) as product_total_qty, '
                            'sum(b.direct_material) as product_total_dmc '
                            'from mrp_production a, (select sum(product_qty*price_unit) as direct_material,raw_material_production_id   from stock_move where state=\'done\' group by raw_material_production_id ) b, product_product c, product_uom d '
                            'where a.state=\'done\' and '
                            'a.id=b.raw_material_production_id  and '
                            'a.product_id=c.id and '
                            'a.product_uom=d.id and '
                            'to_date(to_char(date_finished,\'DDMMYYYY\'),\'DDMMYYYY\') between %s and %s   group by a.product_id) bb '
                            'where aa.final_product=bb.final_product '+ subquery +
                            'order by aa.date_finished, aa.mo ',(date_start,date_stop,date_start,date_stop))
        
        move_lines = self.env.cr.fetchall()
        i=0
        total=wcost_total=0.0
        for line in move_lines:
            i+=1
            total+=float(line[6])
          
            lines.append({
                         'sr_no':i,
                         'date':line[1],
                         'mo':line[2],
                         'product':line[7],
                         'qty':line[4],
                         'uom':line[9],
                         'total_dmc':line[6],
                         'unit_dmc':line[8],          
                         'wcost':line[10] 
                          })
        lines.append({
                    'sr_no':'',
                    'date':'',
                    'mo':'',
                    'product':'Total',
                    'qty':'',
                    'uom':'',
                    'total_dmc':total,
                    'unit_dmc':'',          
                    'wcost':''    
                          })
             
        return lines
    
        
    
    def mrp_material_req_summary(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        subquery=''
        if self.categ_id.id:
            subquery=' where aaa.categ_id=%s'%(self.categ_id.id)
        self.env.cr.execute('select ' \
                            'aaa.product_id,' \
                            'aaa.required_qty,' \
                            'aaa.prod_name,' \
                            'aaa.uom, aaa.reserved_qty, ' \
                            'COALESCE(bbb.free_qty,\'0\') '  
                            'as free_qty, '  
                            'aaa.categ_id '
                            'from(select aa.product_id, sum(aa.required_qty) as required_qty, aa.prod_name, aa.uom, sum(COALESCE(bb.reserved_qty,\'0\')) as reserved_qty, aa.categ_id  from '
                            '(select a.id, b.id as move_id, b.product_id, b.product_uom_qty as required_qty, c.name_template as prod_name, d.name as uom, e.categ_id '
                            'from mrp_production a, stock_move b, product_product c, product_uom d, product_template e '
                            'where to_date(to_char(a.date_planned,\'DDMMYYYY\'),\'DDMMYYYY\') between %s and %s and '
                            'a.id=b.raw_material_production_id and '
                            'b.product_id=c.id and '
                            'b.product_uom=d.id and '
                            'c.product_tmpl_id=e.id and '
                            'a.state not in (\'done\',\'cancel\',\'draft\') and '
                            'b.state not in (\'done\',\'cancel\',\'draft\') ) aa '
                            'left outer join '
                            '(select sum(qty) as reserved_qty, reservation_id from stock_quant group by reservation_id) bb on aa.move_id=bb.reservation_id '
                            'group by aa.product_id, aa.prod_name, aa.uom, aa.categ_id ) aaa '
                            'left outer join '
                            '(select sum(a.qty) as free_qty, a.product_id from '
                            'stock_quant a, stock_location b '
                            'where a.location_id=b.id and '
                            'b.usage=\'internal\' and '
                            'b.scrap_location=\'f\' and active=\'t\' and '
                            'a.reservation_id is null group by a.product_id) bbb on aaa.product_id=bbb.product_id '+subquery,(date_start,date_stop)) 
        move_lines = self.env.cr.fetchall()
        i=0
        for line in move_lines:
            i+=1
            if (line[4]+line[5])-line[1]>0:
                bal_qty=0.0
            else:
                bal_qty=line[1]-(line[4]+line[5])    
            
            lines.append({
                         'sr_no':i,
                         'product':line[2],
                         'uom':line[3],
                         'req_qty':line[1],
                         'res_qty':line[4],
                         'free_qty':line[5],
                         'bal_qty':bal_qty           
                          })
             
        return lines
    
    
    def raw_material_consumation_summary(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        subquery=''
        if self.categ_id.id:
            subquery=' and c.categ_id= %s '%(self.categ_id.id)
        self.env.cr.execute('select b.name_template, sum(a.product_uom_qty), sum(a.product_uom_qty*a.price_unit), c.categ_id '  
                                 'from stock_move a, product_product b,  product_template c '  
                                 'where a.state = \'done\' and a.location_id=12 and a.location_dest_id=7 and a.product_id=b.id and b.product_tmpl_id=c.id and to_date(to_char(a.date,\'DDMMYYYY\'),\'DDMMYYYY\') >= %s and to_date(to_char(a.date,\'DDMMYYYY\'),\'DDMMYYYY\') <= %s '+subquery+   
                                 'group by a.product_id, b.name_template, c.categ_id  ' 
                                 'Order by a.product_id, c.categ_id ',(date_start,date_stop)) 
        move_lines = self.env.cr.fetchall()
        i=0
        total=0.0
        for line in move_lines:
            i+=1
            total+=float(line[2])
            lines.append({
                         'sr_no':i,
                         'product':line[0],
                         'qty':line[1],
                         'amount':line[2]           
                          })
        lines.append({
                      'sr_no':'',
                      'product':'',
                      'qty':'Total',
                      'amount':total           
                     })
                 
        return lines
    
    def total_production(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        self.env.cr.execute('select c.name, sum(a.product_qty) '  
                                 'from mrp_production a, product_product b,product_template c '  
                                 'where a.state= \'done\' and a.product_id=b.id  and to_date(to_char(a.date_finished,\'DDMMYYYY\'),\'DDMMYYYY\') >= %s and to_date(to_char(a.date_finished,\'DDMMYYYY\'),\'DDMMYYYY\') <= %s '   
                                 'group by a.product_id, c.name ' 
                                 'Order by a.product_id ',(date_start,date_stop)) 
        mrp_move_lines = self.env.cr.fetchall()
        i=0      
        for line in mrp_move_lines:
            i+=1
            lines.append({
                          'sr_no':i,
                          'product':line[0],
                          'qty':line[1]
                          })
        return lines     
             
    
    def daily_production(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        res=self.env['kts.report.query'].search([('query_name','=',self.report_type)])
        query=res.query
        self.env.cr.execute(query,(date_start,date_stop))
#         self.env.cr.execute('select '
#                             'aa.name_template, '
#                             'aa.uom, ' 
#                             'sum(aa.product_qty), '
#                             'aa.mo_date, ' 
#                             'array_to_string(array_agg(aa.MO),\',\') '
#                             'from '
#                             '( '
#                             'select ' 
#                             'b.name_template, '
#                             'c.name as uom, ' 
#                             'sum(d.product_qty) as product_qty, ' 
#                             'to_date(to_char(d.date,\'DDMMYYYY\'),\'DDMMYYYY\') as mo_date, ' 
#                             'a.name as MO '
#                             'from ' 
#                             'mrp_production a, ' 
#                             'product_product b, ' 
#                             'product_uom c, '
#                             'stock_move d '
#                             'where ' 
#                             'a.product_id=b.id and ' 
#                             'a.product_uom=c.id and ' 
#                             'a.id=d.production_id and '
#                             'a.product_id=d.product_id and '
#                             'd.state=\'done\' and '
#                             'to_date(to_char(d.date,\'DDMMYYYY\'),\'DDMMYYYY\') between %s and %s '
#                             'group by ' 
#                             'a.product_id, ' 
#                             'to_date(to_char(d.date,\'DDMMYYYY\'),\'DDMMYYYY\'), ' 
#                             'b.name_template, '
#                             'c.name, '
#                             'a.name ) aa '
#                             'group by ' 
#                             'aa.name_template, '
#                             'aa.uom, ' 
#                             'aa.mo_date '
#                             'Order by aa.mo_date, aa.name_template ',(date_start,date_stop)) 
                       
        mrp_move_lines = self.env.cr.fetchall()
        for line in mrp_move_lines:  
            lines.append({
                          'date':line[3],
                          'mrp_no': line[4],
                          'product':line[0],
                          'qty':line[2],
                          'uom':line[1],  
                          })
        
        return lines    
    
    def daily_production_vs_plan_achieved(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        res=self.env['kts.report.query'].search([('query_name','=',self.report_type)])
        query=res.query
        self.env.cr.execute(query,(date_start,date_stop))
#         self.env.cr.execute('select '
#                             'aaa.date, ' 
#                             'aaa.product_id, ' 
#                             'ddd.prod_name, ' 
#                             'ddd.uom, ' 
#                             'bbb.mo_plan, ' 
#                             'bbb.plan_qty, ' 
#                             'ccc.produced_qty, ' 
#                             'ccc.produced_mo '
#                             'from '
#                             '(select ' 
#                             'distinct aa.date, aa.product_id '
#                             'from '
#                             '(select ' 
#                             'to_date(to_char(a.date_planned,\'DDMMYYYY\'),\'DDMMYYYY\') as date, ' 
#                             'a.product_id '
#                             'from '
#                             'MRP_production a '
#                             'where '
#                             'a.state!=\'cancel\' '
#                             'union '
#                             'select ' 
#                             'to_date(to_char(d.date,\'DDMMYYYY\'),\'DDMMYYYY\') as date, '
#                             'a.product_id '
#                             'from '
#                             'mrp_production a, ' 
#                             'stock_move d '
#                             'where '
#                             'a.id=d.production_id and '
#                             'a.product_id=d.product_id and '
#                             'd.state=\'done\' ) aa ) aaa '
#                             'left outer join '
#                             '(select ' 
#                             'to_date(to_char(a.date_planned,\'DDMMYYYY\'),\'DDMMYYYY\') as date_planned, ' 
#                             'b.id as product_id, '
#                             'b.name_template as product_name, ' 
#                             'array_to_string(array_agg(a.name),\',\')  as mo_plan, ' 
#                             'c.name as uom, '
#                             'sum( case when a.state=\'draft\' then a.product_qty else a.plan_qty end  * d.factor/e.factor ) as plan_qty '
#                             'from '
#                             'MRP_production a, ' 
#                             'product_product b, '
#                             'product_template c, '
#                             'product_uom d, '
#                             'product_uom e '
#                             'where '
#                             'a.product_id=b.id and '
#                             'b.product_tmpl_id=c.id and '
#                             'c.uom_id=d.id and '
#                             'a.product_uom=e.id and '
#                             'a.state!=\'cancel\' '
#                             'group by '
#                             'to_date(to_char(a.date_planned,\'DDMMYYYY\'),\'DDMMYYYY\'), ' 
#                             'b.id, '
#                             'b.name_template, c.name ) bbb on aaa.product_id=bbb.product_id and aaa.date=bbb.date_planned '
#                             'left outer join '
#                             '(select '
#                             'aa.product_id, '
#                             'aa.uom, '
#                             'sum(aa.product_qty) as produced_qty, '
#                             'aa.mo_date as date, '
#                             'array_to_string(array_agg(aa.MO),\',\') as produced_mo '
#                             'from '
#                             '( '
#                             'select ' 
#                             'a.product_id, '
#                             'c.name as uom, '
#                             'sum(d.product_qty * c.factor/e.factor ) as product_qty, ' 
#                             'to_date(to_char(d.date,\'DDMMYYYY\'),\'DDMMYYYY\') as mo_date, ' 
#                             'a.name as MO '
#                             'from '
#                             'mrp_production a, ' 
#                             'product_product b, '
#                             'product_uom c, '
#                             'stock_move d, '
#                             'product_uom e, '
#                             'product_template f '
#                             'where '
#                             'a.product_id=b.id and '
#                             'a.product_uom=e.id and '
#                             'a.id=d.production_id and '
#                             'a.product_id=d.product_id and '
#                             'b.product_tmpl_id=f.id and '
#                             'f.uom_id=c.id and '
#                             'd.state=\'done\' '
#                             'group by '
#                             'a.product_id, ' 
#                             'to_date(to_char(d.date,\'DDMMYYYY\'),\'DDMMYYYY\'), ' 
#                             'c.name, '
#                             'a.name ) aa '
#                             'group by '
#                             'aa.Product_id, '
#                             'aa.uom, '
#                             'aa.mo_date ) ccc on aaa.product_id=ccc.product_id and aaa.date=ccc.date '
#                             'inner join '
#                             '(select a.id as product_id, c.name as uom, a.name_template as prod_name ' 
#                             'from product_product a, product_template b, product_uom c  '
#                             'where '
#                             'a.product_tmpl_id=b.id and '
#                             'b.uom_id=c.id ) ddd on aaa.product_id=ddd.product_id '
#                             'where aaa.date between %s and %s '
#                             'Order by aaa.date, aaa.product_id, bbb.product_name ',(date_start,date_stop)) 
#                                     
        mrp_move_lines=self.env.cr.fetchall()
        
        for line in mrp_move_lines:
            lines.append({
                          'date':line[0],
                          'mrp_no':line[4],
                          'product':line[2],
                          'qty':line[5],
                          'achieved_qty':line[6],
                          'uom':line[3],
                          'prod_mo':line[7]
                          })
        return lines    
    
    def daily_production_plan(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        self.env.cr.execute('select ' 
                            'to_date(to_char(a.date_planned_start,\'DDMMYYYY\'),\'DDMMYYYY\') as date_planned, ' 
                            'b.id, '
                            'c.name as product_name, ' 
                            'a.name as mo_name, '
                            'd.name as uom, '
                            'case when a.state=\'draft\' then a.product_qty else a.plan_qty end  * d.factor/e.factor '
                            'from '
                            'MRP_production a, ' 
                            'product_product b, ' 
                            'product_template c, '
                            'product_uom d, ' 
                            'product_uom e '
                            'where '
                            'a.product_id=b.id and '
                            'b.product_tmpl_id=c.id and '
                            'c.uom_id=d.id and '
                            'a.product_uom=e.id and '
                            'a.state!=\'cancel\' and '
                            'to_date(to_char(a.date_planned_start,\'DDMMYYYY\'),\'DDMMYYYY\') between %s and %s'
                            'order by '
                            'to_date(to_char(a.date_planned_start,\'DDMMYYYY\'),\'DDMMYYYY\'), ' 
                            'b.id',(date_start,date_stop))
        
        
        mrp_move_lines=self.env.cr.fetchall()
        i=0
        total_qty=0
        date=''
        product=''
        for line in mrp_move_lines:
            i+=1         
            if line[0] != date:
                date=line[0]
                date1=date 
                product=''
            else:
                date1=''
                
            if line[2]!=product:
                product=line[2]
                product1=product
 
                total_qty1=total_qty
                total_qty=0
                total_qty=line[5] if line[5] else 0
            else:
                product1=''       
                total_qty= total_qty+(line[5] if line[5] else 0)
                total_qty1=0
            
            lines.append({
                          'date':'',
                          'mrp_no':'',
                          'product':'',
                          'total_qty':total_qty1,
                          })
            
            lines.append({
                          'date':date1,
                          'product':'',
                          'mrp_no':'',
                          'total_qty':0
                          })
            
            
            lines.append({
                          'date':'',
                          'sr_no':i,
                          'mrp_no':line[3],
                          'product':product1,
                          'qty':line[5],
                          'uom':line[4],
                          'total_qty':0
                          })
        
        lines.append({
                      'date':'',
                      'mrp_no':'',
                      'product':'',
                      'total_qty':total_qty,
                          })
            
        return lines    
    
    def wip_stock_register(self):
        lines=[]
        
        if self.date_start and self.date_stop:
             mrp_move_lines=self.env['mrp.production'].search([('state','=','ready'),('date_planned','>=',self.date_start),('date_planned','<=',self.date_stop),('jobcard_printed','=',True)],order='date_planned asc')
        i=0
        for line in mrp_move_lines: 
            for consumed_line in line.move_lines:
                 i=i+1
                 lines.append({
                          'sr_no':i,
                          'date':line.date_planned,
                          'product':consumed_line.product_id.name,
                          'qty':consumed_line.product_uom_qty,
                          'uom':consumed_line.product_uom.name,
                           })
        return lines    
    
    def scrap_inward_mrp_register(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop 
        if self.location_id:
           stock_move_lines= self.env['stock.move'].search([('state','=','done'),('date','>=',date_start),('date','<=',date_stop),('location_dest_id','=',self.location_id.id)],order='date,location_dest_id asc') 
        else:
           stock_move_lines= self.env['stock.move'].search([('state','=','done'),('date','>=',date_start),('date','<=',date_stop)],order='date,location_dest_id asc')
        location=''
        
        for line in stock_move_lines:
            if line.location_dest_id.scrap_location:
               if not line.picking_id:
                   scrap_from = line.name       
                   if line.location_dest_id.name!=location:
                       location=line.location_dest_id.name
                       location1=location
                   else:
                       location1=''    
                   lines.append({
                                 'location':location1,
                                 'product':'',
                                 })
                   
                   lines.append({
                              'location':'',
                              'date':line.date,
                              'product':line.product_id.name,
                              'qty':line.product_qty,
                              'uom':line.product_uom.name,
                              'scrap_from':scrap_from,
                              })
        return lines        
    
class kts_sale_reports(models.Model):
    _name='kts.sale.reports'
    
    def get_move_lines(self):
        move_obj=[]
        if self.report_type =='total_so_summary':     
            move_obj = self.total_so_summary()
        
        elif self.report_type=='sale_price_variance':
              move_obj = self.sale_price_variance()
         
        return move_obj
        
    def _get_report_type(self):
            report_type=[]
            report_type.append(('total_so_summary','Total Sales Order Summary'))
            report_type.append(('sale_price_variance','Sale Price Variance Report'))
        
            return report_type        
        
    name=fields.Char('Name')
    report_type=fields.Selection(_get_report_type, string='Report Type')
    date_start=fields.Date(string='Start Date')
    date_stop=fields.Date(string='End Date')
    
    @api.onchange('date_start','date_stop')
    def onchange_start_end_date(self):
        if self.date_start and self.date_stop:
           if self.date_start > self.date_stop:
              self.update({'date_stop':False})
              return {'value':{'date_stop':False},'warning':{'title':'User Error','message':'End Date should be greater than Start Date'}}
    
    @api.model
    def create(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start = formatLang(vals.get('date_start'),date=True) if vals.get('date_start') else formatLang(fields.Datetime.now(),date=True) 
           date_stop = formatLang(vals.get('date_stop'),date=True) if vals.get('date_stop') else False 
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+date_start+' To '+date_stop
           vals['name']=name
                          
        ret = super(kts_sale_reports, self).create(vals)
        return ret
   
    @api.multi
    def write(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start =  vals['date_start'] if vals.get('date_start') else self.date_start 
           date_stop = vals['date_stop'] if vals.get('date_stop') else self.date_stop
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+formatLang(date_start,date=True)+' To '+formatLang(date_stop,date=True)
           vals.update({
                       'name':name,
                       })   
        return super(kts_sale_reports, self).write(vals)
    @api.multi
    def to_print_sale(self):
           self.ensure_one()
           ret=False
           if self.report_type=='total_so_summary':
               report_name= 'total_so_summary'    
               report_name1='Total Sale Order Summary'
           elif self.report_type=='sale_price_variance':
                report_name= 'sale_price_variance'    
                report_name1='Sale Price Variance Report'  
        
           else:
            ret=super(kts_inventory_reports_bin, self).to_print_inventory()
        
           if ret:
              return ret
           else:
              return do_print_setup(self, {'name':report_name1, 'model':'kts.sale.reports','report_name':report_name},
                False,False)
    
           
           return do_print_setup(self,{'name':report_name1, 'model':'kts.sale.reports','report_name':report_name},
                False,False)
    
    
    def sale_price_variance(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        self.env.cr.execute('select '
                            'min(aa.price_unit), max(aa.price_unit), sum(aa.weighted_cost)/sum(aa.product_uom_qty), ' 
                            'aa.product_id, aa.name ' 
                            'from ' 
                            '(select '
                            'b.product_id, b.price_unit, b.product_uom_qty, b.product_uom_qty*b.price_unit as weighted_cost, d.name '
                            'from '
                            'sale_order a, sale_order_line b, product_product c, product_template d '
                            'where '
                            'a.id=b.order_id and '
                            'date_order between %s and %s and b.product_id=c.id) aa '
                            'group by aa.product_id, aa.name',(date_start,date_stop))
        move_lines=self.env.cr.fetchall()
        i=0
        for line in move_lines:
            i+=1
            lines.append({
                          'sr_no':i,
                          'product_name':line[4],
                          'min':line[0],
                          'max':line[1],
                          'avg':line[2]
                          
                          }) 
        return lines  

    def total_so_summary(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        self.env.cr.execute('select d.name, sum(a.product_uom_qty), sum(a.price_subtotal) '  
                                 'from sale_order_line a, product_product b, sale_order c,product_template d  '  
                                 'where a.order_id=c.id and c.state in (\'sale\',\'done\') and a.product_id=b.id  and to_date(to_char(c.date_order,\'DDMMYYYY\'),\'DDMMYYYY\') >= %s and to_date(to_char(c.date_order,\'DDMMYYYY\'),\'DDMMYYYY\') <= %s '   
                                 'group by a.product_id, d.name ' 
                                 'Order by a.product_id ',(date_start,date_stop)) 
        move_lines = self.env.cr.fetchall()
        i=0
        total=0.0
        for line in move_lines:
            i+=1 
            total+=float(line[2])
            lines.append({
                         'sr_no':i,
                         'product':line[0],
                         'qty':line[1],
                         'amount':line[2]
                         })
        lines.append({
                      'sr_no':'',
                      'product':'',
                      'qty':'Total',
                      'amount':total
                         })
        
        return lines
    
        
      
    
class kts_purchase_reports(models.Model):
    _name='kts.purchase.reports'
    
    def get_move_lines(self):
        move_obj=[]
        if self.report_type =='purchase_pending_order':     
            move_obj = self.purchase_pending_order()
        elif self.report_type =='purchase_schedule_order':     
            move_obj = self.purchase_schedule_order()    
        elif self.report_type =='total_po_summary':     
            move_obj = self.total_po_summary()    
        elif self.report_type =='total_freight_value':     
            move_obj = self.total_freight_value()    
        elif self.report_type =='po_register':     
            move_obj = self.po_register()    
        
        return move_obj
    
    
    
    def _get_report_type(self):
        report_type=[]
        report_type.append(('purchase_pending_order','Purchase Pending Order'))
        report_type.append(('purchase_schedule_order','Purchase Schedule Order'))
        report_type.append(('total_po_summary','Total Purchase Order Summary'))
        report_type.append(('total_freight_value','Total Freight Value'))
        report_type.append(('po_register','Purchase Order Register'))
       
        return report_type        

    name=fields.Char('Name')
    report_type=fields.Selection(_get_report_type, string='Report Type')
    date_start=fields.Date(string='Start Date')
    date_stop=fields.Date(string='End Date')
    partner_id = fields.Many2one('res.partner',string='Supplier')
    categ_id=fields.Many2one('product.category',string='Product Category')
    
    @api.multi
    def to_print_purchase(self):
           self.ensure_one()
           if self.report_type=='purchase_pending_order':
               report_name= 'purchase_pending_order'    
               report_name1='Purchase Pending Order'
           elif self.report_type=='purchase_schedule_order':
               report_name= 'purchase_schedule_order'    
               report_name1='Purchase Schedule Order'
           elif self.report_type=='total_po_summary':
               report_name= 'total_po_summary'    
               report_name1='Total Purchase Order Summary'      
           elif self.report_type=='total_freight_value':
               report_name= 'total_freight_value'    
               report_name1='Total Freight Value'
           elif self.report_type=='po_register':
               report_name= 'po_register'    
               report_name1='Purchase Order Register'
           
           return do_print_setup(self,{'name':report_name1, 'model':'kts.purchase.reports','report_name':report_name},
                False,False)
    
    @api.onchange('date_start','date_stop')
    def onchange_start_end_date(self):
        if self.date_start and self.date_stop:
           if self.date_start > self.date_stop:
              self.update({'date_stop':False})
              return {'value':{'date_stop':False},'warning':{'title':'User Error','message':'End Date should be greater than Start Date'}}
    
    @api.model
    def create(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start = formatLang(vals.get('date_start'),date=True) if vals.get('date_start') else formatLang(fields.Datetime.now(),date=True) 
           date_stop = formatLang(vals.get('date_stop'),date=True) if vals.get('date_stop') else False 
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+date_start+' To '+date_stop
           vals['name']=name
                          
        ret = super(kts_purchase_reports, self).create(vals)
        return ret
   
    @api.multi
    def write(self, vals):
        if vals.get('report_type'):
           name = vals['report_type'].replace('_',' ')
           date_start =  vals['date_start'] if vals.get('date_start') else self.date_start 
           date_stop = vals['date_stop'] if vals.get('date_stop') else self.date_stop
           if date_stop==False:
               date_stop=''
           name = name.title() +' From '+formatLang(date_start,date=True)+' To '+formatLang(date_stop,date=True)
           vals.update({
                       'name':name,
                       })   
        return super(kts_purchase_reports, self).write(vals)
    
    
   
    def total_po_summary(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        self.env.cr.execute('select d.name, sum(a.product_qty), sum(a.price_subtotal) '  
                                 'from purchase_order_line a, product_product b, purchase_order c,product_template d  '  
                                 'where a.order_id=c.id and c.state in (\'purchase\',\'done\') and a.product_id=b.id  and to_date(to_char(c.date_order,\'DDMMYYYY\'),\'DDMMYYYY\') >= %s and to_date(to_char(c.date_order,\'DDMMYYYY\'),\'DDMMYYYY\') <= %s '   
                                 'group by a.product_id, d.name ' 
                                 'Order by a.product_id ',(date_start,date_stop)) 
        move_lines = self.env.cr.fetchall()
        i=0
        total=0.0
        for line in move_lines:
            i+=1 
            total+=float(line[2])
            lines.append({
                         'sr_no':i,
                         'product':line[0],
                         'qty':line[1],
                         'amount':line[2]
                         })
        lines.append({
                      'sr_no':'',
                      'product':'',
                      'qty':'Total',
                      'amount':total
                         })
        
        return lines
    
    def total_freight_value(self):
        lines=[]
        date_start=self.date_start
        date_stop=self.date_stop
        total=0.0
        move_lines=self.env['purchase.order'].search([('state','in',('purchase','done')),('date_order','>=',date_start),('date_order','<=',date_stop)])
        for line in move_lines:
            freight_charges1=line.freight_charges if ( line.freight_charges_type =='fixed' or line.freight_charges_type =='variable') else 0.0
            if line.freight_charges_type =='variable':
               freight_charges1=round(line.amount_untaxed*freight_charges1/100.0)   
            total+=freight_charges1
        return total    
    
        
    def purchase_pending_order(self):
        lines=[]
        if self.partner_id:
            po_move_lines=self.env['purchase.order'].search([('partner_id','=',self.partner_id.id),('state','=','purchase'),('date_order','>=',self.date_start),('date_order','<=',self.date_stop)],order='partner_id,id,date_order asc')   
        else:
            po_move_lines=self.env['purchase.order'].search([('state','=','purchase'),('date_order','>=',self.date_start),('date_order','<=',self.date_stop)],order='partner_id,id,date_order asc')
        customer=''
        for line in po_move_lines:
            flag=False
            for j in line.picking_ids:
                if j.state=='assigned':
                    flag = True
            if flag:
               if line.partner_id.name!=customer: 
                  customer=line.partner_id.name
                  customer1=customer
               else:
                 customer1=''
               lines.append({
                            'customer':customer1,
                            'po_no':'',
                            'product_name':'',
                            }) 
               
               lines.append({
                          'customer':'',
                          'po_no':line.name+' , '+formatLang(line.date_order,date=True),
                          'po_details':line.name+' , '+formatLang(line.date_order,date=True),
                          'product_name':''
                           })
               i=0
               for order_line in line.order_line:
                 bal_qty=0.0
                 for k in order_line.move_ids:
                     if k.state=='done' or k.state=='cancel':
                        bal_qty += k.product_uom_qty    
                 
                 if (order_line.product_qty - bal_qty)>0:  
                     i+=1
                     lines.append({
                              'customer':'',
                              'po_no':False,
                              'sr_no':i,
                              'product_name':order_line.product_id.name,
                              'order_qty':order_line.product_qty,
                              'supplied_qty':order_line.qty_received,
                              'balanced_qty':order_line.product_qty - order_line.qty_received,
                              'scheduled_date':order_line.date_planned,   
                              })
        return lines
    
    def purchase_schedule_order(self):
        lines=[]
        purchase_order_lines=self.env['purchase.order.line'].search([('state','=','purchase'),('date_planned','>=',self.date_start),('date_planned','<=',self.date_stop)],order='date_planned,order_id asc')
        customer=date1=order_name=''
        i=0
        for line in purchase_order_lines:
            if line.product_qty-line.qty_received >0:
                move_ids=line.move_ids
                deliver_qty=0.0
                for line1 in move_ids:
                    if line1.state=='done' or line1.state=='cancel':
                        deliver_qty+=line1.product_uom_qty
                if line.product_qty-deliver_qty>0:
                    date=formatLang(line.date_planned, date=True)
                    if date!=date1: 
                       date1=date
                       date2=date1
                    else:
                       date2=''
                    lines.append({
                             'date':date2,
                             'customer':'',
                             'po_no':'',
                             'product_name':'',
                             
                             })                    
                    if line.order_id.partner_id.name!=customer: 
                        customer=line.order_id.partner_id.name
                        customer1=customer
                    else:
                       customer1=''
                    lines.append({
                            'customer':customer1,
                            'po_no':'',
                            'product_name':'',
                            'date':''
                            }) 
               
                    if line.order_id.name!=order_name: 
                        order_name=line.order_id.name
                        order_name1=order_name
                    else:
                       order_name1=''
                    
                    lines.append({
                          'customer':'',
                          'po_no':order_name1,
                          'po_details':line.order_id.name+' , '+formatLang(line.order_id.date_order,date=True),
                          'product_name':'',
                          'date':'', 
                           })
                    i+=1
                    lines.append({
                              'date':'',
                              'customer':'',
                              'po_no':'',
                              'sr_no':i,
                              'product_name':line.product_id.name,
                              'order_qty':line.product_qty,
                              'supplied_qty':line.qty_received,
                              'balanced_qty':line.product_qty - line.qty_received,
                              'scheduled_date':line.date_planned,   
                              })        
                   
        return lines
    
    def po_register(self):
        lines=[]
        if self.partner_id:
           purchase_order_lines=self.env['purchase.order'].search([('state','=','purchase'),('date_order','>=',self.date_start),('date_order','<=',self.date_stop),('partner_id','=',self.partner_id.id)],order='date_order,id asc')
        else:    
           purchase_order_lines=self.env['purchase.order'].search([('state','=','purchase'),('date_order','>=',self.date_start),('date_order','<=',self.date_stop)],order='date_order,id asc')
        i=0
        for po in purchase_order_lines:
            for line in po.order_line:
                i+=1
                lines.append({
                            'sr_no':i,
                            'po_no':po.name,
                            'po_date':po.date_order,
                            'name':po.partner_id.name,
                            'product':line.product_id.name,
                            'qty':line.product_qty,
                            'rate':line.price_unit,
                            'date':line.date_planned,
                            'amount':line.price_subtotal
                            })         
        return lines        
       
class kts_account_invoice_report(models.Model):
    
    _inherit = "account.invoice"
      
    remark=fields.Text('Remark')
    print_header=fields.Boolean('Print Header',default=True)
    def get_so_fields(self,val):
        date=''
        if val=='so_date':
            if self.origin:
               date=self.env['sale.order'].search([('name','=',self.origin)]).date_order
        elif val=='buyer_ref':
            if self.origin:
                   date=self.env['sale.order'].search([('name','=',self.origin)]).client_order_ref
                   
        elif val=='buyer_ref_date':
            if self.origin:
                   date=self.env['sale.order'].search([('name','=',self.origin)]).client_order_ref_date
        return date    
    @api.multi                
    def to_print_invoice(self):
        self.ensure_one()
        if self.type=='out_invoice':
           report_name= 'customer_invoice'
           name='Customer Invoice'          
        elif self.type=='out_refund':
            report_name= 'credit_note'
            name='Credit Note'
        elif self.type=='in_invoice':
            report_name= 'supplier_invoice'
            name='Supplier Invoice'
        elif self.type=='in_refund':
            report_name= 'debit_note'
            name='Debit Note'
                 
        return do_print_setup(self,{'name':name, 'model':'account.invoice','report_name':report_name},
                False,self.partner_id.id, )
    
    def dispatch_policy(self):
        if self.picking_policy=='direct':
           return 'Deliver each product when available'
        else:
            return 'Deliver all products at once'
    def print_packing_charges(self):
        packing_charges=self.packing_charges if ( self.packing_charges_type =='fixed' or self.packing_charges_type =='variable') else 0.0
       
        if self.packing_charges_type =='variable':
            packing_charges=round(self.amount_untaxed * packing_charges/100.0) 
        return packing_charges
    
    def print_freight_charges(self):
        freight_charges=self.freight_charges if ( self.freight_charges_type =='fixed' or self.freight_charges_type =='variable') else 0.0
        if self.freight_charges_type =='variable':
            freight_charges=round(self.amount_untaxed*freight_charges/100.0)   
        return freight_charges    
    
    def get_invoice_amount_c2text(self):
        amount=self.amount_total
        currency_name=self.currency_id.name
        lang=self._context.get('lang')
        ret=currency_to_text(amount,currency_name,lang)
        return  ret   
    
    def get_vat_amount_c2text(self):
        for line in self.tax_line_ids:
            if line.tax_type=='mvat':
                amount=line.amount
                currency_name=self.currency_id.name
                lang=self._context.get('lang')
                ret=currency_to_text(amount,currency_name,lang)
                return  ret   
    
    def get_move_lines(self):
        lines=[]
        i=0
        
        for line in self.invoice_line_ids:
              if self.fiscal_position_id.price_include and self.type in ['out_invoice','out_refund']:
                  subtotal=line.price_unit * line.quantity * (1 - (line.discount or 0.0) / 100.0)   
              i+=1
              lines.append({
                            'sr_no':i,
                            'product':line.product_id.name,
                            'qty':line.quantity,
                            'price':line.price_unit,
                            'disc':line.discount,
                            'uom':line.uom_id.name,
                            'subtotal':line.price_subtotal if not self.fiscal_position_id.price_include else subtotal,
                            'tarrif':line.tarrif_id.code if line.tarrif_id else ''
                            })
        return lines
    def get_val_recs(self):
        lines=[]
        if self.tax_line_ids:
           for line in self.tax_line_ids:
                lines.append({
                          'tax_name':line.name,
                          'tax_rate':line.tax_id.amount,
                          'perc':'%',
                          'tax_amount':line.amount,
                          
                          })
        return lines            
        
    
    def get_tax_amount(self,line,tax_id):
         for tax_amount_line in line.invoice_id.tax_line_ids:
             
             if tax_amount_line.tax_id.id==tax_id.id:
                 return tax_amount_line.amount
             else: 
                 return 0.0  
    
    def get_abatement(self):
        lines=[]
        for line in self.invoice_line_ids:
              for tax in line.invoice_line_tax_ids:
                   if tax.applicable_mrp and line.net_mrp > 0.0:
                      tax_amount=self.get_tax_amount(line,tax)
                      currency_name=self.currency_id.name
                      lang=self._context.get('lang')
                      lines.append({
                                'abatement':True,
                                'product':line.product_id.name,
                                'mrp':line.mrp_price,
                                'net_mrp':line.net_mrp,
                                'perc':line.abatement_perc,
                                'tax_rate': tax.amount,
                                'tax_amount':tax_amount,
                                'in_words':currency_to_text(tax_amount,currency_name,lang)
                              })
        return lines
        

class kts_account_move_report(models.Model):
    _inherit='account.move'
    
    @api.multi
    def to_print_journal_voucher(self):
           self.ensure_one()
           report_name= 'journal_voucher'
           report_name1='Journal Voucher'
           return do_print_setup(self, {'name':report_name1, 'model':'account.move','report_name':report_name},
                False,False)
    
    def get_move_lines(self):
        lines=[]
        debit=credit=0.0
        for line in self.line_ids:   
            debit+=line.debit
            credit+=line.credit
            lines.append({
                         'date':line.date,
                         'acc_code':line.account_id.code,
                         'name':line.name+', '+line.account_id.name,
                         'credit':line.credit,
                         'debit':line.debit, 
                         'total':'' 
                          })
        lines.append({'date':'',
                      'acc_code':'',
                      'name':'',
                      'total':'Total',
                      'debit':debit,
                      'credit':credit
                      })
        return lines                
        

class kts_report_purchase_order(models.Model):
    
    _inherit = "purchase.order"
    print_header=fields.Boolean('Print Header',default=True)  
    
    @api.constrains('order_line')
    @api.one
    def _check_lines(self):
        seen_line=[]
        for line in self.order_line:
            if not line.product_id in seen_line:
                seen_line.append(line.product_id)
            else:
                raise ValidationError(_('Please select one line for one product'))    
    @api.multi         
    def to_print_purchase_order(self):
        self.ensure_one()
        
        if self.state == 'purchase':
           report_name= 'purchase_order'
           name='Purchase Order'          
        elif self.state in ['draft','sent']:
            report_name= 'request_for_quotation'
            name='Request For Quotation'     
        return do_print_setup(self, {'name':name, 'model':'purchase.order','report_name':report_name},
                False,self.partner_id.id)
    
    def excise_cal(self):
        excise_amount=0.0
        for line in self.tax_line_ids:
            if line.tax_id.tax_category=='cenvat': 
                excise_amount+=line.amount    
        if excise_amount<0.0:
            return 0.0
        else:
            return (excise_amount) 
    def subtotal_excise(self):
        excise_amount=0.0
        for line in self.tax_line_ids:
            if line.tax_id.tax_category=='cenvat':
                excise_amount+=line.amount    
        if excise_amount<0:
            return 0.0
        else:
            return (excise_amount+self.amount_untaxed) 
    
    def cal_rate(self,tax_type):
        for line in self.tax_line_ids:
            if line.tax_id.tax_category=='cenvat' and tax_type=='cenvat':
                return '@'+str(line.tax_id.amount)
            elif line.tax_id.tax_category!='cenvat' and tax_type=='mvat':
                name='VAT'+'@'+str(line.tax_id.amount) if line.tax_id.tax_category=='mvat' else 'CST' +'@'+str(line.tax_id.amount)
                return name
            
        return '' 
    def cst_vat_cal(self):
        cst_vat_amount=0.0
        for line in self.tax_line_ids:
            if line.tax_id.tax_category!='cenvat':
                cst_vat_amount+=line.amount    
        if cst_vat_amount<0.0:
            return 0.0
        else:
            return cst_vat_amount 
    
         
    def dispatch_policy(self):
        if self.picking_policy=='direct':
            dispatch_policy='Deliver each product when available'
        else:
            dispatch_policy='Deliver all products at once'
    def print_packing_charges(self):
        packing_charges=self.packing_charges if ( self.packing_charges_type =='fixed' or self.packing_charges_type =='variable') else 0.0
       
        if self.packing_charges_type =='variable':
            packing_charges=round(self.amount_untaxed * packing_charges/100.0) 
        return packing_charges
    
    def print_freight_charges(self):
        freight_charges=self.freight_charges if ( self.freight_charges_type =='fixed' or self.freight_charges_type =='variable') else 0.0
        if self.freight_charges_type =='variable':
            freight_charges=round(self.amount_untaxed*freight_charges/100.0)   
        return freight_charges    
    
    
    def get_move_lines(self):
        lines=[]
        i=0
        for line in self.order_line:
              i+=1
              
              lines.append({
                            'sr_no':i,
                            'code':line.product_id.default_code,
                            'product':line.product_id.name,
                            'qty':line.product_qty,
                            'price':line.price_unit,
                            'discount':line.discount,
                            'uom':line.product_uom.name,
                            'net_price':line.price_subtotal,
                            'delivery_date':line.supplier_schedule_date,
                            })
        return lines
            


        
        
             
    