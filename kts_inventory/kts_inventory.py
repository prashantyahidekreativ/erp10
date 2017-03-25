from odoo import models, fields, api,_
from odoo import exceptions, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp
import odoo
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_compare, float_is_zero
from odoo.tools.translate import _
from odoo import tools, SUPERUSER_ID
from odoo.exceptions import UserError, AccessError
import re
import time
         
class kts_stock(models.Model):
    _inherit='stock.pack.operation'
    qty_received = fields.Integer('Quantity Received',default=0)
    autoserial_lot_gen = fields.Boolean(related='product_id.product_tmpl_id.serialno', store=True)
    expiry_date=fields.Date('Expiry Date')
    
    @api.multi
    def autogen_expiry_date(self):
        self.ensure_one()
        if self.pack_lot_ids:
           if self.expiry_date:
              for line in self.pack_lot_ids:
                   line.write({'expiry_date':self.expiry_date}) 
           else:
               raise UserError(_('Please Selection Expiry Date'))
        else:
            raise UserError(_('Please first Genrate serial Nos'))
    
    @api.onchange('qty_done')
    def onchange_qty_done(self):
        if self.qty_done > 1.0:
            if self.qty_done > self.product_qty:
                return{'value':{'qty_done':0.0},
                       'warning':{'title':'UserError', 'message':'Product qty done is greater than product  qty!'}   
                       }        
    
    @api.multi
    def do_reopen_form(self):
        self.ensure_one()
        data_obj = self.env['ir.model.data']
        view = data_obj.xmlid_to_res_id('stock.view_pack_operation_lot_form')
        
        return { 'type': 'ir.actions.act_window', 
                'res_model':self._name, 
                'res_id':self.id, 
                'view_type':'form', 
                'view_mode': 'form', 
                'views': [(view, 'form')],
                'view_id': view,
                'target': 'new',
                'context': self._context 
                 }
       
    @api.multi
    def autogen_serialno(self):
        self.ensure_one()
        val={}
        lot_ids=False
        self.qty_done = sum([x.qty for x in self.pack_lot_ids])
        if self.qty_received and self.product_qty >= self.qty_done and self.qty_received+self.qty_done <= self.product_qty:
            if self.product_id.serialno:
               if self.product_id.serial_sequence:
                   serial_sequence = self.product_id.serial_sequence.code
               else:
                   serial_sequence='kts.serial.no'
               spolot_obj=self.pack_lot_ids.browse([])
               for i in range(0,self.qty_received):
                   val.update({
                         'lot_name':self.env['ir.sequence'].next_by_code(serial_sequence),      
                        })
                   self.pack_lot_ids+=spolot_obj.create(val)
                   self.qty_done +=1  
               return self.do_reopen_form()
            
            else:
                raise UserError(_('Product is not serial Tracker'))
     
        else:
            raise UserError(_('Quantity are done with producing serial number'))
    
    @api.multi
    def autogen_lotno(self):
        self.ensure_one()
        val={}
        lot_ids=False
        self.qty_done = sum([x.qty for x in self.pack_lot_ids])
        if self.qty_received and self.product_qty >= self.qty_done and self.qty_received+self.qty_done <= self.product_qty:
            if self.product_id.serialno:
               spolot_obj=self.pack_lot_ids.browse([])
               val.update({
                         'lot_name':self.env['ir.sequence'].next_by_code('kts.serial.no'),     
                         'qty':self.qty_received,
                        })
               self.pack_lot_ids+=spolot_obj.new(val)
               self.qty_done = self.qty_received  
               return self.do_reopen_form()
            
            else:
                raise UserError(_('Product is not  Tracker'))
     
        else:
            raise UserError(_('Quantity are done with producing lot number number'))
    
    @api.multi
    def do_partial_plus(self):
        self.ensure_one()
        if self.product_qty >= self.qty_done and self.qty_received <= (self.product_qty-self.qty_done):   
           lines=self.pack_lot_ids.search([('qty','=',0),('operation_id','=',self.id)])   
           i=self.qty_received
           for j,line in map(None,range(1,i+1),lines):
                if j:
                      line.do_plus()
           self.write({'qty_received':0})
           return self.do_reopen_form()
        else:
            raise UserError(_('Partial Done is Error due to qty to process check is wrong Process'))

    
    @api.multi
    def do_all_plus(self):
        self.ensure_one()
        pack_lot_obj=self.env['stock.pack.operation.lot']
        if self.product_qty >0.0 and self.qty_done <= 0.0:
           line=self.pack_lot_ids
           for line in self.pack_lot_ids:
                 line.do_plus()
           return self.do_reopen_form()
        else:
            raise UserError(_('All Done is already Process'))

