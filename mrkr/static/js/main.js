
var current_label = null;
var current_color = null;
var linked = false;
var linked_initialized = false;

/* Document event listeners */

document.addEventListener('DOMContentLoaded', function (evt) {
    console.log('DOMContentLoaded');
    register_event_listeners()
});

document.addEventListener('htmx:beforeRequest', function (evt) {
    console.log('htmx:beforeRequest');
    /* todo */
});


document.addEventListener('htmx:afterSwap', function (evt) {
    console.log('htmx:afterSwap');
    register_event_listeners();
    current_label = null;
    current_color = null;
    linked = false;
    linked_initialized = false;
});

document.addEventListener('htmx:timeout', function (evt) {
    console.log('htmx:timeout');
    /* todo */
});

document.addEventListener('htmx:sendError', function (evt) {
    console.log('htmx:sendError');
    /* todo */
});

document.addEventListener('htmx:responseError', function (evt) {
    console.log('htmx:responseError');
    /* todo */
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Shift") {
        linked = true;
    }
});

document.addEventListener("keyup", (event) => {
    if (event.key === "Shift") {
        linked = false;
        linked_initialized = false;
    }
});

document.addEventListener('keypress', function (evt) {
    const labelimage = document.getElementById("label-image");
    if (labelimage === null) {
        return;
    }
    if (evt.key === '+') {
        width = labelimage.clientWidth
        labelimage.style.width = Math.round(width * 1.01, 0) + "px";
    }
    if (evt.key === '-') {
        width = labelimage.clientWidth
        labelimage.style.width = Math.round(width * 0.99, 0) + "px";
    }
});

/* Renewable Event Listeners */

function register_event_listeners() {

    add_event_listener(document.getElementById('toggle-nav-button'), 'click', function (evt) {
        toggle_navigation();
    });

    const nav = document.getElementById("nav");
    const nav_items = nav.getElementsByTagName('button');
    for (const item of nav_items) {
        add_event_listener(item, 'click', function (evt) {
            collapse_navigation();
        });
    }

    const labelbuttons = document.getElementsByClassName('label-button');
    for (const item of labelbuttons) {
        add_event_listener(item, 'click', function (evt) {
            const allbuttons = document.getElementsByClassName('label-button');
            for (const button of allbuttons) {
                button.classList.remove("selected");
            }
            evt.target.classList.add("selected");
            current_label = evt.target.dataset.label;
            current_color = evt.target.dataset.color;
            linked = false;
            linked_initialized = false;
        });
    }

    const highlights = document.getElementsByClassName('highlight');
    for (const highlight of highlights) {
        add_event_listener(highlight, 'click', function (evt) {

            if (current_label === null) {
                return;
            }

            if (this.dataset.active === "true") {
                return;
            }

            this.dataset.active = "true";

            this.style.backgroundColor = current_color;

            if (!evt.shiftKey || linked_initialized === false) {

                if (evt.shiftKey) {
                    linked_initialized = true;
                }

                details = document.getElementById("added-labels");


                let new_item = document.createElement("div");
                new_item.classList.add("labeled-item");
                new_item.style.borderColor = current_color;
                new_item.style.backgroundColor = current_color + "20";
                new_item.dataset.ocr_ids = this.dataset.id;

                let new_span = document.createElement("span");
                new_span.innerHTML = current_label;

                let new_input = document.createElement("input");
                new_input.type = "text";
                new_input.value = this.dataset.content;

                let new_button = document.createElement("button");
                let new_img = document.createElement("img");
                new_img.src = "/static/img/trash-outline.svg";
                new_button.addEventListener('click', function (evt) {
                    remove_label(this);
                });

                new_button.appendChild(new_img);
                new_item.appendChild(new_span);
                new_item.appendChild(new_input);
                new_item.appendChild(new_button);

                details.prepend(new_item);

            } else {

                details = document.getElementById("added-labels");

                let existing_item = details.firstChild;

                existing_item.dataset.ocr_ids = existing_item.dataset.ocr_ids + "," + this.dataset.id;

                let input = existing_item.getElementsByTagName("input")[0];

                input.value = input.value + " " + this.dataset.content;

            }
        });
    }

}

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

function expand_navigation() {
    const nav = document.getElementById("nav");
    nav.classList.add("expanded");
}

function collapse_navigation() {
    const nav = document.getElementById("nav");
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

function remove_label(element) {

    ocr_ids = element.parentElement.dataset.ocr_ids.split(",");

    for (const ocr_id of ocr_ids) {
        highlight = document.querySelector(`.highlight[data-id="${ocr_id}"]`);
        highlight.style.backgroundColor = "#c0c0c0";
        highlight.dataset.active = "false";
    }

    element.parentElement.remove();
}

function scroll_to_element(element) {
    element.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
}