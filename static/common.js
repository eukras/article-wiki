$(document).ready(function() { 

    var offset = 220;
    var duration = 500;

    //  Scroll by percentage. Still slightly out of sync at the end of
    //  long sections. Works well enough. 

    $('#editor textarea').on('scroll', function() {
        var editTop = $(this).scrollTop();
        var editHeight = $(this)[0].scrollHeight - $(this).height() - 20;
        if (editHeight > 0) {
            var ratio = editTop / editHeight;
            var that = $('#editor main');
            var previewHeight = $(that)[0].scrollHeight - $(that).height();
            var previewTop = Math.floor(previewHeight * ratio);
            $(that).scrollTop(previewTop);
        }
    });

    //  Handy shortcut for editing.
    $('#editor textarea').on('keydown', function(e) {
        const SPACE = 32;
        const KEY_B = 66;
        const KEY_I = 73;
        const KEY_U = 85;
        if (e.ctrlKey) {
            if (e.keyCode == SPACE) {
                selectParagraph(this);
            } else if (e.keyCode == KEY_I) {
                insertAtCursor(this, '/', '/');
            } else if (e.keyCode == KEY_B) {
                insertAtCursor(this, '*', '*');
            } else if (e.keyCode == KEY_U) {
                insertAtCursor(this, '_', '_');
                return false;
            }
        }
    });

    //  On small screens, 'Edit' button switches back from #editor.mode-preview
    //  to #editor.mode-edit. CSS will show and hide page elements accordingly.

    $('#editor #btn-edit').click(function () {
        $('#editor.mode-preview')
            .removeClass('mode-preview')
            .addClass('mode-edit');
    });

    //  Simple theme cycling.
    $('.button-themes').click(function () {
        cycleTheme();
    });

    //  A compressed version of Adobe's jquery.balanceText.js, which operates
    //  on the 'balance-text' class. This is a polyfill for `wrap-text:
    //  balance`, which will appear in CSS Text Level 4. Note this deletes
    //  links from the rewrapped text, and probably other tags too.

    !function(a){"use strict";function d(){this.reset()}function k(){a(".balance-text").balanceText()}var b=document.documentElement.style,c=b.textWrap||b.WebkitTextWrap||b.MozTextWrap||b.MsTextWrap||b.OTextWrap;d.prototype.reset=function(){this.index=0,this.width=0};var e=function(a){return Boolean(a.match(/^\s$/))},f=function(b){b.find('br[data-owner="balance-text"]').replaceWith(document.createTextNode(" "));var c=b.find('span[data-owner="balance-text"]');if(c.length>0){var d="";c.each(function(){d+=a(this).text(),a(this).remove()}),b.html(d)}},g=function(a){return b=a.get(0).currentStyle||window.getComputedStyle(a.get(0),null),"justify"===b.textAlign},h=function(b,c,d){c=a.trim(c);var e=c.split(" ").length;if(c+=" ",2>e)return c;var f=a("<span></span>").html(c);b.append(f);var g=f.width();f.remove();var h=Math.floor((d-g)/(e-1));return f.css("word-spacing",h+"px").attr("data-owner","balance-text"),a("<div></div>").append(f).html()},i=function(a,b){return 0===b||b===a.length||e(a.charAt(b-1))&&!e(a.charAt(b))},j=function(a,b,c,d,e,f,g){for(var h;;){for(;!i(b,f);)f+=e;if(a.text(b.substr(0,f)),h=a.width(),0>e?d>=h||0>=h||0===f:h>=d||h>=c||f===b.length)break;f+=e}g.index=f,g.width=h};a.fn.balanceText=function(){return c?this:this.each(function(){var b=a(this),c=5e3;f(b);var e="";b.attr("style")&&b.attr("style").indexOf("line-height")>=0&&(e=b.css("line-height")),b.css("line-height","normal");var i=b.width(),k=b.height(),l=b.css("white-space"),m=b.css("float"),n=b.css("display"),o=b.css("position");b.css({"white-space":"nowrap","float":"none",display:"inline",position:"static"});var p=b.width(),q=b.height(),r="pre-wrap"===l?0:q/4;if(i>0&&p>i&&c>p){for(var s=b.text(),t="",u="",v=g(b),w=Math.round(k/q),x=w;x>1;){var y=Math.round((p+r)/x-r),z=Math.round((s.length+1)/x)-1,A=new d;j(b,s,i,y,-1,z,A);var B=new d;z=A.index,j(b,s,i,y,1,z,B),A.reset(),z=B.index,j(b,s,i,y,-1,z,A);var C;C=0===A.index?B.index:i<B.width||A.index===B.index?A.index:Math.abs(y-A.width)<Math.abs(B.width-y)?A.index:B.index,u=s.substr(0,C),v?t+=h(b,u,i):(t+=u.trimRight(),t+='<br data-owner="balance-text" />'),s=s.substr(C),x--,b.text(s),p=b.width()}v?b.html(t+h(b,s,i)):b.html(t+s)}b.css({position:o,display:n,"float":m,"white-space":l,"line-height":e})})},a(window).ready(k),a(window).resize(k)}(jQuery);

    setSvgBackground();

    /**
     * Move a copy of the table of contents into the nav popover
     */

    $('.table-of-contents').clone().appendTo('#popover-table-of-contents');

    $('.href-button').click(function() {
       location.href = $(this).attr('href');
    });

    /**
     * When the table of contents is clicked, make sure any popover closes.
     */
    $('#popover-table-of-contents a').click(function(event) {
        //  allow event to continue
        toggleMenuPopover();
    });

});

