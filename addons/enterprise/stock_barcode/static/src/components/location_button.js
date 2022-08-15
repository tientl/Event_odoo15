/** @odoo-module **/

export default class LocationButton extends owl.Component {
    select(source) {
        if (source) {
            this.env.model.changeSourceLocation(this.props.location.id, true);
        } else {
            this.env.model.changeDestinationLocation(this.props.location.id);
        }
    }
}
LocationButton.template = 'stock_barcode.LocationButton';
