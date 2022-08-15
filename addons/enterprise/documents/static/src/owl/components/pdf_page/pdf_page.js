odoo.define('documents.component.PdfPage', function (require) {
'use strict';

const { useState, useRef } = owl.hooks;

/**
 * Represents the page of a PDF.
 */
class PdfPage extends owl.Component {

    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.state = useState({
            isHover: false,
            isRendered: false,
        });
        // Used to append a canvas when it has been rendered.
        this.canvasWrapperRef = useRef("canvasWrapper");
    }

    mounted() {
        this.renderPage(this.props.canvas);
    }

    patched() {
        this.renderPage(this.props.canvas);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * The canvas is rendered asynchronously so it is only manually appended
     * later when available. It should have been done through the natural owl
     * re-rendering but it is currently causing unnecessary re-renderings of
     * sibling components which would noticeably slows the behaviour down.
     *
     * @public
     * @param {DomElement} canvas
     */
    renderPage(canvas) {
        if (!canvas || this.isRendered) {
            return;
        }
        this.canvasWrapperRef.el.appendChild(canvas);
        this.isRendered = true;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickWrapper(ev) {
        ev.stopPropagation();
        this.trigger('page-clicked', this.props.pageId);
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSelect(ev) {
        ev.stopPropagation();
        this.trigger('select-clicked', {
            pageId: this.props.pageId,
            isCheckbox: true,
            isRangeSelection: ev.shiftKey,
            isKeepSelection: true,
        });
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragEnter(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.state.isHover = true;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragLeave(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.state.isHover = false;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragOver(ev) {
        ev.preventDefault();
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragStart(ev) {
        ev.stopPropagation();
        this.trigger('page-dragged');
        ev.dataTransfer.setData('o_documents_pdf_data', this.props.pageId);
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDrop(ev) {
        this.state.isHover = false;
        if (!ev.dataTransfer.types.includes('o_documents_pdf_data')) {
            return;
        }
        const pageId = ev.dataTransfer.getData('o_documents_pdf_data');
        if (pageId === this.props.pageId) {
            return;
        }
        this.trigger('page-dropped', { targetPageId: this.props.pageId, pageId });
    }
}

PdfPage.defaultProps = {
    isPreview: false,
    isSelected: false,
};

PdfPage.props = {
    canvas: {
        type: Object,
        optional: true,
    },
    isPreview: Boolean,
    isSelected: Boolean,
    pageId: String,
};

PdfPage.template = 'documents.component.PdfPage';

return PdfPage;

});
