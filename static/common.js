document.addEventListener("DOMContentLoaded", () => {

    //  var offset = 220;
    //  var duration = 500;

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

    $('.href-button').click(function() {
       location.href = $(this).attr('href');
    });

});

/**
 *
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
*/

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
//  SVG creation for outliner.
//  ----------------------------------------

function read_contents(text) {
    const lines = text.split('\n');
    const outline = lines.filter(line => line.startsWith('- '));
    return outline
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
