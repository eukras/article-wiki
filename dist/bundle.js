(function () {
    'use strict';

    /**
     * Attach a full-screen toggle to a clickable target.
     *
     */

    function toggleFullScreen() 
    {
        if (document.fullscreenEnabled || document.webkitFullscreenEnabled) {
            if (document.fullscreen) {
                document.exitFullscreen();
            } else if (document.webkitFullscreenElement) {
                document.webkitCancelFullScreen();
            } else if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen();
            } else {
                document.documentElement.webkitRequestFullScreen();
            }
        }
    }

    function initFullScreen(buttonSelector)
    {
        document.addEventListener('click', function (event) {
            const button = event.target.closest(buttonSelector);
            if (button !== null) {
                toggleFullScreen();
            }
        });
    }

    /**
     * Navigation modes use buttons or sidebars.
     * The HTML tag can have classes:
     * - navigation-buttons
     * - navigation-sidebars
     * Navigation tags are stored in localStorage as article-wiki-navigation
     * Navigation is initialised in views/base.html to avoid style flashing during load.
     */

    const CLASSES$1 = ['navigation-buttons', 'navigation-sidebars'];

    function cycleNavigation() {
        var html = document.querySelector('html');
        for (var i = 0; i < CLASSES$1.length; i++) {
            if (html.classList.contains(CLASSES$1[i])) {
                html.classList.remove(CLASSES$1[i]);
                const new_navigation = CLASSES$1[(i + 1) % CLASSES$1.length];
                html.classList.add(new_navigation);
                localStorage.setItem('article-wiki-navigation', new_navigation);
                return;
            }
        }
        html.classList.add(CLASSES$1[0]);  // <-- If no matches, use first navigation
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

    /*! js-cookie v3.0.5 | MIT */
    /* eslint-disable no-var */
    function assign (target) {
      for (var i = 1; i < arguments.length; i++) {
        var source = arguments[i];
        for (var key in source) {
          target[key] = source[key];
        }
      }
      return target
    }
    /* eslint-enable no-var */

    /* eslint-disable no-var */
    var defaultConverter = {
      read: function (value) {
        if (value[0] === '"') {
          value = value.slice(1, -1);
        }
        return value.replace(/(%[\dA-F]{2})+/gi, decodeURIComponent)
      },
      write: function (value) {
        return encodeURIComponent(value).replace(
          /%(2[346BF]|3[AC-F]|40|5[BDE]|60|7[BCD])/g,
          decodeURIComponent
        )
      }
    };
    /* eslint-enable no-var */

    /* eslint-disable no-var */

    function init (converter, defaultAttributes) {
      function set (name, value, attributes) {
        if (typeof document === 'undefined') {
          return
        }

        attributes = assign({}, defaultAttributes, attributes);

        if (typeof attributes.expires === 'number') {
          attributes.expires = new Date(Date.now() + attributes.expires * 864e5);
        }
        if (attributes.expires) {
          attributes.expires = attributes.expires.toUTCString();
        }

        name = encodeURIComponent(name)
          .replace(/%(2[346B]|5E|60|7C)/g, decodeURIComponent)
          .replace(/[()]/g, escape);

        var stringifiedAttributes = '';
        for (var attributeName in attributes) {
          if (!attributes[attributeName]) {
            continue
          }

          stringifiedAttributes += '; ' + attributeName;

          if (attributes[attributeName] === true) {
            continue
          }

          // Considers RFC 6265 section 5.2:
          // ...
          // 3.  If the remaining unparsed-attributes contains a %x3B (";")
          //     character:
          // Consume the characters of the unparsed-attributes up to,
          // not including, the first %x3B (";") character.
          // ...
          stringifiedAttributes += '=' + attributes[attributeName].split(';')[0];
        }

        return (document.cookie =
          name + '=' + converter.write(value, name) + stringifiedAttributes)
      }

      function get (name) {
        if (typeof document === 'undefined' || (arguments.length && !name)) {
          return
        }

        // To prevent the for loop in the first place assign an empty array
        // in case there are no cookies at all.
        var cookies = document.cookie ? document.cookie.split('; ') : [];
        var jar = {};
        for (var i = 0; i < cookies.length; i++) {
          var parts = cookies[i].split('=');
          var value = parts.slice(1).join('=');

          try {
            var found = decodeURIComponent(parts[0]);
            jar[found] = converter.read(value, found);

            if (name === found) {
              break
            }
          } catch (e) {}
        }

        return name ? jar[name] : jar
      }

      return Object.create(
        {
          set,
          get,
          remove: function (name, attributes) {
            set(
              name,
              '',
              assign({}, attributes, {
                expires: -1
              })
            );
          },
          withAttributes: function (attributes) {
            return init(this.converter, assign({}, this.attributes, attributes))
          },
          withConverter: function (converter) {
            return init(assign({}, this.converter, converter), this.attributes)
          }
        },
        {
          attributes: { value: Object.freeze(defaultAttributes) },
          converter: { value: Object.freeze(converter) }
        }
      )
    }

    var api = init(defaultConverter, { path: '/' });

    /**
     * Create an array of the H1..H6 tags within a given target selector.
     *
     * Structure: [tagName, href, number, title]
     *
     * Example: ['H1', '#section-one', '1', 'Section One']
     *
     * @todo Add word counts.
     *
     */
    function word_count(text) {
        return (text.match(/\w+/g) || []).length;
    }

    function getOutline(selector)
    {
        const hgroups = document.querySelectorAll(selector);
        const outline = [...hgroups].map(hgroup => {
            const anchor = hgroup.querySelector('a');
            const [number, title] = hgroup.querySelectorAll('h1,h2,h3,h4,h5,h6');
            const section = hgroup.closest('section');
            return [
                number.tagName,
                anchor.getAttribute('href'),
                number.innerText, 
                title.innerText,
                word_count(section.innerText)
            ];
        });
        return outline;
    }

    /**
     * Attach an event to a clickable .option-button
     *
     */

    function toggleOption(option_key) 
    {
        const value = localStorage.getItem(option_key) === 'true';
        localStorage.setItem(option_key, !value);
    }

    function initOptionHandler(option_selector, option_key, callback)
    {
        document.addEventListener('click', function (event) {
            const element = event.target.closest(option_selector);
            if (element) {
                toggleOption(option_key);
                callback();
            }
        });
        callback();
    }

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
            const zero_value = bar_width - 0.7;
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
        const login = api.get('token');
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
    }
    function hideSidebars() {
        var html = document.querySelector('html');
        html.classList.remove('navigation-sidebars');
        html.classList.add('navigation-buttons');
    }
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
    }
    function startWaitTimer() {
        if (waitTimer !== undefined) {
            stopWaitTimer();
        }
        waitTimer = setTimeout(waitTimerCallback, WAIT_TIME);
        mode = NAVIGATE_WAIT;
    }
    function stopWaitTimer() {
        clearTimeout(waitTimer);
        waitTimer = undefined;
    }
    function waitTimerCallback() {
        startScrollDownIndicatorBlinking();
        startBlinkTimer();
        mode = NAVIGATE_STOP;
    }
    function startScrollDownIndicatorBlinking() {
        const action = document.getElementById('scroll-icon');
        action.classList.add('blink');
    }
    function stopScrollDownIndicatorBlinking() {
        const action = document.getElementById('scroll-icon');
        action.classList.remove('blink');
    }
    function hideScrollDownIndicator() {
        const icon = document.getElementById('scroll-icon');
        icon.classList.remove(ICON_SCROLL_DOWN);
        icon.classList.remove(ICON_UNCHECKED);
        icon.classList.add(ICON_CHECKED);
    }
    function startBlinkTimer() {
        clearTimeout(blinkTimer);
        blinkTimer = setTimeout(blinkTimerCallback, STOP_TIME);
    }
    function stopBlinkTimer() {
        clearTimeout(blinkTimer);
        blinkTimer = undefined;
    }
    function blinkTimerCallback() {
        hideScrollDownIndicator();
        mode = READ;
        hideSidebars();
    }
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
                    var li = outlineLink.closest('li');
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
    }
    function storeCompletionData() {
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
    }
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
        let maxKey = undefined;
        for (var key in currentSectionVisiblilityTime) {
            if (currentSectionVisiblilityTime[key] > BOOKMARK_TIME) {
                currentSectionVisiblilityTime[key];
                maxKey = key;
            }
        }
        if (maxKey != undefined) {
            lastReadSectionId = maxKey;
            updateLastReading();
            saveBookMark();
            currentSectionVisiblilityTime = {};
        }
    }
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
    }
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

    function handleScroll$1() 
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
                    stopScrollDownIndicatorBlinking();
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
                stopScrollDownIndicatorBlinking();
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
            handleScroll$1();
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
        outline = getOutline('hgroup.section-heading');

        totalSectionVisibilityTime = loadUserDocCompletion();

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

    /**
     * When scrolling, update a progress value which shows the percentage position
     * in the page.
     */

    function handleScroll(selector) {
        const readout = document.querySelector(selector);
        if (readout !== null) {
            const scrolledPixels = window.scrollY,
                documentPixels = document.body.scrollHeight,
                viewportPixels = window.innerHeight;
            if (viewportPixels == documentPixels) { 
                readout.innerHTML = '';
            } else {
                const scrollPercent = Math.min(Math.max(Math.round(
                    (scrolledPixels / (documentPixels - viewportPixels)) * 100
                ), 0), 100);

                readout.innerHTML = scrollPercent + '%';
            }
        }
    }
    function initProgress(selector) 
    {
        window.addEventListener('scroll', () => handleScroll(selector));
        handleScroll(selector);
    }

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

    //  A compressed version of Adobe's jquery.balanceText.js, which operates
    //  on the 'balance-text' class. This is a polyfill for `wrap-text:
    //  balance`, which will appear in CSS Text Level 4. Note this deletes
    //  links from the rewrapped text, and probably other tags too.

    function polyfillForBalanceText() {
        if (!window.CSS || !CSS.supports('text-wrap:balance')) {
            console.log('Using JS polyfill for text-wrap:balance');
            !function(a){function d(){this.reset();}function k(){a(".balance-text").balanceText();}var b=document.documentElement.style,c=b.textWrap||b.WebkitTextWrap||b.MozTextWrap||b.MsTextWrap||b.OTextWrap;d.prototype.reset=function(){this.index=0,this.width=0;};var e=function(a){return Boolean(a.match(/^\s$/))},f=function(b){b.find('br[data-owner="balance-text"]').replaceWith(document.createTextNode(" "));var c=b.find('span[data-owner="balance-text"]');if(c.length>0){var d="";c.each(function(){d+=a(this).text(),a(this).remove();}),b.html(d);}},g=function(a){return b=a.get(0).currentStyle||window.getComputedStyle(a.get(0),null),"justify"===b.textAlign},h=function(b,c,d){c=a.trim(c);var e=c.split(" ").length;if(c+=" ",2>e)return c;var f=a("<span></span>").html(c);b.append(f);var g=f.width();f.remove();var h=Math.floor((d-g)/(e-1));return f.css("word-spacing",h+"px").attr("data-owner","balance-text"),a("<div></div>").append(f).html()},i=function(a,b){return 0===b||b===a.length||e(a.charAt(b-1))&&!e(a.charAt(b))},j=function(a,b,c,d,e,f,g){for(var h;;){for(;!i(b,f);)f+=e;if(a.text(b.substr(0,f)),h=a.width(),0>e?d>=h||0>=h||0===f:h>=d||h>=c||f===b.length)break;f+=e;}g.index=f,g.width=h;};a.fn.balanceText=function(){return c?this:this.each(function(){var b=a(this),c=5e3;f(b);var e="";b.attr("style")&&b.attr("style").indexOf("line-height")>=0&&(e=b.css("line-height")),b.css("line-height","normal");var i=b.width(),k=b.height(),l=b.css("white-space"),m=b.css("float"),n=b.css("display"),o=b.css("position");b.css({"white-space":"nowrap","float":"none",display:"inline",position:"static"});var p=b.width(),q=b.height(),r="pre-wrap"===l?0:q/4;if(i>0&&p>i&&c>p){for(var s=b.text(),t="",u="",v=g(b),w=Math.round(k/q),x=w;x>1;){var y=Math.round((p+r)/x-r),z=Math.round((s.length+1)/x)-1,A=new d;j(b,s,i,y,-1,z,A);var B=new d;z=A.index,j(b,s,i,y,1,z,B),A.reset(),z=B.index,j(b,s,i,y,-1,z,A);var C;C=0===A.index?B.index:i<B.width||A.index===B.index?A.index:Math.abs(y-A.width)<Math.abs(B.width-y)?A.index:B.index,u=s.substr(0,C),v?t+=h(b,u,i):(t+=u.trimRight(),t+='<br data-owner="balance-text" />'),s=s.substr(C),x--,b.text(s),p=b.width();}v?b.html(t+h(b,s,i)):b.html(t+s);}b.css({position:o,display:n,"float":m,"white-space":l,"line-height":e});})},a(window).ready(k),a(window).resize(k);}(jQuery);
        }
    }

    /**
     * (Article Wiki)
     *
     * Generate an SVG Bokeh pattern to be applied as a background image.
     *
     * [NC 2024-02-10] Firefox has trouble with the large blurred circles. 
     */

    const LARGE_SIZES = [3, 3, 3, 4, 5];
    const SMALL_SIZES = [1, 1, 1, 1, 1, 1, 1, 2, 2];

    let svgIsRendering = false;

    function randInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1) + min);   
    }

    function randFloat(min, max) {
        return (Math.random() * (max - min) + min).toFixed(2);
    }

    function randItem(arr) {
        return arr[randInt(0, arr.length - 1)];
    }

    function randColor()
    {
        return [
            randInt(0, 360),    // hue
            randInt(40, 80),    // saturation
            randInt(20, 80),    // luminosity
            randFloat(0, 0.5)   // opacity
        ];
    }

    function diagonalPoints(num_points, y_height)
    {
        //  Height is how far the diagonal reaches above or below the horizontal.
        var x_delta = 100.0 / num_points;
        var y_delta = ((y_height * 2) / num_points);
        var x = 0, y = 35 + y_height;
        var points = [];
        for (var i = 0; i < num_points; i++) {
            points.push([
                randInt(x, x + x_delta) + randInt(-3, 3),
                randInt(y, y + y_delta) + randInt(-9, 9),
            ]);
            x += x_delta;
            y += y_delta;
        }
        return points;
    }

    function drawOneCircle(x, y, radius, h, s, v, opacity)
    {
        if (radius < 3) {
            //  Add an outline on smaller circles.
            return [
                '<circle ',
                'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ',
                'fill="hsla(' + h + ', ' + s + '%, 90%, ' + randFloat(0.3, opacity) + ')" ',
                '>',
                '</circle>',
                '<circle ',
                'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ',
                'fill="none" ',
                'stroke="white" ',
                'stroke-opacity="' + randFloat(0.0, (opacity))+ '" ',
                '>',
                '</circle>',
            ].join('');
        } else {
            //  Add a blur on larger circles.
            return [
                '<circle ',
                'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ',
                'fill="hsla(' + h + ', ' + s + '%, 90%, ' + randFloat(0.1, opacity * 0.5) + ')" ',
                'filter="url(#blur)" ',
                '>',
                '</circle>',
            ].join('');
        }
    }

    function drawCircles(num_points, sizes)
    {
        var y_height = randInt(3, 7);
        var points = diagonalPoints(num_points, y_height);
        var _ = '';
        for (var i=0; i < points.length; i++) {
            var p = points[i], hsv = randColor();
            //  ...p, radius, ...hsva
            var x = p[0], y = p[1], radius = randItem(sizes);
            var h = hsv[0], s = hsv[1], v = hsv[2], opacity = hsv[3];
            _ += drawOneCircle(x, y, radius, h, s, v, opacity);
        }
        return _;
    }

    function makeBokehSvg()
    {
        return [
            '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">',
            '<defs>',
            '<filter id="blur">',
            '<feGaussianBlur stdDeviation="4"></feGaussianBlur>',
            '</filter>',
            '</defs>',
            drawCircles(randInt(30, 40), LARGE_SIZES),
            drawCircles(randInt(45, 65), SMALL_SIZES),
            '</svg>'
        ].join('');
    }

    function setSvgBackground(selector)
    {
        if (!svgIsRendering) {
            svgIsRendering = true;

            var svg = makeBokehSvg();
            var encodedData = window.btoa(svg);
            var url = 'data:image/svg+xml;base64,' + encodedData;

            const target = document.querySelector(selector);
            if (target) {
                target.style.backgroundImage = "url(" + url + ")";
            }

            svgIsRendering = false;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {

        polyfillForBalanceText();

        setSvgBackground('#background');

        initSidebars();
        initProgress('#progress-meter');

        //  After sidebars are rendered:
        initThemes('.theme-button');
        initFullScreen('.fullscreen-button');
        initNavigation('.navigation-button', stopScrollDownIndicatorBlinking);

    });

})();
