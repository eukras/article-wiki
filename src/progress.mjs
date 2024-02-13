/**
 * When scrolling, update a progress value which shows the percentage position
 * in the page.
 */

function handleScroll(selector) {
    const scrolledPixels = window.scrollY,
          documentPixels = document.body.scrollHeight,
          viewportPixels = window.innerHeight;
    const scrollPercent = Math.round(
        (scrolledPixels / (documentPixels - viewportPixels)) * 100
    );
    const readout = document.querySelector(selector);
    if (readout !== null) {
        readout.innerHTML = scrollPercent + '%';
    }
};

function initProgress(selector) 
{
    window.addEventListener('scroll', () => handleScroll(selector));
    handleScroll(selector);
}

export {initProgress};
