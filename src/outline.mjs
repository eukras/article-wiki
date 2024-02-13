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

export {getOutline};
