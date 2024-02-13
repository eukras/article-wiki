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

export {initOptionHandler};
