odoo.define('sign.multiFileUpload', function (require) {
    'use strict';

    function addNewFiles(files) {
        sessionStorage.setItem('signMultiFileData', JSON.stringify(files))
        return true;
    }

    function getNext() {
        return (JSON.parse(sessionStorage.getItem('signMultiFileData')) || []).shift();
    }

    function removeFile(id) {
        const files = JSON.parse(sessionStorage.getItem('signMultiFileData')) || [];
        sessionStorage.setItem('signMultiFileData', JSON.stringify(
            files.reduce((files, file) => {
                if (file.template === id) {
                    return files;
                }
                files.push(file);
                return files;
            }, [])
        ));
    }


    return {
        addNewFiles: addNewFiles,
        getNext: getNext,
        removeFile: removeFile
    }
});
