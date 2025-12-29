# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StudentStudent(models.Model):
    _inherit = 'student.student'

    library_member_id = fields.Many2one(
        comodel_name='library.member',
        string='Library Member',
        readonly=True,
        help='Linked library member record'
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

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create library member when student is created"""
        students = super().create(vals_list)
        for student in students:
            if not student.library_member_id:
                student._create_library_member()
        return students

    def write(self, vals):
        """Update library member when student info changes"""
        res = super().write(vals)
        
        # Fields that should sync to library member
        sync_fields = ['name', 'email', 'mobile', 'street', 'street2', 
                      'zip', 'city', 'state_id', 'country_id']
        
        if any(field in vals for field in sync_fields):
            for student in self:
                if student.library_member_id:
                    student._sync_to_library_member()
        
        return res

    def _create_library_member(self):
        """Create library member record for student"""
        self.ensure_one()
        
        member_vals = {
            'name': self.name,
            'email': self.email,
            'phone': self.mobile,
            'address': self._get_full_address(),
            'membership_date': fields.Date.today(),
            'membership_type': 'student',
            'photo': self.student_image,
        }
        
        member = self.env['library.member'].create(member_vals)
        self.library_member_id = member.id
        
        return member

    def _sync_to_library_member(self):
        """Sync student data to library member"""
        self.ensure_one()
        
        if not self.library_member_id:
            return
        
        self.library_member_id.write({
            'name': self.name,
            'email': self.email,
            'phone': self.mobile,
            'address': self._get_full_address(),
            'photo': self.student_image,
        })

    def _get_full_address(self):
        """Get formatted address"""
        self.ensure_one()
        parts = [
            self.street,
            self.street2,
            self.city,
            self.state_id.name if self.state_id else '',
            self.country_id.name if self.country_id else '',
            self.zip
        ]
        return ', '.join(filter(None, parts))

    def action_view_library_member(self):
        """Open library member record"""
        self.ensure_one()
        
        if not self.library_member_id:
            self._create_library_member()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Library Member'),
            'res_model': 'library.member',
            'res_id': self.library_member_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_borrowings(self):
        """View student's library borrowings"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Borrowings'),
            'res_model': 'library.borrowing',
            'view_mode': 'list,form,calendar',
            'domain': [('member_id', '=', self.library_member_id.id)],
            'context': {'default_member_id': self.library_member_id.id},
        }

    def action_view_library_fines(self):
        """View student's library fines"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Library Fines'),
            'res_model': 'library.fine',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.library_member_id.id)],
            'context': {'default_member_id': self.library_member_id.id},
        }