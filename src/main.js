import {initFullScreen} from './full-screen.mjs';
import {initNavigation} from './navigation.mjs';
import {initSidebars, stopScrollDownIndicatorBlinking} from './sidebars.mjs';
import {initProgress} from './progress.mjs';
import {initThemes} from './themes.mjs';
import {setSvgBackground} from './bokeh.mjs';

document.addEventListener("DOMContentLoaded", () => {

    //  IOS devices can't generally handle our fullscreen SVG translucency.
    if (!/Mac OS/.test(window.navigator.userAgent)) {
        setSvgBackground('#background');
    }

    initSidebars();
    initProgress('#progress-meter');

    //  After sidebars are rendered:
    initThemes('.theme-button');
    initFullScreen('.fullscreen-button');
    initNavigation('.navigation-button', stopScrollDownIndicatorBlinking);

});
