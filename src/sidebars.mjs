import Cookies from 'js-cookie';
import {cycleNavigation} from './navigation.mjs';
import {getOutline} from './outline.mjs';
import {initOptionHandler} from './options.mjs';

/**
 * Modes:
 * Starts in NAVIGATE at top of screen.
 *
 * - READ:
 *   ? User is reading and is shown no distractions
 *   - No sidebars
 *   - No timers
 *   - Stay in READ if scroll_down.
 *   - Go to NAVIGATE if scroll_up.
 *
 * - NAVIGATE:
 *   ? User is looking for something; show site and page navigation in sidebars
 *   - Visible sidebars
 *   - No timers
 *   - Stay in NAVIGATE if scroll_up
 *   - Go to NAVIGATE_WAIT if scroll_down
 *
 * - NAVIGATE_WAIT:
 *   ? User should still see navigation after scrolling down, but may also have
 *   stopped scrolling. Wait for activity. If none, prepare them for navigation
 *   fade-out.
 *   - Visible sidebars
 *   - Go to NAVIGATE if scroll_up
 *   - Restart NAVIGATE_WAIT if scroll_down
 *   - Start timer:
 *     - If no action for WAIT_TIME milliseconds
 *       - Go to NAVIGATE_STOP
 *
 * - NAVIGATE_STOP:
 *   ? User should still see navigation after stopping scrolling, but be
 *   prepared for navigation to fadeout. Scrolling keeps the nav visible.
 *   - Visible scrollbars
 *   - Micro-interaction: Anticipation:
 *      - Show blinking dot to indicate imminent change
 *   - Go to NAVIGATE on scroll_up
 *   - Go to NAVIGATE_WAIT on scroll_down
 *   - Go to READ after STOP_TIME milliseconds.
 * 
 * Intervals:
 * - Every second:
 *   - Calculate most visible section. Add 1s to its current timer. If >30s,
 *   mark as current in sidebar and store in cookie.
 */

const READ = 'READ';
const NAVIGATE = 'NAVIGATE';
const NAVIGATE_WAIT = 'NAVIGATE_WAIT';
const NAVIGATE_STOP = 'NAVIGATE_STOP';

const DOWN = 'DOWN';
const UP = 'UP';

const ICON_UNCHECKED = 'fa-square-o';
const ICON_CHECKED = 'fa-check-square-o';
const ICON_SCROLL_DOWN = 'fa-arrow-down';

const LOCAL_STORAGE_LAST_READING = 'last-reading';

const TABLET_BREAKPOINT = 1100;  // Detect small screens

const WAIT_TIME = 1000;  // For NAVIGATE_WAIT
const STOP_TIME = 1000;  // For NAVIGATE_STOP
const BOOKMARK_TIME = 20;  // How long a section should be onscreen before marking is the 'Last Read'.
const READING_SPEED = 5;  // Words per second per on-screen sections.

//  Completion
const MAX_BAR_WIDTH = 10; // ems

var [user_slug, doc_slug] = getPageInfo(document.location.pathname);

var mode = NAVIGATE;
var verticalPosition = window.scrollY;
var lastScrollDirection = UP;
var waitTimer = undefined;
var blinkTimer = undefined;
var outline = [];

/**
 * An object of {section_id: string, seconds_onscreen: int}. 
 * Stores the time for which any section has currently been visible onscreen.
 * Use to bookmark the Last Read section.
 */
var currentSectionVisiblilityTime = {};

/**
 * An object of {section_id: string, seconds_onscreen: int}. 
 * Stores the total time a section has been visible onscreen on this device.
 * Used to estimate completedSections.
 *
 */
var totalSectionVisibilityTime = {};

/**
 * The ID of the 'Last Read' section.
 * Determined by being onscreen for a minimum period of time.
 * Shown in #page-navigation.
 */
var lastReadSectionId = ''; 

function estimateReadingTime(word_count) {
    return Math.round(word_count / READING_SPEED);
}

/**
 *
 * @idea: Log scale for setting a boundary on large values?
 */
function mapWordCountToBarWidth(word_count) {
    const bar_width = Math.floor(word_count / 10) / 10;
    const constrained = Math.max(0, Math.min(MAX_BAR_WIDTH, bar_width));
    return constrained;
}

const COMPLETION_WORD_LIMIT = 10000;

