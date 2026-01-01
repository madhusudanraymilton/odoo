# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryFine(models.Model):
    _name = 'library.fine'
    _description = 'Library Fine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'created_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    borrowing_id = fields.Many2one(
        comodel_name='library.borrowing',
        string='Borrowing',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )
    member_id = fields.Many2one(
        comodel_name='library.member',
        string='Member',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )
    book_id = fields.Many2one(
        related='borrowing_id.book_id',
        string='Book',
        readonly=True,
        store=True
    )
    fine_amount = fields.Float(
        string='Fine Amount',
        required=True,
        tracking=True,
        digits='Product Price'
    )
    fine_reason = fields.Text(
        string='Reason',
        tracking=True,
        required=True
    )
    payment_status = fields.Selection(
        selection=[
            ('unpaid', 'Unpaid'),
            ('paid', 'Paid'),
        ],
        string='Payment Status',
        default='unpaid',
        required=True,
        tracking=True,
        index=True
    )
    payment_date = fields.Date(
        string='Payment Date',
        tracking=True,
        store=True,
        # CHANGED: Removed required=True - payment_date should only be required when paid
    )
    created_date = fields.Date(
        string='Created Date',
        default=fields.Date.today,
        required=True,
        readonly=True,
        index=True
    )
    notes = fields.Text(
        string='Notes'
    )
    color = fields.Integer(
        string='Color Index',
        compute='_compute_color'
    )

    # CHANGED: Modified to return domain for borrowing_id dropdown
    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Clear borrowing_id when member changes and set domain for overdue borrowings"""
        if not self.member_id:
            self.borrowing_id = False
            # CHANGED: Return empty domain when no member selected
            return {'domain': {'borrowing_id': [('id', '=', False)]}}
        
        # CHANGED: Clear borrowing_id to force reselection
        self.borrowing_id = False
        
        # CHANGED: Set domain to show only this member's overdue borrowings
        domain = [
            ('member_id', '=', self.member_id.id),
            ('status', '=', 'borrowed'),
            ('due_date', '<', fields.Date.today()),  # Actually overdue
        ]
        
        return {'domain': {'borrowing_id': domain}}

    # CHANGED: Complete rewrite - now only handles auto-fill when borrowing is selected
    @api.onchange('borrowing_id')
    def _onchange_borrowing_id(self):
        """Auto-fill fine details when a borrowing record is selected"""
        if not self.borrowing_id:
            # CHANGED: Clear fields when borrowing is unselected
            self.fine_amount = 0.0
            self.fine_reason = False
            self.notes = False
            return
        
        borrowing = self.borrowing_id
        
        # CHANGED: Verify the selected borrowing is actually overdue
        if borrowing.status != 'borrowed':
            return {
                'warning': {
                    'title': _('Invalid Borrowing'),
                    'message': _('The selected borrowing is not in borrowed status.')
                }
            }
        
        # CHANGED: Check if actually overdue using computed field or date comparison
        if hasattr(borrowing, 'days_overdue'):
            if borrowing.days_overdue <= 0:
                return {
                    'warning': {
                        'title': _('Not Overdue'),
                        'message': _('The selected borrowing is not overdue yet.')
                    }
                }
        elif borrowing.due_date >= fields.Date.today():
            return {
                'warning': {
                    'title': _('Not Overdue'),
                    'message': _('The selected borrowing is not overdue yet.')
                }
            }
        
        # CHANGED: Auto-fill member_id from borrowing (in case it wasn't set)
        self.member_id = borrowing.member_id
        
        # CHANGED: Auto-fill fine amount from borrowing's computed fine
        self.fine_amount = borrowing.fine_amount if hasattr(borrowing, 'fine_amount') else 0.0
        
        # CHANGED: Generate descriptive fine reason
        days_overdue = borrowing.days_overdue if hasattr(borrowing, 'days_overdue') else 0
        self.fine_reason = _('Overdue fine for book "%s" (%d days late)') % (
            borrowing.book_id.title, 
            days_overdue
        )
        
        # CHANGED: Generate detailed notes
        self.notes = _(
            'Borrow Date: %s\n'
            'Due Date: %s\n'
            'Return Date: %s\n'
            'Days Overdue: %d'
        ) % (
            borrowing.borrow_date,
            borrowing.due_date,
            borrowing.return_date or '-',
            days_overdue
        )

    @api.constrains('borrowing_id', 'member_id')
    def _check_borrowing_member(self):
        for fine in self:
            if fine.borrowing_id and fine.borrowing_id.member_id != fine.member_id:
                raise ValidationError(_('Borrowing does not belong to selected member.'))

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('library.fine') or _('New')
        return super().create(vals)

    def _compute_color(self):
        """Compute color for kanban view"""
        for fine in self:
            if fine.payment_status == 'paid':
                fine.color = 10  # Green
            else:
                fine.color = 1  # Red

    @api.constrains('fine_amount')
    def _check_fine_amount(self):
        """Validate fine amount is positive"""
        for fine in self:
            if fine.fine_amount <= 0:
                raise ValidationError(_('Fine amount must be greater than zero.'))

    def action_mark_as_paid(self):
        """Mark fine as paid"""
        for fine in self:
            if fine.payment_status == 'paid':
                raise ValidationError(_('This fine is already marked as paid.'))

            fine.write({
                'payment_status': 'paid',
                'payment_date': fields.Date.today()
            })

            # Send payment confirmation email
            template = self.env.ref('library_management.email_template_fine_payment_confirmation',
                                    raise_if_not_found=False)
            if template:
                template.send_mail(fine.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Fine marked as paid successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }
    def action_send_payment_reminder(self):
        """Send payment reminder to member"""
        self.ensure_one()
        template = self.env.ref('library_management.email_template_fine_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment reminder sent to %s') % self.member_id.name,
                'type': 'success',
                'sticky': False,
            }
        }