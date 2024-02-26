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
};

function initProgress(selector) 
{
    window.addEventListener('scroll', () => handleScroll(selector));
    handleScroll(selector);
}

export {initProgress};
