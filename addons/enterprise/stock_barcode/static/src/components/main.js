/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import BarcodeQuantModel from '@stock_barcode/models/barcode_quant_model';
import config from 'web.config';
import core from 'web.core';
import GroupedLineComponent from '@stock_barcode/components/grouped_line';
import LineComponent from '@stock_barcode/components/line';
import LocationButton from '@stock_barcode/components/location_button';
import PackageLineComponent from '@stock_barcode/components/package_line';
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import ViewsWidget from '@stock_barcode/widgets/views_widget';
import ViewsWidgetAdapter from '@stock_barcode/components/views_widget_adapter';
import * as BarcodeScanner from '@web_enterprise/webclient/barcode/barcode_scanner';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { Component } = owl;
const { useSubEnv, useState } = owl.hooks;

/**
 * Main Component
 * Gather the line information.
 * Manage the scan and save process.
 */

class MainComponent extends Component {
    //--------------------------------------------------------------------------
    // Lifecycle
    //--------------------------------------------------------------------------

    setup() {
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.state = useState({
            displayDestinationSelection: false,
            displaySourceSelection: false,
            productPageOpened: false,
        });
        this.ViewsWidget = ViewsWidget;
        this.props.model = this.props.action.res_model;
        this.props.id = this.props.action.context.active_id;
        const model = this._getModel(this.props);
        useSubEnv({model});
        this._scrollBehavior = 'smooth';
        this.isMobile = config.device.isMobile;
    }

    async willStart() {
        const barcodeData = await this.rpc(
            '/stock_barcode/get_barcode_data',
            {
                model: this.props.model,
                res_id: this.props.id || false,
            }
        );
        this.groups = barcodeData.groups;
        this.env.model.setData(barcodeData);
        this.env.model.on('process-action', this, this._onDoAction);
        this.env.model.on('notification', this, this._onNotification);
        this.env.model.on('refresh', this, this._onRefreshState);
        this.env.model.on('update', this, this.render);
        this.env.model.on('do-action', this, args => this.trigger('do-action', args));
        this.env.model.on('history-back', this, () => this.trigger('history-back'));
    }

    mounted() {
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        this.el.addEventListener('edit-line', this._onEditLine.bind(this));
        this.el.addEventListener('exit', this.exit.bind(this));
        this.el.addEventListener('open-package', this._onOpenPackage.bind(this));
        this.el.addEventListener('refresh', this._onRefreshState.bind(this));
        this.el.addEventListener('warning', this._onWarning.bind(this));
    }

