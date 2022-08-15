odoo.define('payment_sepa_direct_debit.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    const sepaSignatureForm = require('payment_sepa_direct_debit.signature_form');

    const _t = core._t;

    const sepaDirectDebitMixin = {

        /**
         * Prepare the inline form of SEPA for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'sepa_direct_debit') {
                return this._super(...arguments);
            }

            if (flow === 'token') {
                return Promise.resolve(); // Don't show the form for tokens
            }
            // Although payments with SEPA are always performed as "online payments by token", we
            // set the flow to 'online' here so that it is not misinterpreted as a payment from an
            // existing mandate. The flow is later communicated to the controller as 'token'.
            this._setPaymentFlow('direct');

            // Configure the form
            this._resetSepaForm();
            return this._rpc({
                route: '/payment/sepa_direct_debit/form_configuration',
                params: {
                    'acquirer_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                },
            }).then(formConfiguration => {
                const sepaForm = document.getElementById(`o_sdd_form_${paymentOptionId}`);
                // Update the form with the partner information
                if (formConfiguration.partner_name && formConfiguration.partner_email) {
                    sepaForm.querySelector('div[name="o_sdd_signature_config"]').setAttribute(
                        'data-name', formConfiguration.partner_name
                    );
                    sepaForm.querySelector('span[name="o_sdd_partner_email"]')
                        .innerText = formConfiguration.partner_email;
                }
                // Show the phone number input if enabled on the acquirer
                if (formConfiguration.sms_verification_required) {
                    sepaForm.querySelectorAll('div[name="o_sdd_sms"]').forEach(el => {
                        el.querySelector('input').required = true;
                        el.classList.remove('d-none');
                    });
                    sepaForm.querySelector('button[name="o_sms_button"]').addEventListener(
                        'click', () => {
                            this._sendVerificationSms(paymentOptionId, parseInt(
                                this.txContext.partnerId
                            ));
                        }
                    );
                }
                // Show the signature form if required on the acquirer
                if (formConfiguration.signature_required) {
                    this.sdd_signature_required = true;
                    this._setupSignatureForm(sepaForm);
                }
            });
        },

        /**
         * Create a token and use it as payment option to process the payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        _processPayment: function (provider, paymentOptionId, flow) {
            if (provider !== 'sepa_direct_debit' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }

            // Retrieve and store inputs
            const sepaForm = document.getElementById(`o_sdd_form_${paymentOptionId}`);
            const ibanInput = sepaForm.querySelector('input[name="iban"]');
            const phoneInput = sepaForm.querySelector('input[name="phone"]');
            const verificationCodeInput = sepaForm.querySelector('input[name="verification_code"]');
            const signerInput = sepaForm.querySelector('input[name="signer"]');

            // Check that all required inputs are filled at this step
            if (
                !ibanInput.reportValidity()
                || !phoneInput.reportValidity()
                || !verificationCodeInput.reportValidity()
                || (this.sdd_signature_required && signerInput && !signerInput.reportValidity())
            ) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve(); // Let the browser request to fill out required fields
            }

            // Extract the signature from the signature widget if the option is enabled
            let signature = undefined;
            if (this.sdd_signature_required && signerInput) {
                const signValues = this.signatureWidget._getValues();
                if (signValues) {
                    signature = signValues.signature;
                }
            }

            // Create the token to use for the payment
            return this._rpc({
                route: '/payment/sepa_direct_debit/create_token',
                params: {
                    'acquirer_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                    'iban': ibanInput.value,
                    'mandate_id': this.mandate_id,
                    'phone': phoneInput.value,
                    'verification_code': verificationCodeInput.value,
                    // If the submit button was hit before that the signature widget was loaded, the
                    // input will be null. Pass undefined to let the server raise an error.
                    'signer': this.sdd_signature_required && signerInput
                        ? signerInput.value : undefined,
                    'signature': signature,
                },
            }).then(tokenId => {
                // Now that the token is created, use it as a payment option in the generic flow
                return this._processPayment(provider, tokenId, 'token');
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message,
                );
            });
        },

        /**
         * Clear the stored mandate id and removes the signature form.
         *
         * @private
         * @return {undefined}
         */
        _resetSepaForm: function () {
            this.mandate_id = undefined;
            if (this.signatureWidget) {
                this.signatureWidget.destroy();
            }
        },

        /**
         * Send a verification code by SMS to the provider phone number
         *
         * @private
         * @param {number} acquirerId - The id of the selected payment acquirer
         * @param {number} partnerId - The id of the partner
         * @return {Promise}
         */
        _sendVerificationSms: function (acquirerId, partnerId) {
            this._hideError(); // Remove any previous error

            // Retrieve and store inputs
            const sepaForm = document.getElementById(`o_sdd_form_${acquirerId}`);
            const ibanInput = sepaForm.querySelector('input[name="iban"]');
            const phoneInput = sepaForm.querySelector('input[name="phone"]');
            const verificationCodeInput = sepaForm.querySelector('input[name="verification_code"]');

            // Check that all required inputs are filled at this step
            if (!ibanInput.reportValidity() || !phoneInput.reportValidity()) {
                return Promise.resolve(); // Let the browser request to fill out required fields
            }

            // Disable the button to avoid spamming
            const sendSmsButton = sepaForm.querySelector('button[name="o_sms_button"]');
            sendSmsButton.setAttribute('disabled', true);

            // Fetch the mandate to verify. It is needed as it stores the verification code.
            return this._rpc({
                route: '/payment/sepa_direct_debit/get_mandate',
                params: {
                    'acquirer_id': acquirerId,
                    'partner_id': partnerId,
                    'iban': ibanInput.value,
                    'phone': phoneInput.value,
                },
            }).then(mandateId => {
                this.mandate_id = mandateId;
                // Send the verification code by SMS
                return this._rpc({
                    route: '/payment/sepa_direct_debit/send_verification_sms',
                    params: {
                        acquirer_id: acquirerId,
                        mandate_id: mandateId,
                        phone: phoneInput.value,
                    }
                });
            }).then(() => {
                // Enable the validation code field
                verificationCodeInput.removeAttribute('readonly');
                sendSmsButton.innerText = _t("SMS Sent");
                sendSmsButton.classList.add('fa', 'fa-check');

                // Show the button again after a few moments to allow sending a new SMS
                setTimeout(() => {
                    sendSmsButton.removeAttribute('disabled');
                    sendSmsButton.innerText = _t('Re-send SMS');
                    sendSmsButton.classList.remove('fa', 'fa-check');
                }, 15000);
            }).guardedCatch(error => {
                error.event.preventDefault();
                sendSmsButton.removeAttribute('disabled');
                this._displayError(
                    _t("Server Error"),
                    _t("Could not send the verification code."),
                    error.message.data.message
                );
            });
        },

        /**
         * Show the signature form and attach the signature widget
         *
         * @private
         * @param {HTMLElement} sepaForm - The SEPA payment form
         * @return {undefined}
         */
        _setupSignatureForm: function (sepaForm) {
            const signatureForm = sepaForm.querySelector('div[name="o_sdd_signature_form"]');
            signatureForm.querySelector('input').required = true;
            signatureForm.classList.remove('d-none');
            const signatureConfig = sepaForm.querySelectorAll('div[name="o_sdd_signature_config"]');
            this.signatureWidget = new sepaSignatureForm(this, {
                mode: 'draw',
                nameAndSignatureOptions: signatureConfig[0].dataset
            });
            this.signatureWidget.insertAfter(signatureConfig);
        },

    };

    checkoutForm.include(sepaDirectDebitMixin);
    manageForm.include(sepaDirectDebitMixin);
});