function getCompletionScale(outline) {
    const total_words = outline.reduce((acc, section) => {
        return acc + section[4]; // word_count
    }, 0);
    if (total_words > COMPLETION_WORD_LIMIT) {
        return COMPLETION_WORD_LIMIT / total_words;
    } else {
        return 1;
    }
}

function createCompletionListByRecursion(h1, outline, ratio) {
    //  Create list items for tags (e.g. H1) and recurse for sections having
    //  lower tags (e.g. > H1).
    //  We want to create:
    //  <ol>  // H1
    //      <li>
    //          <a href="">H1</a>
    //          // Recurse here for H2
    //      </li>
    //      ...
    //  </ol>
    if (!ratio) {
         var ratio = getCompletionScale(outline);
    }
    var html = '<ol>';
    var h1_index = 0;
    while (h1_index < outline.length) {
        const [tag, href, number, title, word_count] = outline[h1_index];
        const unit_width = mapWordCountToBarWidth(word_count * ratio);
        const bar_width = mapWordCountToBarWidth(word_count * ratio);
        const zero_value = bar_width - 0.7
        html += '<li>';
        html += `<a class="${tag}" href="${href}">`;
        html += `<div class="completion-unit" style="width: ${unit_width}em; background-position-x: ${zero_value}em;"></div>`,
        html += `</a>`;
        var distance_to_next_h1 = 1;
        while (
                h1_index + distance_to_next_h1 < outline.length
            &&  outline[h1_index + distance_to_next_h1][0] != h1 
        ) {
            distance_to_next_h1 += 1;
        }
        if (distance_to_next_h1 > 1) {
            html += createCompletionListByRecursion(
                incTag(h1),
                outline.slice(h1_index + 1, h1_index + distance_to_next_h1),
                ratio
            );
        }
        h1_index += distance_to_next_h1;
        html += '</li>';
    }
    return html + '</ol>';
}

function calculateBackgroundOffset(time_visible, reading_time, word_count) {
    const min_value = -1.0;
    const bar_width = mapWordCountToBarWidth(word_count);
    const max_value = bar_width - 0.7;
    const difference = max_value - min_value;
    const ratio = Math.max(0, Math.min(1, time_visible / reading_time));
    return min_value + (difference * ratio);
}

function updateCompletionBars() {
    const ratio = getCompletionScale(outline);
    const completion_list = document.querySelector('#completion');
    outline.forEach(([tag, href, number, title, word_count]) => {
        const key = href.slice(1);
        const time_visible = totalSectionVisibilityTime[key] || 0;
        const reading_time = estimateReadingTime(word_count) || 0.1;
        const offset = calculateBackgroundOffset(time_visible, reading_time,
                                                 word_count * ratio);
        const a = completion_list.querySelector('[href="' + href + '"]');
        const div = a.querySelector('.completion-unit');
        div.style.backgroundPositionX = `${offset}em`;
    });
}

function changeListLevel(last_level, level) {
    //  e.g. H1, H2 -> '<ol>'
    //  e.g. H4, H2 -> '</ol></ol>'
    //  e.g. H4, H4 -> ''
    const last_number = Math.round(last_level.slice(1));
    const number = Math.round(level.slice(1));
    if (number > last_number) {
        return '<ol>'.repeat(number - last_number);
    }
    if (last_number > number) {
        return '</ol>'.repeat(last_number - number);
    }
    return '';
}

function incTag(tag) {
    //  Change e.g. H3 into H4.
    const number = Math.round(tag.slice(1));
    return `H${number + 1}`;
}

function createLastReadingBookmarks() {
    if (user_slug && doc_slug && outline.length > 0) {
        return `
                <a id="last-reading" class="icon-button"><i class="fa fa-fw fa-bookmark"></i> <span>Last Reading</span> <span id="last-reading-readout">&sect;0</span></a>
            `;
    } else {
        return '';
    }
}