    willUnmount() {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get displayHeaderInfoAsColumn() {
        return this.env.model.isDone || this.env.model.isCancelled;
    }

    get currentPageIndex() {
        return this.env.model.pageIndex + 1;
    }

    get displayDestinationLocation() {
        return this.env.model.displayDestinationLocation;
    }

    get displayLocations() {
        return this.groups.group_stock_multi_locations && this.displayBarcodeLines;
    }

    get displaySourceLocation() {
        return this.env.model.displaySourceLocation;
    }

    get currentSourceLocation() {
        return this.env.model.location.display_name;
    }

    get sourceLocations() {
        return this.env.model.locationList;
    }

    get destinationLocations() {
        return this.env.model.destLocationList;
    }

    get currentDestinationLocation() {
        if (!this.env.model.destLocation) {
            return null;
        }
        return this.env.model.destLocation.display_name;
    }

    get displayBarcodeApplication() {
        return this.env.model.view === 'barcodeLines';
    }

    get displayBarcodeActions() {
        return this.env.model.view === 'actionsView';
    }

    get displayBarcodeLines() {
        return this.displayBarcodeApplication && this.env.model.canBeProcessed;
    }

    get displayInformation() {
        return this.env.model.view === 'infoFormView';
    }

    get displayNextButton() {
        return this.numberOfPages > 1 && this.currentPageIndex < this.numberOfPages;
    }

    get displayNote() {
        return !this._hideNote && this.env.model.record.note;
    }

    get displayPackageContent() {
        return this.env.model.view === 'packagePage';
    }

    get displayProductPage() {
        return this.env.model.view === 'productPage';
    }

    get highlightDestinationLocation() {
        return this.env.model.highlightDestinationLocation;
    }

    get highlightSourceLocation() {
        return this.env.model.highlightSourceLocation;
    }

    get highlightNextButton() {
        return this.env.model.highlightNextButton;
    }

    get highlightValidateButton() {
        return this.env.model.highlightValidateButton;
    }

    get info() {
        return this.env.model.barcodeInfo;
    }

    get informationParams() {
        return this.env.model.informationParams;
    }

    get isTransfer() {
        return this.currentSourceLocation && this.currentDestinationLocation;
    }

    get lines() {
        return this.env.model.groupedLines;
    }

    get mobileScanner() {
        return BarcodeScanner.isBarcodeScannerSupported();
    }

    get numberOfPages() {
        return this.env.model.pages.length;
    }

    async render() {
        await super.render(...arguments);
        if (!this.displayBarcodeLines) {
            this._scrollBehavior = 'auto';
            return;
        }
        let selectedLine = document.querySelector('.o_sublines .o_barcode_line.o_highlight');
        if (!selectedLine) {
            selectedLine = document.querySelector('.o_barcode_line.o_highlight');
        }
        if (selectedLine) {
            // If a line is selected, checks if this line is entirely visible
            // and if it's not, scrolls until the line is.
            const footer = document.querySelector('.fixed-bottom');
            const header = document.querySelector('.o_barcode_header');
            const lineRect = selectedLine.getBoundingClientRect();
            const navbar = document.querySelector('.o_main_navbar');
            // On mobile, overflow is on the html.
            const page = document.querySelector(this.isMobile ? 'html' : '.o_barcode_lines');
            // Computes the real header's height (the navbar is present if the page was refreshed).
            const headerHeight = navbar ? navbar.offsetHeight + header.offsetHeight : header.offsetHeight;
            let scrollCoordY = false;
            if (lineRect.top < headerHeight) {
                scrollCoordY = lineRect.top - headerHeight + page.scrollTop;
            } else if (lineRect.bottom > window.innerHeight - footer.offsetHeight) {
                const pageRect = page.getBoundingClientRect();
                scrollCoordY = page.scrollTop - (pageRect.bottom - lineRect.bottom);
                if (this.isMobile) {
                    // The footer can hide the line on mobile, we increase the scroll coord to avoid that.
                    scrollCoordY += footer.offsetHeight;
                }
            }
            if (scrollCoordY !== false) { // Scrolls to the line only if it's not entirely visible.
                page.scroll({ left: 0, top: scrollCoordY, behavior: this._scrollBehavior });
                this._scrollBehavior = 'smooth';
            }
        }
    }

    get packageLines() {
        return this.env.model.packageLines;
    }

    get viewsWidgetData() {
        const data = this.env.model.viewsWidgetData;
        data.params = this._editedLineParams;
        return data;
    }

    get viewsWidgetDataForPackage() {
        const params = {
            searchQuery: {
                domain: [['package_id', '=', this._inspectedPackageId]],
            },
        };
        return {
            model: 'stock.quant',
            view: 'stock_barcode.stock_quant_barcode_kanban',
            additionalContext: {},
            params,
            view_type: 'kanban'
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getModel(params) {
        if (params.model === 'stock.picking') {
            return new BarcodePickingModel(params);
        } else if (params.model === 'stock.quant') {
            return new BarcodeQuantModel(params);
        } else {
            throw new Error('No JS model define');
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    async cancel() {
        await this.env.model.save();
        const action = await this.orm.call(
            this.props.model,
            'action_cancel_from_barcode',
            [[this.props.id]]
        );
        const onClose = res => {
            if (res && res.cancelled) {
                this.env.model._cancelNotification();
                this.trigger('history-back');
            }
        };
        this.trigger('do-action', {
            action,
            options: {
                on_close: onClose.bind(this),
            },
        });
    }

    async openMobileScanner() {
        const barcode = await BarcodeScanner.scanBarcode();
        if (barcode) {
            this.env.model.processBarcode(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.env.services.notification.notify({
                type: 'warning',
                message: this.env._t("Please, Scan again !"),
            });
        }
    }

    closeProductPage() {
        this.toggleBarcodeLines();
    }

    async exit(ev) {
        if (this.displayBarcodeApplication) {
            await this.env.model.save();
            this.trigger('history-back');
        } else {
            this.toggleBarcodeLines();
        }
    }

    hideNote(ev) {
        this._hideNote = true;
        this.render();
    }

    nextPage(ev) {
        this.env.model.nextPage();
    }

    async openProductPage() {
        if (!this._editedLineParams) {
            await this.env.model.save();
        }
        this.env.model.displayProductPage();
    }

    previousPage(ev) {
        this.env.model.previousPage();
    }

    async print(action, method) {
        await this.env.model.save();
        const options = this.env.model._getPrintOptions();
        if (options.warning) {
            return this.env.model.notification.add(options.warning, { type: 'warning' });
        }
        if (!action && method) {
            action = await this.orm.call(
                this.props.model,
                method,
                [[this.props.id]]
            );
        }
        this.trigger('do-action', { action, options });
    }

    putInPack(ev) {
        ev.stopPropagation();
        this.env.model._putInPack();
    }

    toggleBarcodeActions(ev) {
        ev.stopPropagation();
        this.env.model.displayBarcodeActions();
    }

    toggleBarcodeLines(recordId) {
        this._editedLineParams = undefined;
        this.env.model.displayBarcodeLines(recordId);
    }

    async toggleInformation() {
        await this.env.model.save();
        this.env.model.displayInformation();
    }

    toggleDestinationSelection(ev) {
        ev.stopPropagation();
        this.state.displayDestinationSelection = !this.state.displayDestinationSelection;
        this.state.displaySourceSelection = false;
        document.addEventListener('click', () => {
            this.state.displayDestinationSelection = false;
        }, {once: true});
    }

    toggleSourceSelection(ev) {
        ev.stopPropagation();
        this.state.displaySourceSelection = !this.state.displaySourceSelection;
        this.state.displayDestinationSelection = false;
        document.addEventListener('click', () => {
            this.state.displaySourceSelection = false;
        }, {once: true});
    }

    /**
     * Calls `validate` on the model and then triggers up the action because OWL
     * components don't seem able to manage wizard without doing custom things.
     *
     * @param {OdooEvent} ev
     */
    async validate(ev) {
        ev.stopPropagation();
        await this.env.model.validate();
    }

    /**
     * Handler called when a barcode is scanned.
     *
     * @private
     * @param {string} barcode
     */
    _onBarcodeScanned(barcode) {
        if (this.displayBarcodeApplication) {
            this.env.model.processBarcode(barcode);
        }
    }

    async _onDoAction(ev) {
        this.trigger('do-action', {
            action: ev,
            options: {
                on_close: this._onRefreshState.bind(this),
            },
        });
    }

    async _onEditLine(ev) {
        let line = ev.detail.line;
        const virtualId = line.virtual_id;
        await this.env.model.save();
        // Updates the line id if it's missing, in order to open the line form view.
        if (!line.id && virtualId) {
            line = this.env.model.pageLines.find(l => Number(l.dummy_id) === virtualId);
        }
        this._editedLineParams = { currentId: line.id };
        await this.openProductPage();
    }

    _onNotification(notifParams) {
        const { message } = notifParams;
        delete notifParams.message;
        this.env.services.notification.add(message, notifParams);
    }

    _onOpenPackage(ev) {
        ev.stopPropagation();
        this._inspectedPackageId = ev.detail.packageId;
        this.env.model.displayPackagePage();
    }

    async _onRefreshState(ev) {
        const { recordId } = (ev && ev.detail) || {};
        const { route, params } = this.env.model.getActionRefresh(recordId);
        const result = await this.rpc(route, params);
        await this.env.model.refreshCache(result.data.records);
        this.toggleBarcodeLines(recordId);
    }

    /**
     * Handles triggered warnings. It can happen from an onchange for example.
     *
     * @param {CustomEvent} ev
     */
    _onWarning(ev) {
        const { title, message } = ev.detail;
        this.env.services.dialog.add(ConfirmationDialog, { title, body: message });
    }
}
MainComponent.template = 'stock_barcode.MainComponent';
MainComponent.components = {
    GroupedLineComponent,
    LineComponent,
    LocationButton,
    PackageLineComponent,
    ViewsWidgetAdapter,
};

registry.category("actions").add("stock_barcode_client_action", MainComponent);

export default MainComponent;
