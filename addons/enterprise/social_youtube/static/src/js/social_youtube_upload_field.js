odoo.define('youtube_upload_field', function (require) {
'use strict';

var basicFields = require('web.basic_fields');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var utils = require('web.utils');

var _t = core._t;

var Dialog = require('web.Dialog');

/**
 * Override of the FieldChar that will handle the YouTube video upload process.
 *
 * We want to handle the upload from the client browser directly to his YouTube account and avoid
 * that the video file goes through our Odoo server to save time and bandwidth.
 *
 * User selects a file "c:/temp/my_video.mp4", which triggers the upload process directly on the
 * YouTube account he selected on the form view.
 * When the upload is finished, we save the 'youtube_video_id' value in a separate field and keep
 * a "dumb" string as the value of the 'youtube_video' field that will simply contain 'my_video.mp4'.
 *
 * Obviously the usage of this Widget is very limited:
 * - Only works in a form view
 * - Only works along specific other fields in the form view of the social.post model
 *   (youtube_access_token, youtube_video_id, ...)
 *
 * It is not meant to be used anywhere else.
 *
 * The template of the Char field was replaced by a custom one that can display upload buttons and
 * readonly input containing the uploaded file name.
 *
 */
var YoutubeUploadField = basicFields.FieldChar.extend({
    events: {
        'change .o_input_file': '_onFileChanged',
        'click .o_select_file_button': function () {
            this.$('.o_input_file').click();
        },
        'click .o_clear_file_button': '_onClearClick',
    },
    template: 'social_youtube.YoutubeUploadField',

    init: function (parent, name, record) {
        this._super.apply(this, arguments);
        this.useFileAPI = !!window.FileReader;
        this.maxUploadSize = 128 * 1024 * 1024 * 1024; // 128 Go -> max Youtube upload
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When the file upload is complete, Youtube triggers his own video "processing"
     * that can take up to a few minutes and during which we can't alter the video
     * in any way nor embed it in the YouTube preview.
     *
     * It's necessary to wait for the process to be complete before letting the user
     * proceed with posting, since we can't alter video properties during this process.
     *
     * So we just periodically ping the API to check the status of this "video processing".
     * When it's done, we resolve the Promise returned by this method.
     *
     * @private
     */
    _awaitPostProcessing: function (uploadedVideoId) {
        return new Promise((resolve, reject) => {
            this.uploadedVideoId = uploadedVideoId;
            this.videoProcessedResolve = resolve;
            this.processingInfoInterval = setInterval(this._updateProcessingInfo.bind(this), 1500);
        });
    },

    /**
     * Clear file input and empties the related youtube_video_id field
     *
     * @private
     */
     _clearValue: function () {
        var self = this;
        this._setValue('').then(function () {
            self.trigger_up('field_changed', {
                dataPointID: self.dataPointID,
                changes: {
                    youtube_video_id: false
                }
            });
            self._render();
        });
    },

    _getYoutubeAccessToken: function () {
        return this.getParent() && this.getParent().state.data.youtube_access_token;
    },

    /**
     * Small method that listens to the file upload progress and updates the UI accordingly to give
     * user feedback.
     *
     * @private
     */
    _listenUploadProgress: function () {
        var self = this;

        var xhr = new window.XMLHttpRequest();
        xhr.upload.addEventListener("progress", function (e) {
            if (e.lengthComputable) {
                var roundedProgress = Math.round((e.loaded / e.total) * 100);
                self.$('.o_social_youtube_upload_progress').css('width', roundedProgress + '%');
                self.$('.o_social_youtube_upload_text').text(
                    _.str.sprintf(_t('Uploading... %s'), roundedProgress + '%'));
            }
       }, false);

       return xhr;
    },

    /**
     * We use the resumable upload protocol of YouTube to upload our videos, because it allows
     * setting the video as 'private' before uploading it, meaning it will not publicly appear for
     * followers of the channel before the video is actually "posted" on the social application.
     *
     * However, to simplify the implementation, we do not split the video in "chucks" and still
     * upload all at once.
     * Depending on the feedback we get, it would maybe be nice to actually split the file in chunks
     * and implement a "retry" behavior whenever an upload sequence fails.
     *
     * This method will open the upload session and return a 'location' that will be used to upload
     * the file chunks.
     *
     * @param {number} fileSize
     * @param {string} fileType
     * @private
     */
    _openUploadSession: async function (fileSize, fileType) {
        var self = this;

        return new Promise((resolve, reject) => {
            var title = _t('Draft Video');
            var description = '';

            // attempt to get latest record information from form view
            var parentState = this.getParent() && this.getParent().state;
            if (parentState) {
                if (parentState.data.youtube_title) {
                    title = parentState.data.youtube_title;
                }

                if (parentState.data.youtube_description) {
                    description = parentState.data.youtube_description;
                }
            }

            $.ajax({
                url: 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=status%2Csnippet',
                type: 'POST',
                beforeSend: (request) => {
                    request.setRequestHeader("Authorization", "Bearer " + self._getYoutubeAccessToken());
                    request.setRequestHeader('Content-Type', 'application/json');
                    request.setRequestHeader("X-Upload-Content-Length", fileSize);
                    request.setRequestHeader("x-Upload-Content-Type", fileType);
                },
                data: JSON.stringify({
                    status: {privacyStatus: "private"},
                    snippet: {
                        title: title,
                        description: description
                    },
                }),
                dataType: 'text',
                processData: false,
                cache: false,
                success: (data, textStatus, request) => {
                    resolve(request.getResponseHeader('location'));
                },
                error: () => {
                    self.displayNotification({
                        type: 'warning',
                        message: _t('Upload failed. Please try again.')
                    });
                    self.$('.o_input_file').val('');
                    self._renderEdit();
                    reject();
                },
            });
        });
    },

    /**
     * When rendering as edit, there are 2 use cases:
     * - When the field already has a value, render a readonly input displaying that value and a
     *   button to remove the value ;
     * - When the field has no value yet, simply display a "UPLOAD FILE" button.
     *
     * @private
     * @override
     */
    _renderEdit: function () {
        this.$('.o_social_youtube_upload_bar').addClass('d-none');
        if (this.value) {
            this.$('button').removeClass('d-none');
            this.$('.o_select_file_button').first().addClass('d-none');
            this.$('.o_social_youtube_upload_filename')
                .removeClass('d-none')
                .val(this.value);
        } else {
            this.$('button').addClass('d-none');
            this.$('.o_social_youtube_upload_filename').addClass('d-none');
            this.$('.o_select_file_button').first().removeClass('d-none');
        }
    },

    /**
     * When rendering as readonly, only display the filename.
     *
     * @private
     * @override
     */
    _renderReadonly: function () {
        if (this.value) {
            this.$('.o_social_youtube_upload_filename')
                .removeClass('d-none')
                .text(this.value);
        }
    },

    /**
     * See #_awaitPostProcessing for more information.
     *
     * @private
     */
    _updateProcessingInfo: function () {
        var self = this;
        $.ajax({
            url: 'https://www.googleapis.com/youtube/v3/videos',
            type: 'GET',
            beforeSend: function (request) {
                request.setRequestHeader("Authorization", "Bearer " + self._getYoutubeAccessToken());
            },
            data: {
                part: 'processingDetails',
                id: this.uploadedVideoId
            },
            success: function (response) {
                if ('items' in response && response.items.length === 1 && 'processingDetails' in response.items[0]) {
                    var processingDetails = response.items[0].processingDetails;
                    // Youtube is supposed to send a "partsProcessed / partsTotal"
                    // but from my tests it doesn't work (it either doesn't send it or sends 1000 / 1000)
                    self.$('.o_social_youtube_upload_text').text(_t('Youtube is processing...'));

                    if (processingDetails.processingStatus === 'succeeded') {
                        clearInterval(self.processingInfoInterval);
                        self.videoProcessedResolve();
                    }
                } else {
                    self.displayNotification({
                        type: 'warning',
                        message: _t('Upload failed. Please try again.')
                    });
                    self.$('.o_input_file').val('');
                    self._setValue('').then(function () {
                        self.trigger_up('field_changed', {
                            dataPointID: self.dataPointID,
                            changes: {
                                youtube_video_id: false
                            }
                        });
                        self._render();
                    });
                }
            },
        });
    },

    /**
     * See #_openUploadSession for more information about the upload process.
     *
     * @param {string} location
     * @param {File} file
     * @private
     */
    _uploadFile: async function (location, file) {
        var self = this;

        return new Promise((resolve, reject) => {
            $.ajax({
                url: location,
                type: 'PUT',
                beforeSend: function (request) {
                    request.setRequestHeader("Authorization", "Bearer " + self._getYoutubeAccessToken());
                    request.setRequestHeader("Content-Type", 'application/octet-stream');
                },
                success: (response) => {
                    resolve({
                        videoId: response.id,
                        categoryId: response.snippet.categoryId
                    })
                },
                error: function () {
                    self.displayNotification({
                        type: 'warning',
                        message: _t('Upload failed. Please try again.')
                    });
                    self.$('.o_input_file').val('');
                    self._renderEdit();
                    reject();
                },
                data: file,
                cache: false,
                contentType: false,
                processData: false,
                xhr: this._listenUploadProgress.bind(this)
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Clear the value and ask the user if he also wants to delete the actual
     * video from his YouTube channel.
     *
     * @private
     */
    _onClearClick: function () {
        var self = this;
        this.$('.o_input_file').val('');
        if (!this.isDestroyed()) {
            new Dialog(this, {
                size: 'medium',
                buttons: [{
                    text: _t("Yes, delete it"),
                    classes: 'btn-primary',
                    close: true,
                    click: function () {
                        $.ajax({
                            url: 'https://www.googleapis.com/youtube/v3/videos',
                            type: 'DELETE',
                            beforeSend: function (request) {
                                request.setRequestHeader("Authorization", "Bearer " + self._getYoutubeAccessToken());
                            },
                            data: {
                                id: self.getParent().state.data.youtube_video_id
                            },
                        });
                        self.uploadedVideoId = null;
                        self._clearValue();
                    },
                }, {
                    text: _t("No"),
                    close: true,
                    click: self._clearValue.bind(self)
                }],
                $content: $('<main/>', {
                    role: 'alert',
                    text: _t('Do you also want to remove the video from your YouTube account?'),
                }),
                title: _t("Confirmation"),
            }).open({shouldFocusButtons:true});
        }
    },

    /**
     * When the user selects a file:
     * - We start the upload process
     * - Periodically update the UI to show how many % are uploaded
     * - Wait for YouTube post-processing to finish
     * - Change the values of the 'youtube_video_id' and 'youtube_video_category_id' fields when the
     *   upload is complete.
     *
     * @param {Event} e
     * @private
     */
    _onFileChanged: async function (e) {
        var fileNodes = e.target;
        var hasReadableFile = this.useFileAPI && fileNodes.files.length !== 0;
        if (!this._getYoutubeAccessToken() || !hasReadableFile) {
            return;
        }

        var file = fileNodes.files[0];
        if (file.size > this.maxUploadSize) {
            this.displayNotification({
                title: _t("Video Upload"),
                message: _.str.sprintf(
                    _t("The selected video exceeds the maximum allowed size of %s."),
                    utils.human_size(this.maxUploadSize)
                ),
                type: 'danger',
            });
            return false;
        }

        this.$('.o_social_youtube_upload_bar').removeClass('d-none');
        this.$('button').addClass('d-none');

        var sessionLocation = await this._openUploadSession(file.size, file.type);
        var {videoId, categoryId} = await this._uploadFile(sessionLocation, file);
        await this._awaitPostProcessing(videoId);

        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: {
                youtube_video_id: videoId,
                youtube_video_category_id: categoryId,
            }
        });

        // strip and keep the last part of file name to get "video.mp4" and not "C:/fakepath/video.mp4"
        var fileName = this.$('form .o_input_file')
            .val()
            .match(/([^\\.]+)\.\w+$/)[0];
        this._setValue(fileName).then(() => this._render());
    }
});

fieldRegistry.add('youtube_upload', YoutubeUploadField);

return YoutubeUploadField;

});
