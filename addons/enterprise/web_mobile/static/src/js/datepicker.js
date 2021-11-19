odoo.define("web_mobile.datepicker", function (require) {
    "use strict";

    const config = require("web.config");
    const mobile = require("web_mobile.core");
    const web_datepicker = require("web.datepicker");
    const Widget = require("web.Widget");

    /**
     * Override odoo date-picker (bootstrap date-picker) to display mobile native
     * date picker. Because of it is better to show native mobile date-picker to
     * improve usability of Application (Due to Mobile users are used to native
     * date picker).
     */
    web_datepicker.DateWidget.include({
        /**
         * @override
         */
        start() {
            if (!mobile.methods.requestDateTimePicker || (this.type_of_date === 'datetime' && config.device.isIOS)) {
                return this._super(...arguments);
            }
            this.$input = this.$("input.o_datepicker_input");
            // forcefully removes the library's classname to "disable" library's event listeners
            this.$input.removeClass('datetimepicker-input')
            this._setupMobilePicker();
        },

        /**
         * Bootstrap date-picker already destroyed at initialization
         *
         * @override
         */
        destroy() {
            if (!mobile.methods.requestDateTimePicker || (this.type_of_date === 'datetime' && config.device.isIOS)) {
                return this._super(...arguments);
            }
            Widget.prototype.destroy.apply(this, arguments);
        },

        /**
         * @override
         */
        maxDate() {
            if (!mobile.methods.requestDateTimePicker || (this.type_of_date === 'datetime' && config.device.isIOS)) {
                return this._super(...arguments);
            }
            console.warn("Unsupported in the mobile applications");
        },

        /**
         * @override
         */
        minDate() {
            if (!mobile.methods.requestDateTimePicker || (this.type_of_date === 'datetime' && config.device.isIOS)) {
                return this._super(...arguments);
            }
            console.warn("Unsupported in the mobile applications");
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @override
         * @private
         */
        _setLibInputValue() {
            if (!mobile.methods.requestDateTimePicker || (this.type_of_date === 'datetime' && config.device.isIOS)) {
                return this._super(...arguments);
            }
        },

        /**
         * @private
         */
        _setupMobilePicker() {
            this.$el.on("click", async () => {
                const { data } = await mobile.methods.requestDateTimePicker({
                    value: this.getValue() ? this.getValue().format("YYYY-MM-DD HH:mm:ss") : false,
                    type: this.type_of_date,
                    ignore_timezone: true,
                });
                this.$input.val(data);
                this.changeDatetime();
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        _onInputClicked: function () {
            if (!mobile.methods.requestDateTimePicker || (this.type_of_date === 'datetime' && config.device.isIOS)) {
                return this._super(...arguments);
            }
        },
    });
});