function toggleMenuPopover() {
    //  No popovers: show contents
    //  Popovers: hide them
    const num_contents = $('div#popover-contents-modal:visible').length;
    const num_comments = $('div#popover-comment-modal:visible').length;
    if (num_comments > 0 || num_contents > 0) {
        $('div#popover-contents-modal').hide();
    } else {
        $('div#popover-contents-modal').show();
    }
    $('div#popover-comment-modal').hide();
    //  $('div#popover-comment-button').hide();
    $('div#popover-comment-close').hide();
}

function cleanupText(s) { 
    return s.replace(/…/g, '...')
            .replace(/—/g, '---')
            .replace(/–/g, '--')
            .replace(/(\d+)--(\d+)/g, '$1-$2')  // <-- No '--' between numbers
            .replace(/[“”]/g, '"')
            .replace(/[‘’]/g, "'")
            .replace(/&[#A-Za-z0-9]+;/gi, (entity, pos, text) => {
                span = document.createElement('span');
                span.innerHTML = entity;
                return span.innerText;
            })
            ;
}

//  ----------------------------------------
//  SVG Bokeh Background
//  ----------------------------------------

//  https://codepen.io/dudleystorey/pen/GJemEX

$("body").click(function(event) { 
    setSvgBackground();
});

let svgIsRendering = false;

function setSvgBackground()
{
    if (!svgIsRendering) {
        svgIsRendering = true;
        svg = makeBokehSvg()
        var encodedData = window.btoa(svg);
        var url = 'data:image/svg+xml;base64,' + encodedData;
        $("#background").css('background-image', "url(" + url + ")");
        svgIsRendering = false;
    }
}

function randInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1) + min);   
}

function randFloat(min, max) {
    return (Math.random() * (max - min) + min).toFixed(2);
}

function randItem(arr) {
    return arr[randInt(0, arr.length - 1)]
}

function randHsv()
{
    return [
        randInt(0, 360),
        randInt(40, 80),
        randInt(20, 80),
        randFloat(0, 0.5)
    ]
}

