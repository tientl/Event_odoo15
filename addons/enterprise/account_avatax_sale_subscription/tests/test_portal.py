# coding: utf-8
import contextlib
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.addons.account_avatax_sale_subscription.controllers.portal import SaleSubscriptionAvatax, PaymentPortalAvatax
from odoo.addons.website.tools import MockRequest
from odoo.tools import mute_logger

from .test_sale_subscription import TestSaleSubscriptionAvalaraCommon
from .mocked_subscription_response import generate_response


@contextlib.contextmanager
def WebsiteSaleSubMockRequest(*args, **kwargs):
    class Response:
        def __init__(self, qcontext):
            self.qcontext = qcontext

    qcontext = kwargs.pop('qcontext')
    with MockRequest(*args, **kwargs) as request:
        request.uid = 1
        request.render = lambda self, _: Response(qcontext)
        yield request


@tagged("-at_install", "post_install")
class TestWebsiteSaleSubscriptionAvatax(TestSaleSubscriptionAvalaraCommon):
    @mute_logger('odoo.http')
    def test_01_portal_avatax_called(self):
        controller = SaleSubscriptionAvatax()
        with WebsiteSaleSubMockRequest(self.env, qcontext={'account': self.subscription}), \
             self._capture_request({'lines': [], 'summary': []}) as capture:
            controller.subscription(self.subscription.id)

        self.assertEqual(
            capture.val and capture.val['json']['referenceCode'],
            self.subscription.name,
            'Should have queried avatax for the right taxes on the SO.'
        )

    def test_02_portal_transaction_creation(self):
        controller = PaymentPortalAvatax()

        with WebsiteSaleSubMockRequest(self.env, qcontext={'account': self.subscription}), \
             self._capture_request(return_value={'lines': [], 'summary': []}) as capture, \
             patch('odoo.addons.account_avatax.models.account_move.AccountMove.button_update_avatax') as mocked_button_update_avatax_on_inv:

            # Without this hasattr(..., '_ondelete') returns True and
            # the ORM adds this function to the _ondelete methods of
            # account.move. It causes the ORM to call the mocked
            # button_update_avatax when subscription_transaction()
            # unlinks the created invoice and thus causes a "false"
            # passing test. Deleting it here causes hasattr to return
            # False.
            del mocked_button_update_avatax_on_inv._ondelete

            processing_vals = controller.subscription_transaction(
                self.subscription.id,
                self.subscription.uuid,

                # kwargs for _create_transaction
                flow="redirect",
                payment_option_id=self.acquirer.id,
                landing_route="/dummy",
            )

            mocked_button_update_avatax_on_inv.assert_called()
