

document.addEventListener('DOMContentLoaded', function (evt) {
    console.log('DOMContentLoaded');
    register_event_listeners()
});

document.addEventListener('htmx:beforeRequest', function (evt) {
    console.log('htmx:beforeRequest');
    /*if (evt.detail.target.tagName in ["SPAN", "H1"]) {
        evt.detail.target.innerHTML = "&nbsp;";
    } else {
        evt.detail.target.innerHTML = "";
    }*/
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

    add_event_listener(document.getElementById('toggle-nav-button'), 'click', function (evt) {
        toggle_navigation();
    });

    const nav = document.getElementById("nav");
    const nav_items = nav.getElementsByTagName('button');
    console.log(nav_items);
    for (const item of nav_items) {
        add_event_listener(item, 'click', function (evt) {
            collapse_navigation();
        });
    }

    document.getElementById("label-image")?.addEventListener('click', function (e) {
        console.log(e);
        width = e.target.clientWidth
        if (e.altKey === true)
            e.target.style.width = Math.round(width * 1.1, 0) + "px";
        else if (e.shiftKey === true)
            e.target.style.width = Math.round(width * 0.9, 0) + "px";
    });

}

/* ---- */

function add_event_listener(element, event_name, callback) {
    if (!element) {
        return
    }

    if (element.dataset.listeners === 'true') {
        return
    }
    element.addEventListener(event_name, callback);
    element.dataset.listeners = 'true'
}

/* ---- */

function expand_navigation() {
    console.log('expand_navigation');
    const nav = document.getElementById("nav");
    nav.classList.add("expanded");
}

function collapse_navigation() {
    console.log('collapse_navigation');
    const nav = document.getElementById("nav");
    const expandable_nav_items = nav.getElementsByClassName('button-container expandable');
    for (const item of expandable_nav_items) {
        collapse_nav_item(item);
    }
    nav.classList.remove("expanded");
}

function toggle_navigation() {
    console.log('toggle_navigation');
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
    element.classList.remove("expanded");
}

function toggle_nav_item(element) {
    if (element.classList.contains("expanded")) {
        collapse_nav_item(element);
    } else {
        expand_nav_item(element);
    }
}