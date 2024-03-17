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


function initEditor() {

    //  Scroll by percentage. Still slightly out of sync at the end of
    //  long sections. Works well enough. 

    const editor = document.querySelector('#editor');
    const textarea = document.querySelector('#editor textarea');
    const preview = document.querySelector('#editor main');
    const editButton = document.querySelector('#editor #btn-edit');

    if (textarea && preview) {

        textarea.focus();

        textarea.addEventListener('scroll', () => {
            var editTop = textarea.scrollTop();
            var editHeight = textarea.scrollHeight - textarea.height - 20;
            if (editHeight > 0) {
                var ratio = editTop / editHeight;
                var previewHeight = preview.scrollHeight - preview.height();
                var previewTop = Math.floor(previewHeight * ratio);
                preview.scrollTop(previewTop);
            }
        });

        //  Handy shortcuts for editing.
        textarea.addEventListener('keydown', (_) => {
            if (_.ctrlKey) {
                if (_.key == ' ') {
                    selectParagraph(textarea);
                } else if (_.key == 'i') {
                    insertAtCursor(textarea, '/', '/');
                } else if (_.key == 'b') {
                    insertAtCursor(textarea, '*', '*');
                } else if (_.key == 'u') {
                    insertAtCursor(textarea, '_', '_');
                    return false;
                }
            }
        });

    }

    if (editButton) {

        //  On small screens, 'Edit' button switches back from #editor.mode-preview
        //  to #editor.mode-edit. CSS will show and hide page elements accordingly.

        editButton.addEventListener('click', (_) => {
            _.stopPropagation();
            editor.classList.remove('mode-preview');
            editor.classList.add('mode-edit');
        });

    }

}

export { initEditor };