function createOutlineListByRecursion(h1, outline) {
    //  Create list items for tags (e.g. H1) and recurse for sections having
    //  lower tags (e.g. > H1).
    //  We want to create:
    //  <ol>  // H1
    //      <li>
    //          <a href="">H1</a>
    //          // Recurse here for H2
    //      </li>
    //      ...
    //  </ol>
    var html = '<ol>';
    var h1_index = 0;
    while (h1_index < outline.length) {
        const [tag, href, number, title, word_count] = outline[h1_index];
        const section = number.slice(1, -1).split('.').pop();
        html += '<li>';
        html += `<a class="${tag}" href="${href}">${section}. ${title}</a>`;
        var distance_to_next_h1 = 1;
        while (
                h1_index + distance_to_next_h1 < outline.length
            &&  outline[h1_index + distance_to_next_h1][0] != h1 
        ) {
            distance_to_next_h1 += 1;
        }
        if (distance_to_next_h1 > 1) {
            html += createOutlineListByRecursion(
                incTag(h1),
                outline.slice(h1_index + 1, h1_index + distance_to_next_h1)
            );
        }
        h1_index += distance_to_next_h1;
        html += '</li>';
    }
    return html + '</ol>';
}

function getPageInfo(pathname) {
    const readPath = /^\/read\/([a-z0-9-]+)\/([a-z0-9-]+)\/?$/;
    const readMatch = pathname.match(readPath);
    if (readMatch) {
        return [readMatch[1], readMatch[2]];
    }
    const userPath = /^\/user\/([a-z0-9-]+)\/?$/;
    const userMatch = pathname.match(userPath);
    if (userMatch) {
        return [userMatch[1], undefined];
    }
    return [undefined, undefined];
}

function createSiteMenu() {
    var html = `
        <div id="menu" class="sticky sidebar">
            <div class="space">
                <div><a class="icon-button" href="/"><i class="fa fa-fw fa-home"></i> Home</a></div>
        `;
    if (user_slug && doc_slug == 'index') {
        html += `
                <div><a class="icon-button" href="/rss/${user_slug}.xml"><i class="fa fa-fw fa-rss"></i> RSS Feed</a></div>
        `;
    }
    html += `
            </div>
            <div class="space">
                <div class="icon-button theme-button"><i class="fa fa-fw fa-adjust"></i> Dark Mode</div>
                <div class="icon-button fullscreen-button"><i class="fa fa-fw fa-expand"></i> Full Screen</div>
            </div>
            <div class="space">
                <div id="option-escape" class="option-button"><span>Show and hide the <span class="show-inline-if-tablet-or-smaller">menu</span><span class="show-inline-if-laptop-or-larger">sidebars</span> with <tt>Esc</tt></span> <i id="escape-icon" class="fa fa-fw fa-square-o"></i></div>
                <div class="show-block-if-laptop-or-larger">
                    <div id="option-auto-hide" class="option-button">Auto-hide sidebars when scrolling down <i id="scroll-icon" class="fa fa-fw fa-square-o"></i></div>
                </div>
                <div class="show-block-if-tablet-or-smaller">
                    <div id="option-click" class="option-button">Hide menu after clicking a navigation link <i id="click-icon" class="fa fa-fw fa-square-o"></i></div>
                </div>
            </div>
        `;
    if (user_slug && doc_slug) {
        html += `
            <div class="space">
                <div><a class="icon-button" href="/epub/${user_slug}/${doc_slug}"><i class="fa fa-fw fa-book"></i> Download ePub</a></div>
                <div><a class="icon-button" href="/download/${user_slug}/${doc_slug}"><i class="fa fa-fw fa-download"></i> Download Source</a></div>
                <div><a class="icon-button" href="/upload/${user_slug}/${doc_slug}"><i class="fa fa-fw fa-upload"></i> Upload Source</a></div>
                <div><a class="icon-button" onclick="window.print();"><i class="fa fa-fw fa-print"></i> Print to PDF</a></div>
            </div>
        `;
    }
    const login = Cookies.get('token');
    if (login) {
        html += `
                <div class="space">
                    <div><a class="icon-button" href="/new-article"><i class="fa fa-fw fa-plus"></i> New Article</a></div>
                    <div><a class="icon-button" href="/logout"><i class="fa fa-fw fa-sign-out"></i> User Logout</a></div>
                </div>
            </div>
        `;
    } else {
        html += `
                <div class="space">
                    <div><a class="icon-button" href="/login"><i class="fa fa-fw fa-sign-in"></i> User Login</a></div>
                </div>
            </div>
        `;
    }
    const page = document.querySelector('#page');
    if (page) {
        const siteMenu = document.createElement('nav');
        siteMenu.setAttribute('id', 'site-menu');
        siteMenu.innerHTML = html;
        page.before(siteMenu);
    }
}

