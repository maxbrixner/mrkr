

document.addEventListener('DOMContentLoaded', function (evt) {
    console.log('DOMContentLoaded');
    register_event_listeners()
});

document.addEventListener('htmx:beforeRequest', function (evt) {
    console.log('htmx:beforeRequest');
    evt.detail.target.innerHTML = "";
});


document.addEventListener('htmx:afterSwap', function (evt) {
    console.log('htmx:afterSwap');
    register_event_listeners()
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

function register_event_listeners() {

    document.getElementById('toggle-nav-button')?.addEventListener('click', function (evt) {
        toggle_navigation();
    });


}

/* ---- */

function toggle_navigation() {
    const nav = document.getElementById("nav");
    nav.classList.toggle("expanded");
}