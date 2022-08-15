/** @odoo-module **/

export default class PackageLineComponent extends owl.Component {
    get isSelected() {
        return this.line.package_id.id === this.env.model.lastScannedPackage;
    }

    get line() {
        return this.props.line;
    }

    get qtyDone() {
        const reservedQuantity = this.line.lines.reduce((r, l) => r + l.product_uom_qty, 0);
        const doneQuantity = this.line.lines.reduce((r, l) => r + l.qty_done, 0);
        if (reservedQuantity > 0) {
            return doneQuantity / reservedQuantity;
        }
        return doneQuantity >= 0 ? 1 : 0;
    }

    openPackage() {
        this.trigger('open-package', { packageId: this.line.package_id.id });
    }

    select(ev) {
        ev.stopPropagation();
        this.env.model.selectPackageLine(this.line.package_id.id);
        this.env.model.trigger('update');
    }
}
PackageLineComponent.template = 'stock_barcode.PackageLineComponent';
