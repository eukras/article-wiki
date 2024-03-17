import {initFullScreen} from './full-screen.mjs';
import {initNavigation} from './navigation.mjs';
import {initSidebars, stopScrollDownIndicatorBlinking} from './sidebars.mjs';
import {initProgress} from './progress.mjs';
import {initThemes} from './themes.mjs';
import {initEditor} from './editor.mjs';
import {setSvgBackground} from './bokeh.mjs';

document.addEventListener("DOMContentLoaded", () => {

    // Small IOS devices can't generally handle our background SVGs.
    const not_ios = !/Mac OS/.test(window.navigator.userAgent);
    const max_res = Math.max(window.screen.width, window.screen.height);
    if (not_ios || max_res >= 1200) {
        setSvgBackground('#background');
    }

    initSidebars();
    initProgress('#progress-meter');
    initThemes('.theme-button');
    initFullScreen('.fullscreen-button');
    initNavigation('.navigation-button', stopScrollDownIndicatorBlinking);
    initEditor();

});