function createPageOutline() {
    var html = `
        <div class="sticky sidebar">
            <div class="space">
                <a class="icon-button" href="#"><i class="fa fa-fw fa-arrow-up"></i> <span>Top of Page</span> <span id="progress-meter">0%</span></a>
        `;
    html += createLastReadingBookmarks();
    html += `
            </div>
            <div id="completion" class="space">
        `;
    html += createCompletionListByRecursion('H1', outline);
    html += `
            </div>
            <div id="outline" class="space">
        `;
    html += createOutlineListByRecursion('H1', outline);
    html += `
            </div>
        </div>
        `;
    const page = document.querySelector('#page');
    if (page) {
        const pageOutline = document.createElement('nav');
        pageOutline.setAttribute('id', 'page-outline');
        pageOutline.innerHTML = html;
        page.after(pageOutline);
    }
}

//  Fade the sidebars

function showSidebars() {
    var html = document.querySelector('html');
    html.classList.remove('navigation-buttons');
    html.classList.add('navigation-sidebars');
};

function hideSidebars() {
    var html = document.querySelector('html');
    html.classList.remove('navigation-sidebars');
    html.classList.add('navigation-buttons');
};

function removeSidebars() {
    const selector = '#site-menu,#page-outline';
    const sidebars = document.querySelectorAll(selector);
    [...sidebars].forEach(sidebar => sidebar.remove());
}

function showScrollDownIndicator() {
    const icon = document.getElementById('scroll-icon');
    icon.classList.remove(ICON_UNCHECKED);
    icon.classList.remove(ICON_CHECKED);
    icon.classList.add(ICON_SCROLL_DOWN);
};

function startWaitTimer() {
    if (waitTimer !== undefined) {
        stopWaitTimer();
    }
    waitTimer = setTimeout(waitTimerCallback, WAIT_TIME);
    mode = NAVIGATE_WAIT;
};

function stopWaitTimer() {
    clearTimeout(waitTimer);
    waitTimer = undefined;
};

function waitTimerCallback() {
    startScrollDownIndicatorBlinking();
    startBlinkTimer();
    mode = NAVIGATE_STOP;
};

function startScrollDownIndicatorBlinking() {
    const action = document.getElementById('scroll-icon');
    action.classList.add('blink');
};

function stopScrollDownIndicatorBlinking() {
    const action = document.getElementById('scroll-icon');
    action.classList.remove('blink');
};

function hideScrollDownIndicator() {
    const icon = document.getElementById('scroll-icon');
    icon.classList.remove(ICON_SCROLL_DOWN)
    icon.classList.remove(ICON_UNCHECKED);
    icon.classList.add(ICON_CHECKED);
};

function startBlinkTimer() {
    clearTimeout(blinkTimer);
    blinkTimer = setTimeout(blinkTimerCallback, STOP_TIME);
};

function stopBlinkTimer() {
    clearTimeout(blinkTimer);
    blinkTimer = undefined;
};

function blinkTimerCallback() {
    hideScrollDownIndicator();
    mode = READ;
    hideSidebars();
};

/*
 * Handle outline updates based on scrolling-into-view.
 */
function handleVisibility(events) {
    const completion = document.querySelector('#completion');
    const outline = document.querySelector('#outline');
    for (var event of events) {
        const selector = '[href="#' + event.target.id + '"]';
        const outlineLink = outline.querySelector(selector);
        if (outlineLink !== null) {
            if (event.isIntersecting) {
                var li = outlineLink.closest('li')
                li.classList.add('visible');
                currentSectionVisiblilityTime[event.target.id] = 0;
            } else {
                outlineLink.closest('li').classList.remove('visible');
                if (currentSectionVisiblilityTime[event.target.id] !== undefined) {
                    delete currentSectionVisiblilityTime[event.target.id];
                }
            }
        }
        const completionLink = completion.querySelector(selector);
        if (completionLink) {
            var li = completionLink.closest('li');
            if (event.isIntersecting) {
                li.classList.add('visible');
            } else {
                li.classList.remove('visible');
            }
        }
    }
}

/*
 * Update timers based on visible sections
 */
