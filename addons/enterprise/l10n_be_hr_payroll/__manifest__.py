# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll',
    'icon': '/l10n_be/static/description/icon.png',
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'hr_contract_reports', 'hr_work_entry_holidays', 'hr_payroll_holidays'],
    'version': '1.0',
    'description': """
Belgian Payroll Rules.
======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Leaves Management
    * Salary Maj, ONSS, Withholding Tax, Child Allowance, ...
    """,

    'data': [
        'security/ir.model.access.csv',
        'security/l10n_be_hr_payroll_security.xml',
        'data/report_paperformat.xml',
        'views/report_payslip_template.xml',
        'views/reports.xml',
        'wizard/hr_payroll_employee_departure_notice_views.xml',
        'wizard/hr_payroll_employee_departure_holiday_attest_views.xml',
        'wizard/hr_payroll_generate_warrant_payslips_views.xml',
        'wizard/l10n_be_hr_payroll_schedule_change_wizard_views.xml',
        'wizard/hr_payroll_allocating_paid_time_off_views.xml',
        'views/l10n_be_double_pay_recovery_line_views.xml',
        'views/l10n_be_meal_voucher_report_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
        'views/hr_work_entry_views.xml',
        'views/report_termination_fees.xml',
        'views/report_termination_holidays.xml',
        'views/hr_dmfa_template.xml',
        'views/hr_dmfa_views.xml',
        'views/hr_departure_reason_views.xml',
        'views/273S_xml_export_template.xml',
        'views/281_10_xml_export_template.xml',
        'views/281_45_xml_export_template.xml',
        'views/withholding_tax_xml_export_template.xml',
        'views/hr_job_views.xml',
        'data/res_partner_data.xml',
        'data/contract_type_data.xml',
        'data/ir_default_data.xml',
        'data/resource_calendar_data.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_leave_type_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_rule_parameters_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/hr_departure_reason_data.xml',
        'data/cp200/employee_double_holidays_data.xml',
        'data/cp200/employee_pfi_data.xml',
        'data/cp200/employee_salary_data.xml',
        'data/cp200/employee_termination_fees_data.xml',
        'data/cp200/employee_termination_holidays_N1_data.xml',
        'data/cp200/employee_termination_holidays_N_data.xml',
        'data/cp200/employee_thirteen_month_data.xml',
        'data/cp200/employee_warrant_salary_data.xml',
        'data/student/student_regular_pay_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'wizard/l10n_be_individual_account_wizard_views.xml',
        'views/l10n_be_281_10_views.xml',
        'views/l10n_be_281_45_views.xml',
        'report/hr_individual_account_templates.xml',
        'report/hr_contract_employee_report_views.xml',
        'report/hr_281_10_templates.xml',
        'report/hr_281_45_templates.xml',
        'report/hr_contract_history_report_views.xml',
        'report/l10n_be_hr_payroll_274_XX_sheet_template.xml',
        'report/l10n_be_hr_payroll_273S_pdf_template.xml',
        'wizard/l10n_be_social_balance_sheet_views.xml',
        'report/l10n_be_social_balance_report_template.xml',
        'wizard/l10n_be_social_security_certificate_views.xml',
        'report/l10n_be_social_security_certificate_report_template.xml',
        'views/l10n_be_273S_views.xml',
        'views/l10n_be_274_XX_views.xml',
        'wizard/l10n_be_eco_vouchers_wizard_views.xml',
        'wizard/l10n_be_double_pay_recovery_wizard_views.xml',
        'wizard/l10n_be_hr_payroll_employee_lang_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'demo':[
        'data/l10n_be_hr_payroll_demo.xml'
    ],
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'l10n_be_hr_payroll/static/src/js/**/*',
        ],
        'web.assets_qweb': [
            'l10n_be_hr_payroll/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
