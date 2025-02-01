

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

    const nav = document.getElementById("nav");
    const expandable_nav_items = nav.getElementsByClassName('button-container expandable');
    for (const item of expandable_nav_items) {
        const button = item.firstElementChild;
        button.addEventListener('click', function (evt) {
            toggle_nav_item(item);
        });
    }

}

/* ---- */

function expand_navigation() {
    const nav = document.getElementById("nav");
    nav.classList.add("expanded");
}

function collapse_navigation() {
    const nav = document.getElementById("nav");
    const expandable_nav_items = nav.getElementsByClassName('button-container expandable');
    for (const item of expandable_nav_items) {
        collapse_nav_item(item);
    }
    nav.classList.remove("expanded");
}

function toggle_navigation() {
    const nav = document.getElementById("nav");
    if (nav.classList.contains("expanded")) {
        collapse_navigation();
    } else {
        expand_navigation();
    }
}

function expand_nav_item(element) {
    expand_navigation();
    element.classList.add("expanded");
}

function collapse_nav_item(element) {
    expand_navigation();
    element.classList.remove("expanded");
}

function toggle_nav_item(element) {
    if (element.classList.contains("expanded")) {
        collapse_nav_item(element);
    } else {
        expand_nav_item(element);
    }
}