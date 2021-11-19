/** @odoo-module alias=documents_spreadsheet.SpreadsheetComponent */

import { _t } from "web.core";
import Dialog from "web.OwlDialog";
import { useSetupAction } from "@web/webclient/actions/action_hook";

import PivotDialog from "documents_spreadsheet.PivotDialog";
import { jsonToBase64 } from "../o_spreadsheet/helpers/pivot_helpers";
import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";
import CachedRPC from "../o_spreadsheet/helpers/cached_rpc";
import { DEFAULT_LINES_NUMBER } from "../o_spreadsheet/constants";
import { useService } from "@web/core/utils/hooks";
import { legacyRPC } from "../o_spreadsheet/helpers/helpers";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

const { Spreadsheet, Model } = spreadsheet;
const { useState, useRef, useSubEnv, useExternalListener } = owl.hooks;

export default class SpreadsheetComponent extends owl.Component {
    constructor(parent, props) {
        super(...arguments);
        this.orm = useService("orm");
        const rpc = legacyRPC(this.orm);
        this.cacheRPC = new CachedRPC(rpc);
        const user = useService("user");
        this.ui = useService("ui");
        useSubEnv({
            newSpreadsheet: this.newSpreadsheet.bind(this),
            saveAsTemplate: this._saveAsTemplate.bind(this),
            makeCopy: this.makeCopy.bind(this),
            openPivotDialog: this.openPivotDialog.bind(this),
            download: this._download.bind(this),
            delayedRPC: this.cacheRPC.delayedRPC.bind(this.cacheRPC),
            getLinesNumber: this._getLinesNumber.bind(this),
        });
        useSetupAction({
            beforeLeave: this._onLeave.bind(this),
        });
        this.state = useState({
            dialog: {
                isDisplayed: false,
                title: undefined,
                isEditText: false,
                inputContent: undefined,
                isEditInteger: false,
                inputIntegerContent: undefined,
            },
            pivotDialog: {
                isDisplayed: false,
            },
        });
        this.spreadsheet = useRef("spreadsheet");
        this.dialogContent = undefined;
        this.pivot = undefined;
        this.insertPivotValueCallback = undefined;
        this.confirmDialog = () => true;
        this.data = props.data;
        this.stateUpdateMessages = props.stateUpdateMessages;
        this.client = {
            id: uuidGenerator.uuidv4(),
            name: user.name,
            userId: user.uid,
        };
        this.isReadonly = props.isReadonly;
        this.transportService = this.props.transportService;
        useExternalListener(window, "beforeunload", this._onLeave.bind(this));
    }

    get model() {
        return this.spreadsheet.comp.model;
    }

    mounted() {
        this.model.on("update", this, () =>
            this.trigger("spreadsheet-sync-status", {
                synced: this.model.getters.isFullySynchronized(),
                numberOfConnectedUsers: this.getConnectedUsers(),
            })
        );
        if (this.props.showFormulas) {
            this.model.dispatch("SET_FORMULA_VISIBILITY", { show: true });
        }
        if (this.props.initCallback) {
            this.props.initCallback(this.model);
        }
        if (this.props.download) {
            this._download();
        }
    }
    /**
     * Return the number of connected users. If one user has more than
     * one open tab, it's only counted once.
     * @return {number}
     */
    getConnectedUsers() {
        return new Set(
            [...this.model.getters.getConnectedClients().values()].map((client) => client.userId)
        ).size;
    }

    willUnmount() {
        this._onLeave();
    }
    /**
     * Open a dialog to ask a confirmation to the user.
     *
     * @param {CustomEvent} ev
     * @param {string} ev.detail.content Content to display
     * @param {Function} ev.detail.confirm Callback if the user press 'Confirm'
     */
    askConfirmation(ev) {
        this.dialogContent = ev.detail.content;
        this.confirmDialog = () => {
            ev.detail.confirm();
            this.closeDialog();
        };
        this.state.dialog.isDisplayed = true;
    }

    editText(ev) {
        this.dialogContent = undefined;
        this.state.dialog.title = ev.detail.title && ev.detail.title.toString();
        this.state.dialog.isEditText = true;
        this.state.inputContent = ev.detail.placeholder;
        this.confirmDialog = () => {
            this.closeDialog();
            ev.detail.callback(this.state.inputContent);
        };
        this.state.dialog.isDisplayed = true;
    }
    _getLinesNumber(callback) {
        this.dialogContent = _t("Select the number of records to insert");
        this.state.dialog.title = _t("Re-insert list");
        this.state.dialog.isEditInteger = true;
        this.state.dialog.inputIntegerContent = DEFAULT_LINES_NUMBER;
        this.confirmDialog = () => {
            this.closeDialog();
            callback(this.state.dialog.inputIntegerContent);
        };
        this.state.dialog.isDisplayed = true;
    }
    /**
     * Close the dialog.
     */
    closeDialog() {
        this.dialogContent = undefined;
        this.confirmDialog = () => true;
        this.state.dialog.title = undefined;
        this.state.dialog.isDisplayed = false;
        this.state.dialog.isEditText = false;
        this.state.dialog.isEditInteger = false;
        this.spreadsheet.comp.focusGrid();
    }
    /**
     * Close the pivot dialog.
     */
    closePivotDialog() {
        this.state.pivotDialog.isDisplayed = false;
        this.spreadsheet.comp.focusGrid();
    }
    /**
     * Insert a value of the spreadsheet using the callbackfunction;
     */
    _onCellClicked(ev) {
        this.insertPivotValueCallback(ev.detail.formula);
        this.closePivotDialog();
    }
    /**
     * Retrieve the spreadsheet_data and the thumbnail associated to the
     * current spreadsheet
     */
    getSaveData() {
        const data = this.spreadsheet.comp.model.exportData();
        return {
            data,
            revisionId: data.revisionId,
            thumbnail: this.getThumbnail(),
        };
    }
    getMissingValueDialogTitle() {
        const title = _t("Insert pivot cell");
        const pivotTitle = this.getPivotTitle();
        if (pivotTitle) {
            return `${title} - ${pivotTitle}`;
        }
        return title;
    }

