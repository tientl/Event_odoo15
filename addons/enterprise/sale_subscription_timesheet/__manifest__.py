# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Subscription and Timesheet',
    'summary': 'Synchronize data between timesheet and subscriptions',
    'description': """This module ensure that data (such as analytic accounts) defined on the sale order via timesheet app are correctly set also on subscriptions""",
    'category': 'Sales/Subscription',
    'depends': [
        'sale_subscription',
        'sale_timesheet',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