class kts_stock_pack_operation_lot(models.Model):
    _inherit='stock.pack.operation.lot'
    vendor_serial_no=fields.Char('Vendor Serial No')
    expiry_date=fields.Date('Expiry Date')
           
class kts_stock_production_lot(models.Model):
    _inherit='stock.production.lot'
    vendor_serial_no=fields.Char('Vendor Serial No')
                
class kts_inventory_stock_picking(models.Model):
    _inherit='stock.picking'
    grn_no=fields.Char(string='GRN NO',readonly=True)
    transporter_name = fields.Char(string='Transporter Name')
    chalan_no = fields.Char(string='Chalan No')
    
    state = fields.Selection([
        ('draft', 'Draft'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'), ('done', 'Done')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
             " * Waiting Availability: still waiting for the availability of products\n"
             " * Partially Available: some products are available and reserved\n"
             " * Ready to Transfer: products reserved, simply waiting for confirmation.\n"
             " * Transferred: has been processed, can't be modified or cancelled anymore\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore")
 
    
    @api.depends('move_type', 'launch_pack_operations', 'move_lines.state', 'move_lines.picking_id', 'move_lines.partially_available')
    @api.one
    def _compute_state(self):
        ret = super(kts_inventory_stock_picking, self)._compute_state()
        if self.state=='done' and self.picking_type_id.code=='incoming':       
              self.write({'grn_no':self.env['ir.sequence'].next_by_code('kts.grn.no')}) 
        return ret
    
        
        
        
    def _create_lots_for_picking(self):
        Lot = self.env['stock.production.lot']
        for pack_op_lot in self.mapped('pack_operation_ids').mapped('pack_lot_ids'):
            if not pack_op_lot.lot_id:
                if pack_op_lot.expiry_date:
                    expiry_date= pack_op_lot.expiry_date+' '+'00:00:00'
                else:
                    expiry_date=pack_op_lot.expiry_date   
                lot = Lot.create({'name': pack_op_lot.lot_name, 'product_id': pack_op_lot.operation_id.product_id.id,'vendor_serial_no':pack_op_lot.vendor_serial_no,'life_date':expiry_date})
                
                pack_op_lot.write({'lot_id': lot.id})
        # TDE FIXME: this should not be done here
        self.mapped('pack_operation_ids').mapped('pack_lot_ids').filtered(lambda op_lot: op_lot.qty == 0.0).unlink()
    create_lots_for_picking = _create_lots_for_picking

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        # TDE note: o2o conversion, todo multi
        backorders = self.env['stock.picking']
        for picking in self:
            backorder_moves = backorder_moves or picking.move_lines
            if self._context.get('do_only_split'):
                not_done_bo_moves = backorder_moves.filtered(lambda move: move.id not in self._context.get('split', []))
            else:
                not_done_bo_moves = backorder_moves.filtered(lambda move: move.state not in ('done', 'cancel'))
            if not not_done_bo_moves:
                continue
            backorder_picking = picking.copy({
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
                'transporter_name':'',
                'chalan_no':''
            })
            picking.message_post(body=_("Back order <em>%s</em> <b>created</b>.") % (backorder_picking.name))
            not_done_bo_moves.write({'picking_id': backorder_picking.id})
            if not picking.date_done:
                picking.write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            backorder_picking.action_confirm()
            backorder_picking.action_assign()
            backorders |= backorder_picking
        return backorders



