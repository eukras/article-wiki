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
    document.addEventListener('click', function (event) {
        const button = event.target.closest(buttonSelector);
        if (button !== null) {
            toggleFullScreen();
        }
    });
}

export {initFullScreen};
