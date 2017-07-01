from openerp import models, fields, api, _
from lxml import etree
from openerp.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
class kts_company_master(models.Model):
    _inherit='res.company'
    report_template_ids=fields.One2many('kts.report.template','company_id',string='Report Template')
    
    
class kts_report_template(models.Model):    
    _name='kts.report.template'
    
    @api.model
    def _referencable_models(self):
        models=self.env['res.request.link'].search([])
        return [(x.object, x.name) for x in models]
    
    def _get_state(self):
        state=[]
        state.append(('sale','Sale Order'),)
        state.append(('open','Invoice open'),)
        state.append(('post','Payment Post'),)
        state.append(('done','Delivery or receipt'),)
        state.append(('draft','Draft'),)
        state.append(('purchase','Purchase Order'),)
        return state
    
    name=fields.Char('Name')
    note=fields.Text('Note')
    model_id=fields.Selection(_referencable_models,string='Reference Document')
    state=fields.Selection(_get_state,string='State')
    partner=fields.Selection([('out_invoice','Customer'),('in_invoice','Supplier'),('out_refund','Credit Note'),('in_refund','Debit Note')],string='Partner')
    company_id=fields.Many2one('res.company','Company')
    print_no=fields.Integer('Sequence of print',default=0)
    