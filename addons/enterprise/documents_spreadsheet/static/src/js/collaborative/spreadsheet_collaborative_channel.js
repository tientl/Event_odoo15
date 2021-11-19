/** @odoo-module alias=documents_spreadsheet.SpreadsheetCollaborativeChannel **/

/**
 * This class implements the `TransportService` interface defined
 * by o-spreadsheet. Its purpose is to communicate with other clients
 * by sending and receiving spreadsheet messages through the server.
 * @see https://github.com/odoo/o-spreadsheet
 *
 * It listens messages on the long polling bus and forwards spreadsheet messages
 * to the handler. (note: it is assumed there is only one handler)
 *
 * It uses the RPC protocol to send messages to the server which
 * push them in the long polling bus for other clients.
 */
export default class SpreadsheetCollaborativeChannel {
    /**
     * @param {Env} env
     * @param {number} documentId Id of the spreadsheet
     */
    constructor(env, documentId) {
        this.env = env;
        this._documentId = documentId;
        /**
         * A callback function called to handle messages when they are received.
         */
        this._listener;
        /**
         * Messages are queued while there is no listener. They are forwarded
         * once it registers.
         */
        this._queue = [];
        // Listening this channel tells the server the spreadsheet is active
        // but the server will actually push to channel [{dbname}, "spreadsheet", {documentId}]
        // The user can listen to this channel only if he has the required read access.
        this._channel = `spreadsheet_collaborative_session_${this._documentId}`;
        this.env.services.bus_service.addChannel(this._channel);
        this.env.services.bus_service.onNotification(this, (notifs) =>
            this._handleNotifications(this._filterSpreadsheetNotifs(notifs))
        );
    }

    /**
     * Register a function that is called whenever a new spreadsheet revision
     * message notification is received by server.
     *
     * @param {any} id
     * @param {Function} callback
     */
    onNewMessage(id, callback) {
        this._listener = callback;
        for (let message of this._queue) {
            callback(message);
        }
        this._queue = [];
    }

    /**
     * Send a message to the server
     *
     * @param {Object} message
     */
    sendMessage(message) {
        return this.env.services.rpc({
            model: "documents.document",
            method: "dispatch_spreadsheet_message",
            args: [this._documentId, message],
        }, { shadow: true });
    }

    /**
     * Stop listening new messages
     */
    leave() {
        this._listener = undefined;
    }

    /**
     * Filters the received messages to only handle the messages related to
     * spreadsheet
     *
     * @private
     * @param {Array} notifs
     *
     * @returns {Array} notifs which are related to spreadsheet
     */
    _filterSpreadsheetNotifs(notifs) {
        return notifs.filter((notification) => {
            const { payload, type } = notification;
            return type === 'spreadsheet' && payload.id === this._documentId;
        });
    }

    /**
     * Either forward the message to the listener if it's already registered,
     * or put it in a queue.
     *
     * @private
     * @param {Array} notifs
     */
    _handleNotifications(notifs) {
        for (const { payload } of notifs) {
            if (!this._listener) {
                this._queue.push(payload);
            } else {
                this._listener(payload);
            }
        }
    }
}