function incrementVisibilityTimers() {
    const oldBookmark = lastReadSectionId;
    for (var key in currentSectionVisiblilityTime) {
        currentSectionVisiblilityTime[key] += 1;
        if (key in totalSectionVisibilityTime) {
            totalSectionVisibilityTime[key] += 1;
        } else {
            totalSectionVisibilityTime[key] = 0;
        }
        if (currentSectionVisiblilityTime[key] > BOOKMARK_TIME) {
            lastReadSectionId = key;
        }
        if (oldBookmark !== lastReadSectionId && !isAtTopOfScreen()) {
            updateBookmark();
            break;
        }
    }
    updateCompletionBars();
};

function storeCompletionData() {
    const pathname = window.location.pathname;
    if (user_slug && doc_slug) {
        saveUserDocVisited();
        saveUserDocCompletion(totalSectionVisibilityTime);
    }
}

function saveUserDocVisited() {
    var visited = loadUserDocVisited();
    const key = `${user_slug}_${doc_slug}`;
    if (!(key in visited)) {
        visited.push(key);
        localStorage.getItem('pages_visited', JSON.stringify(visited));
    }
}

function loadUserDocVisited() {
    const json = localStorage.getItem('pages_visited') || '[]';
    return JSON.parse(json) || [];
}

function saveUserDocCompletion(totalSectionVisibilityTime) {
    const key = `completion_${user_slug}_${doc_slug}`;
    localStorage.setItem(key, JSON.stringify(totalSectionVisibilityTime));
}

function loadUserDocCompletion() {
    const key = `completion_${user_slug}_${doc_slug}`;
    const json = localStorage.getItem(key) || '{}';
    return JSON.parse(json) || {};
}

//  Auto-bookmark

function saveBookMark() {
    const json = localStorage.getItem(LOCAL_STORAGE_LAST_READING);
    if (json) {
        let last_reading = JSON.parse(json) || {};
        if (lastReadSectionId !== '') {
            const key = `${user_slug}_${doc_slug}`;
            last_reading[key] = lastReadSectionId;
            localStorage.setItem(LOCAL_STORAGE_LAST_READING, JSON.stringify(last_reading));
        }
    }
};

function isAtTopOfScreen() {
    return window.scrollY < 50;
}

function loadBookmark() {
    if (user_slug && doc_slug) {
        const json = localStorage.getItem(LOCAL_STORAGE_LAST_READING);
        if (json) {
            const data = JSON.parse(json) || {};
            const key = `${user_slug}_${doc_slug}`;
            if (key in data) {
                lastReadSectionId = data[key];
            }
        }
    }
}

function updateBookmark() {
    let maxTime = 0;
    let maxKey = undefined;
    for (var key in currentSectionVisiblilityTime) {
        if (currentSectionVisiblilityTime[key] > BOOKMARK_TIME) {
            maxTime = currentSectionVisiblilityTime[key];
            maxKey = key;
        }
    }
    if (maxKey != undefined) {
        lastReadSectionId = maxKey;
        updateLastReading();
        saveBookMark();
        currentSectionVisiblilityTime = {};
    }
};

function updateLastReading() {
    if (lastReadSectionId !== '') {
        var link = document.querySelector('#last-reading');
        var readout = document.querySelector('#last-reading-readout');
        if (link && readout) {
            var [number, slug] = lastReadSectionId.split('_');
            link.setAttribute('href', `#${lastReadSectionId}`);
            readout.innerHTML = `&sect;${number}`;
        }
    }
};

function handleEscapeKey() {
    const escapeOptionEnabled = localStorage.getItem('option-escape') === 'true';
    if (escapeOptionEnabled) {
        cycleNavigation();
        const icon = document.querySelector('#scroll-icon');
        icon.classList.remove('blink');
    }
}

function initKeystrokeHandling() {
    document.addEventListener('keyup', function (event) {
        if (event.key == 'Escape') {
            handleEscapeKey();
        }
    });
}

function handleOutlineClick() {
    const clickOptionEnabled = localStorage.getItem('option-click') === 'true';
    const onTabletOrSmaller = window.innerWidth <= TABLET_BREAKPOINT;
    if (clickOptionEnabled && onTabletOrSmaller) {
        cycleNavigation();
    }
}

function initClickHandling() {
    document.addEventListener('click', function (event) {
        const outline = event.target.closest('#page-outline');
        if (outline) {
            handleOutlineClick();
        }
    });
}

//  Initialisation

