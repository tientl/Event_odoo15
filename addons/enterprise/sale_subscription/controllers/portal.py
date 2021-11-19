# -*- coding: utf-8 -*-
import datetime
import werkzeug
from collections import OrderedDict
from dateutil.relativedelta import relativedelta

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.translate import _

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import get_records_pager, pager as portal_pager


class CustomerPortal(portal.CustomerPortal):

    def _get_subscription_domain(self, partner):
        return [
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
        ]

    def _prepare_home_portal_values(self, counters):
        """ Add subscription details to main account page """
        values = super()._prepare_home_portal_values(counters)
        if 'subscription_count' in counters:
            partner = request.env.user.partner_id
            values['subscription_count'] = (
                request.env['sale.subscription'].search_count(self._get_subscription_domain(partner))
                if request.env['sale.subscription'].check_access_rights('read', raise_exception=False)
                else 0
            )
        return values

    @http.route(['/my/subscription', '/my/subscription/page/<int:page>'], type='http', auth="user", website=True)
    def my_subscription(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleSubscription = request.env['sale.subscription']

        domain = self._get_subscription_domain(partner)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'stage_id': {'label': _('Status'), 'order': 'stage_id asc, to_renew desc, id desc'}
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'open': {'label': _('In Progress'), 'domain': [('stage_category', '=', 'progress')]},
            'pending': {'label': _('To Renew'), 'domain': [('to_renew', '=', True)]},
            'close': {'label': _('Closed'), 'domain': [('stage_category', '=', 'closed')]},
        }

        # default sort by value
        if not sortby:
            sortby = 'stage_id'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # pager
        account_count = SaleSubscription.sudo().search_count(domain)
        pager = portal_pager(
            url="/my/subscription",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=account_count,
            page=page,
            step=self._items_per_page
        )
        accounts = SaleSubscription.sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_subscriptions_history'] = accounts.ids[:100]

        values.update({
            'accounts': accounts,
            'page_name': 'subscription',
            'pager': pager,
            'default_url': '/my/subscription',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("sale_subscription.portal_my_subscriptions", values)


class SaleSubscription(http.Controller):

    @http.route(
        ['/my/subscription/<int:subscription_id>',
         '/my/subscription/<int:subscription_id>/<string:access_token>'],
        type='http', methods=['GET'], auth='public', website=True
    )
    def subscription(self, subscription_id, access_token='', message='', message_class='', **kw):
        logged_in = not request.env.user.sudo()._is_public()
        Subscription = request.env['sale.subscription']
        if access_token or not logged_in:
            subscription = Subscription.sudo().browse(subscription_id).exists()
            if access_token != subscription.uuid:
                raise werkzeug.exceptions.NotFound()
            if request.uid == subscription.partner_id.user_id.id:
                subscription = Subscription.browse(subscription_id).exists()
        else:
            subscription = Subscription.browse(subscription_id).exists()
        if not subscription:
            return request.redirect('/my')

        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            subscription.company_id.id,
            subscription.partner_id.id,
            currency_id=subscription.currency_id.id,
            force_tokenization=True,
            is_validation=not subscription.to_renew,
        )  # In sudo mode to read the fields of acquirers and partner (if not logged in)
        # The tokens are filtered based on the partner hierarchy to allow managing tokens of any
        # sibling partners. As a result, a partner can manage any token belonging to partners of its
        # own company from a subscription.
        tokens = request.env['payment.token'].search([
            ('acquirer_id', 'in', acquirers_sudo.ids),
            ('partner_id', 'child_of', subscription.partner_id.commercial_partner_id.id),
        ]) if logged_in else request.env['payment.token']
        fees_by_acquirer = {
            acquirer: acquirer._compute_fees(
                subscription.recurring_total_incl,
                subscription.currency_id,
                subscription.partner_id.country_id
            ) for acquirer in acquirers_sudo.filtered('fees_active')
        }
        active_plan_sudo = subscription.template_id.sudo()
        display_close = active_plan_sudo.user_closable and subscription.stage_category == 'progress'
        is_follower = request.env.user.partner_id in subscription.message_follower_ids.partner_id
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        if subscription.recurring_rule_type != 'weekly':
            rel_period = relativedelta(datetime.datetime.today(), subscription.recurring_next_date)
            missing_periods = getattr(rel_period, periods[subscription.recurring_rule_type]) + 1
        else:
            delta = datetime.date.today() - subscription.recurring_next_date
            missing_periods = delta.days / 7
        action = request.env.ref('sale_subscription.sale_subscription_action')
        values = {
            'account': subscription,
            'template': subscription.template_id.sudo(),
            'display_close': display_close,
            'is_follower': is_follower,
            'close_reasons': request.env['sale.subscription.close.reason'].search([]),
            'missing_periods': missing_periods,
            'payment_mode': active_plan_sudo.payment_mode,
            'user': request.env.user,
            'is_salesman': request.env.user.has_group('sales_team.group_sale_salesman'),
            'action': action,
            'message': message,
            'message_class': message_class,
            'pricelist': subscription.pricelist_id.sudo(),
        }
        payment_values = {
            'acquirers': acquirers_sudo,
            'tokens': tokens,
            'default_token_id': subscription.payment_token_id.id,
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': False,  # Tokenization is always performed for subscriptions
            'amount': None,  # Determined by the generated invoice
            'currency': subscription.pricelist_id.currency_id,
            'partner_id': subscription.partner_id.id,
            'access_token': subscription.uuid,
            'transaction_route': f'/my/subscription/transaction/{subscription.id}'
            # Operation-dependent values are defined in the view
        }
        values.update(payment_values)

        history = request.session.get('my_subscriptions_history', [])
        values.update(get_records_pager(history, subscription))

        return request.render("sale_subscription.subscription", values)

    @http.route(['/my/subscription/<int:account_id>/close'], type='http', methods=["POST"], auth="public", website=True)
    def close_account(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise werkzeug.exceptions.NotFound()
        else:
            account = account_res.browse(account_id)

        if account.sudo().template_id.user_closable:
            close_reason = request.env['sale.subscription.close.reason'].browse(int(kw.get('close_reason_id')))
            account.close_reason_id = close_reason
            if kw.get('closing_text'):
                account.message_post(body=_('Closing text: %s', kw.get('closing_text')))
            account.set_close()
            account.date = datetime.date.today().strftime('%Y-%m-%d')
        return request.redirect('/my/home')


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route('/my/subscription/transaction/<int:subscription_id>', type='json', auth='public')
    def subscription_transaction(
        self, subscription_id, access_token, is_validation=False, **kwargs
    ):
        """ Create a draft transaction and return its processing values.

        :param int subscription_id: The subscription for which a transaction is made, as a
                                    `sale.subscription` id
        :param str access_token: The UUID of the subscription used to authenticate the partner
        :param bool is_validation: Whether the operation is a validation
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the subscription id or the access token is invalid
        """
        Subscription = request.env['sale.subscription']
        user = request.env.user
        if user._is_public():  # The user is not logged in
            Subscription = Subscription.sudo()
        subscription = Subscription.browse(subscription_id).exists()

        # Check the access token against the subscription uuid
        # The fields of the subscription are accessed in sudo mode in case the user is logged but
        # has no read access on the record.
        if not subscription or access_token != subscription.sudo().uuid:
            raise ValidationError("The subscription id or the access token is invalid.")

        kwargs.update(partner_id=subscription.partner_id.id)
        kwargs.pop('custom_create_values', None)  # Don't allow passing arbitrary create values
        common_callback_values = {
            'callback_model_id': request.env['ir.model']._get_id(subscription._name),
            'callback_res_id': subscription.id,
        }
        if not is_validation:  # Renewal transaction
            # Create an invoice to compute the total amount with tax, and the currency
            invoice_values = subscription.sudo().with_context(lang=subscription.partner_id.lang) \
                ._prepare_invoice()  # In sudo mode to read on account.fiscal.position fields
            invoice_sudo = request.env['account.move'].sudo().create(invoice_values)
            kwargs.update({
                'reference_prefix': subscription.code,  # There is no sub_id field to rely on
                'amount': invoice_sudo.amount_total,
                'currency_id': invoice_sudo.currency_id.id,
                'tokenization_requested': True,  # Renewal transactions are always tokenized
            })

            # Delete the invoice to avoid bloating the DB with draft invoices. It is re-created on
            # the fly in the callback when the payment is confirmed.
            invoice_sudo.unlink()

            # Create the transaction. The `invoice_ids` field is populated later with the final inv.
            tx_sudo = self._create_transaction(
                custom_create_values={
                    **common_callback_values,
                    'callback_method': '_reconcile_and_assign_token',
                },
                is_validation=is_validation,
                **kwargs
            )
        else:  # Validation transaction
            kwargs['reference_prefix'] = payment_utils.singularize_reference_prefix(
                prefix='validation'  # Validation transactions use their own reference prefix
            )
            tx_sudo = self._create_transaction(
                custom_create_values={
                    **common_callback_values,
                    'callback_method': '_assign_token',
                },
                is_validation=is_validation,
                **kwargs
            )

        return tx_sudo._get_processing_values()

    @http.route('/my/subscription/assign_token/<int:subscription_id>', type='json', auth='user')
    def subscription_assign_token(self, subscription_id, token_id):
        """ Assign a token to a subscription.

        :param int subscription_id: The subscription to which the token must be assigned, as a
                                    `sale.subscription` id
        :param int token_id: The token to assign, as a `payment.token` id
        :return: None
        """
        subscription = request.env['sale.subscription'].browse(subscription_id)
        new_token = request.env['payment.token'].browse(int(token_id))
        subscription.payment_token_id = new_token
