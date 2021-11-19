odoo.define('timesheet_grid.TimerStartComponent', function (require) {
    "use strict";

    class TimerStartComponent extends owl.Component {

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        get letter() {
            if (this.props.runningIndex !== this.props.index && this.props.index < 26) {
                const from = this.props.addTimeMode ? 65 : 97;
                return String.fromCharCode(from + this.props.index);
            } else {
                return '';
            }
        }
        get iconClass() {
            if (this.props.runningIndex === this.props.index) {
                return 'fa fa-play primary-green';
            } else if (this.props.index < 26) {
                return '';
            } else if (this.props.addTimeMode) {
                return 'fa fa-plus';
            } else {
                return 'fa fa-play';
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickTimer(ev) {
            ev.stopPropagation();
            this.trigger('timer-started-from-line', this.props.path);
        }
    }
    TimerStartComponent.template = 'timesheet_grid.start_timer';
    TimerStartComponent.props = {
        path: String,
        index: {
            type: Number,
            optional: true
        },
        runningIndex: {
            type: Number,
            optional: true
        },
        addTimeMode: Boolean
    };

    return TimerStartComponent;
});