    getPivotTitle() {
        if (this.pivotId) {
            return this.model.getters.getPivotDisplayName(this.pivotId);
        }
        return "";
    }
    getThumbnail() {
        const dimensions = spreadsheet.SPREADSHEET_DIMENSIONS;
        const canvas = this.spreadsheet.comp.grid.comp.canvas.el;
        const canvasResizer = document.createElement("canvas");
        const size = this.props.thumbnailSize;
        canvasResizer.width = size;
        canvasResizer.height = size;
        const canvasCtx = canvasResizer.getContext("2d");
        // use only 25 first rows in thumbnail
        const sourceSize = Math.min(
            25 * dimensions.DEFAULT_CELL_HEIGHT,
            canvas.width,
            canvas.height
        );
        canvasCtx.drawImage(
            canvas,
            dimensions.HEADER_WIDTH - 1,
            dimensions.HEADER_HEIGHT - 1,
            sourceSize,
            sourceSize,
            0,
            0,
            size,
            size
        );
        return canvasResizer.toDataURL().replace("data:image/png;base64,", "");
    }
    /**
     * Make a copy of the current document
     */
    makeCopy() {
        const { data, thumbnail } = this.getSaveData();
        this.trigger("make-copy", {
            data,
            thumbnail,
        });
    }
    /**
     * Create a new spreadsheet
     */
    newSpreadsheet() {
        this.trigger("new-spreadsheet");
    }

    /**
     * Downloads the spreadsheet in xlsx format
     */
    async _download() {
        this.ui.block();
        try {
            const { files } = await this.spreadsheet.comp.env.exportXLSX();
            this.trigger("download", {
                name: this.props.name,
                files,
            });
        } finally {
            this.ui.unblock();
        }
    }

    /**
     * @private
     * @returns {Promise}
     */
    async _saveAsTemplate() {
        const model = new Model(this.spreadsheet.comp.model.exportData(), {
            mode: "headless",
            evalContext: { env: this.env },
        });
        await model.waitForIdle();
        model.dispatch("CONVERT_PIVOT_TO_TEMPLATE");
        const data = model.exportData();
        const name = this.props.name;
        this.trigger("do-action", {
            action: "documents_spreadsheet.save_spreadsheet_template_action",
            options: {
                additional_context: {
                    default_template_name: `${name} - Template`,
                    default_data: jsonToBase64(data),
                    default_thumbnail: this.getThumbnail(),
                },
            },
        });
    }
    /**
     * Open a dialog to display a message to the user.
     *
     * @param {CustomEvent} ev
     * @param {string} ev.detail.content Content to display
     */
    notifyUser(ev) {
        this.dialogContent = ev.detail.content;
        this.confirmDialog = this.closeDialog;
        this.state.dialog.isDisplayed = true;
    }

    openPivotDialog(ev) {
        this.pivotId = ev.pivotId;
        this.insertPivotValueCallback = ev.insertPivotValueCallback;
        this.state.pivotDialog.isDisplayed = true;
    }
    _onLeave() {
        if (this.alreadyLeft) {
            return;
        }
        this.alreadyLeft = true;
        this.spreadsheet.comp.model.off("update", this);
        if (!this.isReadonly){
            this.trigger("spreadsheet-saved", this.getSaveData());
        }
    }
}

SpreadsheetComponent.template = "documents_spreadsheet.SpreadsheetComponent";
SpreadsheetComponent.components = { Spreadsheet, Dialog, PivotDialog };
Spreadsheet._t = _t;
SpreadsheetComponent.props = {
    name: String,
    data: Object,
    thumbnailSize: Number,
    isReadonly: Boolean,
    snapshotRequested: Boolean,
    showFormulas: Boolean,
    download: Boolean,
    stateUpdateMessages: Array,
    initCallback: {
        optional: true,
        type: Function,
    },
    transportService: {
        optional: true,
        type: Object
    }
}
SpreadsheetComponent.defaultProps = {
    isReadonly: false,
    download: false,
    snapshotRequested: false,
    showFormulas: false,
    stateUpdateMessages: [],
}
