

document.addEventListener('DOMContentLoaded', function (evt) {

    document.getElementById('toggle-nav-button')?.addEventListener('click', function (evt) {
        toggle_navigation();
    });

});

document.addEventListener('htmx:beforeRequest', function (evt) {
    console.log('htmx:beforeRequest');
    evt.detail.target.innerHTML = "";
});


document.addEventListener('htmx:afterSwap', function (evt) {
    console.log('htmx:afterSwap');
});

document.addEventListener('htmx:timeout', function (evt) {
    return;
});

document.addEventListener('htmx:sendError', function (evt) {
    return;
});

document.addEventListener('htmx:responseError', function (evt) {
    return;
});

/* ---- */

function toggle_navigation() {
    const nav = document.getElementById("nav");
    nav.classList.toggle("expanded");
}