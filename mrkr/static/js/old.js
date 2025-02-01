

document.addEventListener('DOMContentLoaded', function (evt) {
    console.log("aaa")
    add_close_dialog_event("dialog-overlay");
    add_close_sidebar_event("sidebar-overlay");
    add_close_sidebar_event2("sidebar-close-button");
    add_open_dialog_event("header-month-picker-button");
    add_open_sidebar_event("header-menu-button");
    add_invalid_event("input-email");
    add_invalid_event("input-password");
    add_go_to_reservation_event("header-plus-button");
});

document.addEventListener('htmx:afterSwap', function (evt) {
    add_close_dialog_event2("reservation-dialog-cancel-button");

    const calendarBody = document.getElementById("calendar-body");
    if (calendarBody) {
        const buttons = calendarBody.getElementsByTagName("button");
        for (let button of buttons) {
            button.addEventListener("click", function () {
                open_dialog();
            });
        }
    }

    document.getElementById("immm")?.addEventListener('click', function (e) {
        console.log(e);
        width = e.target.clientWidth
        if (e.altKey === true)
            e.target.style.width = Math.round(width * 1.1, 0) + "px";
        else if (e.shiftKey === true)
            e.target.style.width = Math.round(width * 0.9, 0) + "px";
    });

});

document.addEventListener('htmx:timeout', function (evt) {
    console.log("timeout", evt)
    evt.detail.target.classList.add("htmx-timeout");
});

document.addEventListener('htmx:sendError', function (evt) {
    console.log("sendError", evt)
    evt.detail.target.classList.add("htmx-timeout");
});

document.addEventListener('htmx:responseError', function (evt) {
    document.querySelector('html').innerHTML = evt.detail.xhr.response;
});

function inert(...element_ids) {
    for (var arg = 0; arg < arguments.length; ++arg) {
        document.getElementById(element_ids[arg])?.setAttribute("inert", "");
    }
}

function active(...element_ids) {
    for (var arg = 0; arg < arguments.length; ++arg) {
        document.getElementById(element_ids[arg])?.removeAttribute("inert", "");
    }
}

function add_custom_validity(element_id) {
    element = document.getElementById(element_id);
    element?.setCustomValidity(' ');
    element?.classList.add('invalid');
}

function remove_custom_validity(element_id) {
    element = document.getElementById(element_id);
    element?.setCustomValidity('');
    element?.classList.remove('invalid');
}

function open_dialog() {
    document.getElementById("dialog-content").innerHTML = "";
    document.getElementById("dialog-overlay").classList.add("open");
    inert("main", "header");
}

function close_dialog() {
    document.getElementById("dialog-overlay").classList.remove("open");
    active("main", "header");
}

function open_sidebar() {
    document.getElementById("sidebar-overlay").classList.add("open");
    inert("main", "header");
}

function close_sidebar() {
    document.getElementById("sidebar-overlay").classList.remove("open");
    active("main", "header");
}

function go_to_reservation() {
    location.href = "/reservation";
}

function add_go_to_reservation_event(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function () {
        go_to_reservation();
    });
}

function add_open_dialog_event(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function () {
        open_dialog();
    });
}

function add_close_dialog_event(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function (event) {
        if (event.target !== event.currentTarget) return;
        close_dialog();
    });
}

function add_close_dialog_event2(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function (event) {
        close_dialog();
    });
}

function add_open_sidebar_event(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function () {
        open_sidebar();
    });
}

function add_close_sidebar_event(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function (event) {
        if (event.target !== event.currentTarget) return;
        close_sidebar();
    });
}

function add_close_sidebar_event2(element_id) {
    document.getElementById(element_id)?.addEventListener('click', function (event) {
        close_sidebar();
    });
}

function add_invalid_event(element_id) {
    document.getElementById(element_id)?.addEventListener('invalid', function () {
        add_custom_validity(element_id);
    });
    document.getElementById(element_id)?.addEventListener('input', function () {
        remove_custom_validity(element_id);
    });
}

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        close_dialog();
        close_sidebar();
    }
});