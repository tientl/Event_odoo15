# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, date_utils
from odoo.tools.misc import format_date

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    def button_validate(self):
        super(AccountBankStatement, self).button_validate()
        for statement in self:
            for line in statement.line_ids:
                if line.partner_id and line.online_partner_information:
                    # write value for account and merchant on partner only if partner has no value, in case value are different write False
                    value_merchant = line.partner_id.online_partner_information or line.online_partner_information
                    value_merchant = value_merchant if value_merchant == line.online_partner_information else False
                    line.partner_id.online_partner_information = value_merchant

    @api.model
    def _online_sync_bank_statement(self, transactions, online_account):
        """
         build a bank statement from a list of transaction and post messages is also post in the online_account of the journal.
         :param transactions: A list of transactions that will be created in the new bank statement.
             The format is : [{
                 'id': online id,                  (unique ID for the transaction)
                 'date': transaction date,         (The date of the transaction)
                 'name': transaction description,  (The description)
                 'amount': transaction amount,     (The amount of the transaction. Negative for debit, positive for credit)
                 'online_partner_information': optional field used to store information on the statement line under the
                    online_partner_information field (typically information coming from plaid/yodlee). This is use to find partner
                    for next statements
             }, ...]
         :param online_account: The online account for this statement
         Return: The number of imported transaction for the journal
        """
        line_to_reconcile = self.env['account.bank.statement.line']
        for journal in online_account.journal_ids:
            # Since the synchronization succeeded, set it as the bank_statements_source of the journal
            journal.sudo().write({'bank_statements_source': 'online_sync'})
            if not transactions:
                continue

            transactions_identifiers = [line['online_transaction_identifier'] for line in transactions]
            existing_transactions_ids = self.env['account.bank.statement.line'].search([('online_transaction_identifier', 'in', transactions_identifiers), ('journal_id', '=', journal.id)])
            existing_transactions = [t.online_transaction_identifier for t in existing_transactions_ids]

            transactions_partner_information = []
            for transaction in transactions:
                transaction['date'] = fields.Date.from_string(transaction['date'])
                if transaction.get('online_partner_information'):
                    transactions_partner_information.append(transaction['online_partner_information'])

            if transactions_partner_information:
                self._cr.execute("""
                    SELECT p.online_partner_information, p.id FROM res_partner p
                    WHERE p.online_partner_information IN %s AND p.company_id = %s
                """, [tuple(transactions_partner_information), journal.company_id.id])
                partner_id_per_information = dict(self._cr.fetchall())
            else:
                partner_id_per_information = {}

            sorted_transactions = sorted(transactions, key=lambda l: l['date'])
            min_date = date_utils.start_of(sorted_transactions[0]['date'], 'month')
            if journal.bank_statement_creation_groupby == 'week':
                # key is not always the first of month
                weekday = min_date.weekday()
                min_date = date_utils.subtract(min_date, days=weekday)
            max_date = sorted_transactions[-1]['date']
            total = sum([t['amount'] for t in sorted_transactions])

            statements_in_range = self.search([('date', '>=', min_date), ('journal_id', '=', journal.id)])

            # For first synchronization, an opening bank statement is created to fill the missing bank statements
            all_statement = self.search_count([('journal_id', '=', journal.id)])
            digits_rounding_precision = journal.currency_id.rounding if journal.currency_id else journal.company_id.currency_id.rounding
            # If there are neither statement and the ending balance != 0, we create an opening bank statement
            if all_statement == 0 and not float_is_zero(online_account.balance - total, precision_rounding=digits_rounding_precision):
                opening_transaction = [(0, 0, {
                    'date': date_utils.subtract(min_date, days=1),
                    'payment_ref': _("Opening statement: first synchronization"),
                    'amount': online_account.balance - total,
                })]
                op_stmt = self.create({
                    'date': date_utils.subtract(min_date, days=1),
                    'line_ids': opening_transaction,
                    'journal_id': journal.id,
                    'balance_end_real': online_account.balance - total,
                })
                op_stmt.button_post()
                line_to_reconcile += op_stmt.mapped('line_ids')

            transactions_in_statements = []
            statement_to_recompute = self.env['account.bank.statement']
            transactions_to_create = {}

            for transaction in sorted_transactions:
                if transaction['online_transaction_identifier'] in existing_transactions:
                    continue # Do nothing if the transaction already exists
                line = transaction.copy()
                line['online_account_id'] = online_account.id
                if journal.bank_statement_creation_groupby == 'day':
                    # key is full date
                    key = transaction['date']
                elif journal.bank_statement_creation_groupby == 'week':
                    # key is first day of the week
                    weekday = transaction['date'].weekday()
                    key = date_utils.subtract(transaction['date'], days=weekday)
                elif journal.bank_statement_creation_groupby == 'bimonthly':
                    if transaction['date'].day >= 15:
                        # key is the 15 of that month
                        key = transaction['date'].replace(day=15)
                    else:
                        # key if the first of the month
                        key = date_utils.start_of(transaction['date'], 'month')
                    # key is year-month-0 or year-month-1
                elif journal.bank_statement_creation_groupby == 'month':
                    # key is first of the month
                    key = date_utils.start_of(transaction['date'], 'month')
                else:
                    # key is last date of transactions fetched
                    key = max_date

                # Find partner id if exists
                if line.get('online_partner_information'):
                    partner_info = line['online_partner_information']
                    if partner_id_per_information.get(partner_info):
                        line['partner_id'] = partner_id_per_information[partner_info]

                # Decide if we have to update an existing statement or create a new one with this line
                stmt = statements_in_range.filtered(lambda x: x.date == key)
                if stmt:
                    line['statement_id'] = stmt[0].id
                    transactions_in_statements.append(line)
                    statement_to_recompute += stmt[0]
                else:
                    if not transactions_to_create.get(key):
                        transactions_to_create[key] = []
                    transactions_to_create[key].append((0, 0, line))

            # Create the lines that should be inside an existing bank statement and reset those stmt in draft
            if transactions_in_statements:
                statement_to_recompute.write({'state': 'open'})
                line_to_reconcile += self.env['account.bank.statement.line'].create(transactions_in_statements)
                # Recompute the balance_end_real of the first statement where we added line
                # because adding line don't trigger a recompute and balance_end_real is not updated.
                # We only trigger the recompute on the first element of the list as it is the one
                # the most in the past and this will trigger the recompute of all the statements
                # that are next.
                statement_to_recompute[0]._compute_ending_balance()
                # Since the balance end real of the latest statement is not recomputed, we will
                # have a problem as balance_end_real and computed balance won't be the same and therefore
                # we will have an error while trying to post the entries. To prevent that error,
                # we force the balance_end_real of the latest statement to be the same as the computed
                # balance. Balance_end_real will be changed at the end of this method to match
                # the real balance of the account anyway so this is no big deal.
                statement_to_recompute[-1].balance_end_real = statement_to_recompute[-1].balance_end
                # Post the statement back
                statement_to_recompute.button_post()

            # Create lines inside new bank statements
            created_stmts = self.env['account.bank.statement']
            for date, lines in transactions_to_create.items():
                # balance_start and balance_end_real will be computed automatically
                created_stmts += self.env['account.bank.statement'].create({
                    'date': date,
                    'line_ids': lines,
                    'journal_id': journal.id,
                })

            created_stmts.button_post()
            line_to_reconcile += created_stmts.mapped('line_ids')
            # write account balance on the last statement of the journal
            # That way if there are missing transactions, it will show in the last statement
            # and the day missing transactions are fetched or manually written, everything will be corrected
            last_bnk_stmt = self.search([('journal_id', '=', journal.id)], limit=1)
            if last_bnk_stmt and (created_stmts or transactions_in_statements):
                last_bnk_stmt.balance_end_real = online_account.balance
            # Set last sync date as the last transaction date
            journal.account_online_account_id.sudo().write({'last_sync': max_date})
        return line_to_reconcile


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    online_transaction_identifier = fields.Char("Online Transaction Identifier", readonly=True)
    online_partner_information = fields.Char(readonly=True)
    online_account_id = fields.Many2one(comodel_name='account.online.account', readonly=True)
    online_link_id = fields.Many2one(comodel_name='account.online.link', related='online_account_id.account_online_link_id', store=True, readonly=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    online_partner_information = fields.Char(readonly=True)
