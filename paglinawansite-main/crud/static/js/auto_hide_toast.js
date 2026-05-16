
document.addEventListener('DOMContentLoaded', function () {

    console.log('Toast JS Loaded');

    setTimeout(function () {

        const toastMessages = document.querySelectorAll('.toast-message');

        toastMessages.forEach(function (toast) {

            toast.remove();

        });

    }, 3000);

});