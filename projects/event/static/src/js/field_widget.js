odoo.define('color_integer_widget', function(require) {
    "use strict";

    var fieldRegistry = require('web.field_registry');
    var basic_fields = require('web.basic_fields');

    var myPassword = basic_fields.FieldChar.extend({
        className: 'o_field_char o_my_password',

        init: function () {
            this._super.apply(this, arguments);
            this.nodeOptions.isPassword = true;
        },

        _renderEdit: function () {
            var result = this._super.apply(this, arguments);
            var $inputGroup = $('<div class="wrapper_input">');
            this.$el = $inputGroup.append(this.$el);
            var $button = $(
                '<i class="fa-eye fa-eye-slash"></i>'
            );
            this.$el = this.$el.append($button);
            $button.on('click', this._ontogglePassword.bind(this));

            return result;
        },

        _ontogglePassword: function(ev) {
            ev.stopPropagation();
            $(ev.target).toggleClass("fa-eye-slash");
            var type = $(ev.target).hasClass("fa-eye-slash") ? "password" : "text";
            this.$input.attr("type", type);
        }

    });

    fieldRegistry.add('my_password', myPassword);

});