# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.bus.controllers.main import BusController

from typing import List

BUS_CHANNEL_NAME = "spreadsheet_collaborative_session_"


class SpreadsheetCollaborationController(BusController):

    # ---------------------------
    # Extends BUS Controller Poll
    # ---------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = self._add_spreadsheet_collaborative_bus_channels(request.env, channels)
        return super()._poll(dbname, channels, last, options)

    @staticmethod
    def _add_spreadsheet_collaborative_bus_channels(env, channels):
        """Add collaborative bus channels for active spreadsheets.

        Listening to channel "spreadsheet_collaborative_session_{document_id}"
        tells the server the spreadsheet is active. But only users with read access
        can actually read the associate bus messages.
        We manually add the channel if the user has read access.
        This channel is used to safely send messages to allowed users.

        :param channels: bus channels
        :return: channels
        """
        active_spreadsheet_ids = SpreadsheetCollaborationController._get_active_spreadsheet_ids(channels)
        if active_spreadsheet_ids:
            channels = list(channels)
            # The following search ensures that the user has the correct access rights
            spreadsheets = (
                env["documents.document"].with_context(active_test=False)
                .search([("id", "in", active_spreadsheet_ids)])
            )
            channels.extend(spreadsheet for spreadsheet in spreadsheets)
        return channels

    @staticmethod
    def _get_active_spreadsheet_ids(channels: List[str]) -> List[int]:
        """Return which spreadsheet are active from the subscription bus channels.
        A spreadsheet is active if someone polls on the channel:
        `spreadsheet_collaborative_session_{document_id}`
        """
        external_channels = [
            channel
            for channel in channels
            if isinstance(channel, str) and channel.startswith(BUS_CHANNEL_NAME)
        ]
        if not external_channels:
            return []
        spreadsheet_session_ids = (
            channel.replace(BUS_CHANNEL_NAME, "") for channel in external_channels
        )
        return [
            int(spreadsheet_id)
            for spreadsheet_id in spreadsheet_session_ids
            if spreadsheet_id.isdigit()
        ]