function diagonalPoints(num_points, y_height)
{
    //  Height is how far the diagonal reaches above or below the horizontal.
    var x_delta = 100.0 / num_points;
    var y_delta = ((y_height * 2) / num_points);
    var x = 0, y = 35 + y_height;
    var points = [];
    for (i = 0; i < num_points; i++) {
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
    var _ = ''
    if (radius < 3) {
        //  Add an outline on smaller circles.
        _ += '<circle '
        _ += 'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ';
        _ += 'fill="hsla(' + h + ', ' + s + '%, 90%, ' + randFloat(0.3, opacity) + ')" ';
        _ += '>';
        _ += '</circle>';
        _ += '<circle '
        _ += 'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ';
        _ += 'fill="none" ';
        _ += 'stroke="white" ';
        _ += 'stroke-opacity="' + randFloat(0.0, (opacity))+ '" ';
        _ += '>';
        _ += '</circle>';
    } else {
        //  Add a blur on larger circles.
        _ += '<circle '
        _ += 'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ';
        _ += 'fill="hsla(' + h + ', ' + s + '%, 90%, ' + randFloat(0.1, opacity * 0.5) + ')" ';
        _ += 'filter="url(#blur)" '
        _ += '>';
        _ += '</circle>';
    }
    return _;
}

function drawCircles(num_points, sizes)
{
    var y_height = randInt(3, 7);
    var points = diagonalPoints(num_points, y_height);
    var _ = '';
    for (var i=0; i < points.length; i++) {
        var p = points[i], hsv = randHsv();
        var x = p[0], y = p[1], radius = randItem(sizes);
        var h = hsv[0], s = hsv[1], v = hsv[2], opacity = hsv[3];
        _ += drawOneCircle(x, y, radius, h, s, v, opacity);
    }
    return _;
}

function makeBokehSvg()
{
    var _ = ''
    _ += '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">';
    _ += '<defs>';
    _ += '<filter id="blur">';
    _ += '<feGaussianBlur stdDeviation="4"></feGaussianBlur>';
    _ += '</filter>';
    _ += '</defs>';   

    _ += drawCircles(randInt(30, 40), sizes=[3, 3, 3, 4, 5]);
    _ += drawCircles(randInt(45, 65), sizes=[1, 1, 1, 1, 1, 1, 1, 2, 2]);
 
    _ += '</svg>';

    return _;
}

//  ----------------------------------------
//  Theme switcher 
//  ----------------------------------------

function getThemes() {
    return ['default', 'dark'];
}

function getThemeClasses() {
    return getThemes().map(theme => {
        return "theme-" + theme;
    });
}

function cycleTheme() {
    classes = getThemeClasses();
    html = $('html');
    for (i = 0; i < classes.length; i++) {
        if (html.hasClass(classes[i])) {
            html.removeClass(classes[i]);
            new_theme = classes[(i + 1) % classes.length];
            html.addClass(new_theme);
            $.cookie('article-wiki-theme', new_theme, {'path': '/'});
            setSvgBackground()
            return;
        }
    }
    html.addClass(classes[0]);  // <-- If no matches, use first theme
    setSvgBackground()
}



//  ----------------------------------------
//  Keystroke and editing functions
//  ----------------------------------------

function selectParagraph(textarea)
{
    if (textarea.selectionStart == textarea.selectionEnd) {
        //  No selection; create one
        let caret = textarea.selectionStart;
        let text = textarea.value;
        let prevEol = text.lastIndexOf('\n\n', caret);
        let nextEol = text.indexOf('\n\n', caret - 2);
        let startParagraph = prevEol == -1 ? 0 : prevEol + 1;
        let endParagraph = nextEol == -1 ? text.length : nextEol + 1;
        textarea.setSelectionRange(startParagraph, endParagraph);
    }
}

function insertAtCursor(textarea, prepend, append='') {
    if (document.selection) {
        textarea.focus();
        document.selection.createRange().text = prepend + document.selection.createRange().text + append;
    } else if (textarea.selectionStart || textarea.selectionStart == '0') {
        var startPos = textarea.selectionStart;
        var endPos = textarea.selectionEnd;
        textarea.value = textarea.value.substring(0, startPos) + prepend + textarea.value.substring(startPos, endPos) + append + textarea.value.substring(endPos, textarea.value.length);
        //  textarea.focus();
        textarea.selectionStart = startPos + prepend.length;
        textarea.selectionEnd = endPos + prepend.length;
    } 
}
