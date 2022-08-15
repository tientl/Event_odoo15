odoo.define('documents.component.PdfGroupName', function (require) {
'use strict';

const { useRef, useState } = owl.hooks;

class PdfGroupName extends owl.Component {

    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.state = useState({
            edit: false,
        });
        // used to get the value of the input when renaming.
        this.nameInputRef = useRef('nameInput');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBlur() {
        this.trigger('edit-name', {
            groupId: this.props.groupId,
            name: this.nameInputRef.el.value,
        });
        this.state.edit = false;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGroupName(ev) {
        ev.stopPropagation();
        this.state.edit = true;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onKeyDown(ev) {
        if (ev.code !== "Enter") {
            return;
        }
        ev.stopPropagation();
        this.trigger('edit-name', {
            groupId: this.props.groupId,
            name: this.nameInputRef.el.value,
        });
        this.state.edit = false;
    }
}

PdfGroupName.props = {
    groupId: String,
    name: String,
};

PdfGroupName.template = 'documents.component.PdfGroupName';

return PdfGroupName;

});