function handleScroll() 
{
    const optionEnabled = localStorage.getItem('option-auto-hide') === 'true';
    const onLaptopOrLarger = window.innerWidth > TABLET_BREAKPOINT;
    if (optionEnabled && onLaptopOrLarger) {

        const scroll = verticalPosition < window.scrollY ? DOWN : UP;
        verticalPosition = window.scrollY;
        if (mode === READ) {
            if (scroll === UP && lastScrollDirection === DOWN) {
                showSidebars();
                hideScrollDownIndicator();
                stopScrollDownIndicatorBlinking()
                mode = NAVIGATE;
            }
        } else if (mode === NAVIGATE) {
            if (scroll === DOWN) {
                showScrollDownIndicator();
                startWaitTimer();
                mode = NAVIGATE_WAIT;
            }
        } else if (mode === NAVIGATE_WAIT) {
            stopWaitTimer();
            if (scroll === DOWN) {
                startWaitTimer();
                mode = NAVIGATE_WAIT;
            } else {
                hideScrollDownIndicator();
                mode = NAVIGATE;
            }
        } else if (mode === NAVIGATE_STOP) {
            startWaitTimer();
            hideScrollDownIndicator();
            stopScrollDownIndicatorBlinking()
            stopBlinkTimer();
            if (scroll === DOWN) {
                mode = NAVIGATE_WAIT;
            } else {
                hideScrollDownIndicator();
                mode = NAVIGATE;
                stopWaitTimer();
            }
        }
        lastScrollDirection = scroll;

    }
}

function initScrollHandling()
{
    document.addEventListener('scroll', function (event) {
        handleScroll();
    });
}

function updateEscapeOption()
{
    stopWaitTimer();
    stopBlinkTimer();
    const icon = document.querySelector('#escape-icon');
    if (icon) {
        const option = localStorage.getItem('option-escape') === 'true';
        if (option) {
            icon.classList.remove(ICON_UNCHECKED);
            icon.classList.add(ICON_CHECKED);
        } else {
            icon.classList.remove(ICON_CHECKED);
            icon.classList.add(ICON_UNCHECKED);
        }
        mode = NAVIGATE;
    }
}

function updateAutoHideOption()
{
    stopWaitTimer();
    stopBlinkTimer();
    const icon = document.querySelector('#scroll-icon');
    if (icon) {
        const option = localStorage.getItem('option-auto-hide') === 'true';
        icon.classList.remove(ICON_SCROLL_DOWN);
        icon.classList.remove('blink');
        if (option) {
            icon.classList.remove(ICON_UNCHECKED);
            icon.classList.add(ICON_CHECKED);
        } else {
            icon.classList.remove(ICON_CHECKED);
            icon.classList.add(ICON_UNCHECKED);
        }
        mode = NAVIGATE;
    }
}

function updateClickOption()
{
    stopWaitTimer();
    stopBlinkTimer();
    const icon = document.querySelector('#click-icon');
    if (icon) {
        const option = localStorage.getItem('option-click') === 'true';
        if (option) {
            icon.classList.remove(ICON_UNCHECKED);
            icon.classList.add(ICON_CHECKED);
        } else {
            icon.classList.remove(ICON_CHECKED);
            icon.classList.add(ICON_UNCHECKED);
        }
        mode = NAVIGATE;
    }
}

function initSectionObservers() 
{
    var observer = new IntersectionObserver(handleVisibility, {
        root: null, // <-- Viewport
        rootMargin: '-15% 0% -15% 0%',
        threshold: 0,
    });
    const sections = document.getElementsByTagName('section');
    for (const section of sections) {
        observer.observe(section);
    }
}

function initBookmarks() 
{
    loadBookmark();
    updateLastReading();
}

function initSidebars() 
{
    outline = getOutline('hgroup.section-heading')

    totalSectionVisibilityTime = loadUserDocCompletion()

    removeSidebars();
    createSiteMenu();
    createPageOutline();

    initOptionHandler('#option-escape', 'option-escape', updateEscapeOption);
    initOptionHandler('#option-auto-hide', 'option-auto-hide', updateAutoHideOption);
    initOptionHandler('#option-click', 'option-click', updateClickOption);

    initClickHandling();
    initKeystrokeHandling();
    initScrollHandling();

    initSectionObservers();
    setInterval(incrementVisibilityTimers, 1000);
    setInterval(storeCompletionData, 10000);

    initBookmarks();
}

export {initSidebars, stopScrollDownIndicatorBlinking};
