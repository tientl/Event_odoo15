odoo.define('web_enterprise.ControlPanel', function (require) {
    "use strict";

    const ControlPanel = require('web.ControlPanel');
    const { device } = require('web.config');
    const { patch } = require('web.utils');

    const { Portal } = owl.misc;
    const { useState } = owl.hooks;
    const STICKY_CLASS = 'o_mobile_sticky';

    if (!device.isMobile) {
        return;
    }

    /**
     * Control panel: mobile layout
     *
     * This patch handles the scrolling behaviour of the control panel in a mobile
     * environment: the panel sticks to the top of the window when scrolling into
     * the view. It is revealed when scrolling up and hiding when scrolling down.
     * The panel's position is reset to default when at the top of the view.
     */
    patch(ControlPanel.prototype, 'web_enterprise.ControlPanel', {
        setup() {
            this._super(...arguments);
            this.state = useState({
                showSearchBar: false,
                showMobileSearch: false,
                showViewSwitcher: false,
            });
        },

        mounted() {
            // Bind additional events
            this.onWindowClick = this._onWindowClick.bind(this);
            this.onWindowScroll = this._onScrollThrottled.bind(this);
            window.addEventListener('click', this.onWindowClick);
            document.addEventListener('scroll', this.onWindowScroll);

            this.oldScrollTop = 0;
            this.initialScrollTop = document.documentElement.scrollTop;
            this.el.style.top = '0px';

            this._super(...arguments);
        },

        willUnmount() {
            window.removeEventListener('click', this.onWindowClick);
            document.removeEventListener('scroll', this.onWindowScroll);
        },

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Get today's date (number).
         * @private
         * @returns {number}
         */
        _getToday() {
            return new Date().getDate();
        },

        /**
         * Reset mobile search state
         * @private
         */
        _resetSearchState() {
            Object.assign(this.state, {
                showSearchBar: false,
                showMobileSearch: false,
                showViewSwitcher: false,
            });
        },

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * Show or hide the control panel on the top screen.
         * The function is throttled to avoid refreshing the scroll position more
         * often than necessary.
         * @private
         */
        _onScrollThrottled() {
            if (this.isScrolling) {
                return;
            }
            this.isScrolling = true;
            requestAnimationFrame(() => this.isScrolling = false);

            const scrollTop = document.documentElement.scrollTop;
            const delta = Math.round(scrollTop - this.oldScrollTop);

            if (scrollTop > this.initialScrollTop) {
                // Beneath initial position => sticky display
                const elRect = this.el.getBoundingClientRect();
                this.el.classList.add(STICKY_CLASS);
                this.el.style.top = delta < 0 ?
                    // Going up
                    `${Math.min(0, elRect.top - delta)}px` :
                    // Going down | not moving
                    `${Math.max(-elRect.height, elRect.top - delta)}px`;
            } else {
                // Above intial position => standard display
                this.el.classList.remove(STICKY_CLASS);
            }

            this.oldScrollTop = scrollTop;
        },

        /**
         * Reset mobile search state on switch view.
         * @private
         */
        _onSwitchView() {
            this._resetSearchState();
        },

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onWindowClick(ev) {
            if (
                this.state.showViewSwitcher &&
                !ev.target.closest('.o_cp_switch_buttons')
            ) {
                this.state.showViewSwitcher = false;
            }
        },
    });

    patch(ControlPanel, 'web_enterprise.ControlPanel', {
        template: 'web_enterprise._ControlPanel',
        components: {
            ...ControlPanel.components,
            Portal,
        },
    });
});
