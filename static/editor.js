/**
 *
 * THIS IS UNUSED AND UNTESTED -- Aspirational code only.
 *
 * Editor functions adapted from splitbrain and docuwiki; require jQuery.
 * 
 * Required functions:
 *
 * - keyTrigger:
 *   - detect and respond to keydown events while in the textarea.
 * - insertText:
 *   - Effectively paste a template at the cursor. (Or as new paragraph?)
 * - wrapText: 
 *   - If selection, wrap with start and end text. Caret goes to end.
 *   - If in word, selectWord() and wrap. Caret goes to end.
 *   - Otherwise, insert and select sample text, wrapped.
 * - continueIndent:
 *   - On return, start next line with control characters from preceding line.
 *   - selectLine()?, getControlCharacters()
 *
 * Or maybe just -> https://github.com/jaywcjlove/hotkeys
 *
 */

function selectionClass() 
{
    this.start     = 0;
    this.end       = 0;
    this.obj       = null;
    this.scroll    = 0;
    this.fix       = 0;

    this.getLength = function() {
        return this.end - this.start;
    };

    this.getText = function() {
        return (!this.obj) ? ''
                           : this.obj.value.substring(this.start,this.end);
    };
}

/**
 * Get current selection/cursor position in a given textArea
 *
 * @link   http://groups.drupal.org/node/1210
 * @author Andreas Gohr <andi@splitbrain.org>
 * @link   http://linebyline.blogspot.com/2006/11/textarea-cursor-position-in-internet.html
 * @returns object - a selection object
 */
function getSelection(textArea)
{
    var sel = new selectionClass();
    textArea.focus();
    sel.obj   = textArea;
    sel.start  = textArea.selectionStart;
    sel.end    = textArea.selectionEnd;
    sel.scroll = textArea.scrollTop;
    return sel;
}

/**
 * Set the selection
 *
 * You need to get a selection object via getSelection() first, then modify the
 * start and end properties and pass it back to this function.
 *
 * @link http://groups.drupal.org/node/1210
 * @author Andreas Gohr <andi@splitbrain.org>
 * @param {selectionClass} selection  a selection object as returned by getSelection()
 */
function setSelection(selection)
{
    selection.obj.setSelectionRange(selection.start, selection.end);
    if (selection.scroll) selection.obj.scrollTop = selection.scroll;
}

/**
 * Inserts the given text at the current cursor position or replaces the current
 * selection
 *
 * @author Andreas Gohr <andi@splitbrain.org>
 * @param {string}  text           the new text to be pasted
 * @param {selectionClass}  selection     selection object returned by getSelection
 * @param {int}     opts.startofs  number of charcters at the start to skip from new selection
 * @param {int}     opts.endofs    number of characters at the end to skip from new selection
 * @param {boolean} opts.nosel     set true if new text should not be selected
 */
function pasteText(selection, text, opts)
{
    if (!opts) opts = {};

    selection.obj.value =
        selection.obj.value.substring(0, selection.start) + text +
        selection.obj.value.substring(selection.end, selection.obj.value.length);
    selection.end = selection.start + text.length;

    // modify the new selection if wanted
    if (opts.startofs) selection.start += opts.startofs;
    if (opts.endofs)   selection.end   -= opts.endofs;

    // no selection wanted? set cursor to end position
    if (opts.nosel) selection.start = selection.end;

    setSelection(selection);
}


/**
 * Format selection
 *
 * Apply tagOpen/tagClose to selection in textarea, use sampleText instead
 * of selection if there is none.
 *
 * @author Andreas Gohr <andi@splitbrain.org>
 */
function insertTags(textAreaID, tagOpen, tagClose, sampleText)
{
    var txtarea = jQuery('#' + textAreaID)[0];

    var selection = getSelection(txtarea);
    var text = selection.getText();
    var opts;

    // don't include trailing space in selection
    if (text.charAt(text.length - 1) == ' ') {
        selection.end--;
        text = selection.getText();
    }

    if (!text) {
        // nothing selected, use the sample text and select it
        text = sampleText;
        opts = {
            startofs: tagOpen.length,
            endofs: tagClose.length
        };
    } else {
        // place cursor at the end
        opts = {
            nosel: true
        };
    }

    // surround with tags
    text = tagOpen + text + tagClose;

    // do it
    pasteText(selection, text, opts);
}

/**
 * Wraps around pasteText() for backward compatibility
 *
 * @author Andreas Gohr <andi@splitbrain.org>
 */
function insertAtCaret(textAreaID, text)
{
    var txtarea = jQuery('#' + textAreaID)[0];
    var selection = getSelection(txtarea);
    pasteText(selection,text, {nosel: true});
}

/**
 * The DokuWiki editor features
 *
 * These are the advanced features of the editor. It does NOT contain any
 * code for the toolbar buttons and it functions. See toolbar.js for that.
 */

function initKeyHandler()
{
	var $editor = jQuery('textarea');
	if ($editor.length === 0) {
		return;
	}
	$editor.keydown(editor.keyHandler);
}

/**
 * Make intended formattings easier to handle
 *
 * Listens to all key inputs and handle indentions
 * of lists and code blocks
 *
 * Currently handles space, backspace, enter and
 * ctrl-enter presses
 *
 * @author Andreas Gohr <andi@splitbrain.org>
 * @fixme handle tabs
 * @param event e - the key press event object
 */
function keyHandler(e) {

	console.log("Key Code: " + e.keyCode)
	RETURN = 13

	var selection = getSelection(this);
	if (selection.getLength() > 0) {
		return; //there was text selected, keep standard behavior
	}
	var search    = "\n"+this.value.substr(0,selection.start);
	var linestart = Math.max(search.lastIndexOf("\n"),
							 search.lastIndexOf("\r")); //IE workaround
	search = search.substr(linestart);

	if (e.keyCode == 13) { // Enter
		// keep current indention for lists and code
		var match = search.match(/(\n  +([\*-] ?)?)/);
		if (match) {
			var scroll = this.scrollHeight;
			var match2 = search.match(/^\n  +[\*-]\s*$/);
			// Cancel list if the last item is empty (i. e. two times enter)
			if (match2 && this.value.substr(selection.start).match(/^($|\r?\n)/)) {
				this.value = this.value.substr(0, linestart) + "\n" +
							 this.value.substr(selection.start);
				selection.start = linestart + 1;
				selection.end = linestart + 1;
				setSelection(selection);
			} else {
				insertAtCarret(this.id,match[1]);
			}
			this.scrollTop += (this.scrollHeight - scroll);
			e.preventDefault(); // prevent enter key
			return false;
		}
	}

};

jQuery(initEditor);
