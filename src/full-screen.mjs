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
            document.webkitCancelFullScreen()
        } else if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen();
        } else {
            document.documentElement.webkitRequestFullScreen();
        }
    }
}

function initFullScreen(buttonSelector)
{
    const buttons = document.querySelectorAll(buttonSelector); // one only
    for (const button of buttons) {
        button.addEventListener('click', function (event) {
            toggleFullScreen();
            event.preventDefault();
        }, true);  // <-- Capture
    }
}

export {initFullScreen};
