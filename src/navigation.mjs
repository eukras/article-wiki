/**
 * Navigation modes use buttons or sidebars.
 * The HTML tag can have classes:
 * - navigation-buttons
 * - navigation-sidebars
 * Navigation tags are stored in localStorage as article-wiki-navigation
 * Navigation is initialised in views/base.html to avoid style flashing during load.
 */

const CLASSES = ['navigation-buttons', 'navigation-sidebars'];

function cycleNavigation() {
    var html = document.querySelector('html');
    for (var i = 0; i < CLASSES.length; i++) {
        if (html.classList.contains(CLASSES[i])) {
            html.classList.remove(CLASSES[i]);
            const new_navigation = CLASSES[(i + 1) % CLASSES.length];
            html.classList.add(new_navigation);
            localStorage.setItem('article-wiki-navigation', new_navigation);
            return;
        }
    }
    html.classList.add(CLASSES[0]);  // <-- If no matches, use first navigation
}

function initNavigation(buttonSelector, callback)
{
    document.addEventListener('click', function (event) {
        const button = event.target.closest(buttonSelector);
        if (button !== null) {
            cycleNavigation();
            callback();
            event.preventDefault();
        }
    }, false);
}

export {cycleNavigation, initNavigation};
