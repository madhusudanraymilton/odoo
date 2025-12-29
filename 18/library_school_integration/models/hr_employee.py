# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    library_member_id = fields.Many2one(
        comodel_name='library.member',
        string='Library Member',
        readonly=True,
        help='Linked library member record'
    )
    is_library_member = fields.Boolean(
        string='Library Member',
        compute='_compute_is_library_member',
        store=True
    )
    can_borrow_books = fields.Boolean(
        related='library_member_id.can_borrow',
        string='Can Borrow Books',
        store=True
    )
    active_borrowings_count = fields.Integer(
        related='library_member_id.active_borrowings',
        string='Active Borrowings'
    )
    total_books_borrowed_count = fields.Integer(
        related='library_member_id.total_books_borrowed',
        string='Total Books Borrowed'
    )
    unpaid_library_fines = fields.Float(
        related='library_member_id.unpaid_fine_amount',
        string='Unpaid Library Fines'
    )

    @api.depends('library_member_id')
    def _compute_is_library_member(self):
        """Compute if employee is a library member"""
        for employee in self:
            employee.is_library_member = bool(employee.library_member_id)

    def action_create_library_member(self):
        """Create library member for teacher"""
        self.ensure_one()
        
        if self.library_member_id:
            raise UserError(_('This employee is already a library member.'))
        
        if not self.is_teacher:
            raise UserError(_('Only teachers can be added as library members.'))
        
        member_vals = {
            'name': self.name,
            'email': self.work_email or self.private_email,
            'phone': self.mobile_phone or self.work_phone,
            'address': self._get_full_address(),
            'membership_date': fields.Date.today(),
            'membership_type': 'teacher',
            'photo': self.image_1024,
        }
        
        member = self.env['library.member'].create(member_vals)
        self.library_member_id = member.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Library member created successfully for %s') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_remove_library_member(self):
        """Remove library member access"""
        self.ensure_one()
        
        if not self.library_member_id:
            raise UserError(_('This employee is not a library member.'))
        
        if self.library_member_id.active_borrowings > 0:
            raise UserError(_('Cannot remove library member with active borrowings.'))
        
        member = self.library_member_id
        self.library_member_id = False
        member.active = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Library member access removed for %s') % self.name,
                'type': 'warning',
                'sticky': False,
            }
        }

    def _get_full_address(self):
        """Get formatted address"""
        self.ensure_one()
        parts = [
            self.address_home_id.street if self.address_home_id else '',
            self.address_home_id.street2 if self.address_home_id else '',
            self.address_home_id.city if self.address_home_id else '',
            self.address_home_id.state_id.name if self.address_home_id and self.address_home_id.state_id else '',
            self.address_home_id.country_id.name if self.address_home_id and self.address_home_id.country_id else '',
            self.address_home_id.zip if self.address_home_id else '',
        ]
        return ', '.join(filter(None, parts))

    def action_view_library_member(self):
        """Open library member record"""
        self.ensure_one()
        
        if not self.library_member_id:
            raise UserError(_('This employee is not a library member.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Library Member'),
            'res_model': 'library.member',
            'res_id': self.library_member_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_borrowings(self):
        """View teacher's library borrowings"""
        self.ensure_one()
        
        if not self.library_member_id:
            raise UserError(_('This employee is not a library member.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Borrowings'),
            'res_model': 'library.borrowing',
            'view_mode': 'list,form,calendar',
            'domain': [('member_id', '=', self.library_member_id.id)],
            'context': {'default_member_id': self.library_member_id.id},
        }

    def action_view_library_fines(self):
        """View teacher's library fines"""
        self.ensure_one()
        
        if not self.library_member_id:
            raise UserError(_('This employee is not a library member.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Library Fines'),
            'res_model': 'library.fine',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.library_member_id.id)],
            'context': {'default_member_id': self.library_member_id.id},
        }

    def write(self, vals):
        """Sync data to library member when employee info changes"""
        res = super().write(vals)
        
        sync_fields = ['name', 'work_email', 'private_email', 'mobile_phone', 
                      'work_phone', 'image_1024', 'address_home_id']
        
        if any(field in vals for field in sync_fields):
            for employee in self.filtered('library_member_id'):
                employee._sync_to_library_member()
        
        return res

    def _sync_to_library_member(self):
        """Sync employee data to library member"""
        self.ensure_one()
        
        if not self.library_member_id:
            return
        
        self.library_member_id.write({
            'name': self.name,
            'email': self.work_email or self.private_email,
            'phone': self.mobile_phone or self.work_phone,
            'address': self._get_full_address(),
            'photo': self.image_1024,
        })