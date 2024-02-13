/**
 * (Article Wiki)
 *
 * Generate an SVG Bokeh pattern to be applied as a background image.
 *
 * [NC 2024-02-10] Firefox has trouble with the large blurred circles. 
 */

const LARGE_SIZES = [3, 3, 3, 4, 5];
const SMALL_SIZES = [1, 1, 1, 1, 1, 1, 1, 2, 2];

let svgIsRendering = false;

function randInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1) + min);   
}

function randFloat(min, max) {
    return (Math.random() * (max - min) + min).toFixed(2);
}

function randItem(arr) {
    return arr[randInt(0, arr.length - 1)];
}

function randColor()
{
    return [
        randInt(0, 360),    // hue
        randInt(40, 80),    // saturation
        randInt(20, 80),    // luminosity
        randFloat(0, 0.5)   // opacity
    ];
}

function diagonalPoints(num_points, y_height)
{
    //  Height is how far the diagonal reaches above or below the horizontal.
    var x_delta = 100.0 / num_points;
    var y_delta = ((y_height * 2) / num_points);
    var x = 0, y = 35 + y_height;
    var points = [];
    for (var i = 0; i < num_points; i++) {
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
    if (radius < 3) {
        //  Add an outline on smaller circles.
        return [
            '<circle ',
            'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ',
            'fill="hsla(' + h + ', ' + s + '%, 90%, ' + randFloat(0.3, opacity) + ')" ',
            '>',
            '</circle>',
            '<circle ',
            'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ',
            'fill="none" ',
            'stroke="white" ',
            'stroke-opacity="' + randFloat(0.0, (opacity))+ '" ',
            '>',
            '</circle>',
        ].join('');
    } else {
        //  Add a blur on larger circles.
        return [
            '<circle ',
            'r="' + radius + '%" cx="' + x + '%" cy="' + y + '%" ',
            'fill="hsla(' + h + ', ' + s + '%, 90%, ' + randFloat(0.1, opacity * 0.5) + ')" ',
            'filter="url(#blur)" ',
            '>',
            '</circle>',
        ].join('');
    }
    return _;
}

function drawCircles(num_points, sizes)
{
    var y_height = randInt(3, 7);
    var points = diagonalPoints(num_points, y_height);
    var _ = '';
    for (var i=0; i < points.length; i++) {
        var p = points[i], hsv = randColor();
        //  ...p, radius, ...hsva
        var x = p[0], y = p[1], radius = randItem(sizes);
        var h = hsv[0], s = hsv[1], v = hsv[2], opacity = hsv[3];
        _ += drawOneCircle(x, y, radius, h, s, v, opacity);
    }
    return _;
}

function makeBokehSvg()
{
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">',
        '<defs>',
        '<filter id="blur">',
        '<feGaussianBlur stdDeviation="4"></feGaussianBlur>',
        '</filter>',
        '</defs>',
        drawCircles(randInt(30, 40), LARGE_SIZES),
        drawCircles(randInt(45, 65), SMALL_SIZES),
        '</svg>'
    ].join('');
}

function setSvgBackground(selector)
{
    if (!svgIsRendering) {
        svgIsRendering = true;

        var svg = makeBokehSvg();
        var encodedData = window.btoa(svg);
        var url = 'data:image/svg+xml;base64,' + encodedData;

        const target = document.querySelector(selector);
        if (target) {
            target.style.backgroundImage = "url(" + url + ")";
        }

        svgIsRendering = false;
    }
}

export {setSvgBackground};
