# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo.addons.website_event.tests.common import TestEventOnlineCommon


class TestTrackPush(TestEventOnlineCommon):
    def test_track_push(self):
        """" Test 'Send Push to Attendees' action and verify that it correctly
        targets all visitors that are registered to the event """

        registered_parent = self.env['website.visitor'].create({
            'name': 'Registered Parent',
            'push_token': 'AAAAA1',
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        })

        registered_visitors = self.env['website.visitor'].create([{
            'name': 'Registered Visitor',
            'push_token': 'BBBBB',
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }, {
            'name': 'Registered Child',
            'push_token': 'AAAAA2',
            # This one is the child of 'registered_parent' and should also be in results
            # Typically happens when a visitor connects with multiple browsers
            'parent_id': registered_parent.id,
            'active': False,
        }])
        registered_visitors |= registered_parent

        # unregistered attendee that should not appear in results
        self.env['website.visitor'].create({
            'name': 'Unregistered Visitor',
            'push_token': 'CCCCC',
        })

        action = self.event_0.action_send_push()
        social_post = self.env['social.post'] \
            .with_context(action.get('context', {})) \
            .create({'message': 'Hello Attendees!'})

        targeted_visitors = self.env['website.visitor'].search(literal_eval(social_post.visitor_domain))
        self.assertEqual(registered_visitors, targeted_visitors)
