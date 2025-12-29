# -*- coding: utf-8 -*-
{
    'name': 'Library School Integration',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Integration between Library Management and School Management',
    'description': """
Library School Integration
==========================
This module integrates Library Management with School Management:
* Students automatically become library members
* Teachers can be added as library staff
* Synchronized data between both systems
* Automatic member creation for students
* Teacher-specific library permissions
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'library_management',
        'wk_school_management',
    ],
    'data': [
        # Views
        'views/student_student_views.xml',
        'views/hr_employee_views.xml',
        'views/library_member_views.xml',
        
        # Menu
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}