# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class LibraryMember(models.Model):
    _inherit = 'library.member'

    student_id = fields.Many2one(
        comodel_name='student.student',
        string='Related Student',
        readonly=True,
        help='Link to student record if member is a student'
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Related Employee',
        readonly=True,
        help='Link to employee record if member is a teacher'
    )
    grade_id = fields.Many2one(
        related='student_id.current_grade_id',
        string='Current Grade',
        store=True
    )
    enrollment_id = fields.Many2one(
        related='student_id.current_enrollment_id',
        string='Current Enrollment',
        store=True
    )
    is_teacher = fields.Boolean(
        related='employee_id.is_teacher',
        string='Is Teacher',
        store=True
    )
    school_id = fields.Many2one(
        comodel_name='res.company',
        string='School',
        compute='_compute_school_id',
        store=True
    )

    @api.depends('student_id.company_id', 'employee_id.company_id')
    def _compute_school_id(self):
        """Compute school from student or employee"""
        for member in self:
            if member.student_id:
                member.school_id = member.student_id.company_id
            elif member.employee_id:
                member.school_id = member.employee_id.company_id
            else:
                member.school_id = False

    def action_view_student(self):
        """View related student record"""
        self.ensure_one()
        
        if not self.student_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('This member is not linked to a student'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Student'),
            'res_model': 'student.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_employee(self):
        """View related employee record"""
        self.ensure_one()
        
        if not self.employee_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('This member is not linked to an employee'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        """Override to prevent duplicate creation from integration"""
        # Check if creating from student
        if self._context.get('from_student_integration'):
            student_id = vals.get('student_id')
            if student_id:
                existing = self.search([('student_id', '=', student_id)], limit=1)
                if existing:
                    return existing
        
        # Check if creating from employee
        if self._context.get('from_employee_integration'):
            employee_id = vals.get('employee_id')
            if employee_id:
                existing = self.search([('employee_id', '=', employee_id)], limit=1)
                if existing:
                    return existing
        
        return super().create(vals)