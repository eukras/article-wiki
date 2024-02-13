/**
 * Themes are light and dark
 *
 * The HTML tag can have classes:
 * - theme-light
 * - theme-dark
 *
 * - Theme tags are stored in localStorage as article-wiki-theme
 * - Themes are initialised in views/base.html to avoid style flashing during
 *      load
 *
 * @todo: Add auto.
 *
 */

const CLASSES = ['theme-light', 'theme-dark'];

function cycleTheme() {
    var html = document.querySelector('html');
    for (var i = 0; i < CLASSES.length; i++) {
        if (html.classList.contains(CLASSES[i])) {
            html.classList.remove(CLASSES[i]);
            const new_theme = CLASSES[(i + 1) % CLASSES.length];
            html.classList.add(new_theme);
            localStorage.setItem('article-wiki-theme', new_theme);
            return;
        }
    }
    html.classList.add(CLASSES[0]);  // <-- If no matches, use first theme
}

function initThemes(buttonSelector)
{
    document.addEventListener('click', function (event) {
        const button = event.target.closest(buttonSelector);
        if (button !== null) {
            cycleTheme();
            event.preventDefault();
        }
    }, false);
}

export {cycleTheme, initThemes};
