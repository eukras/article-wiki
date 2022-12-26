//  Displays an 'ESC' button. When ESC is pressed, toggle a full-screen overlay
//  that shows selected elements of the page. Helps access menu and navigation
//  items on long pages.
//
//  Styles: 
//  nav#escape: the button, suggest top-right
//  div#escape-modal: the full-screen overlay container, fixed position
//  div#escape-menu: the menu within the overlay

export default {
    props: {
        selector: String, // Selectors for DOM elements to copy into the menu
    },
    template: `
        <nav
            id="escape"
            @click="toggleEscape()"
        >
            <i class="fa fa-bars"></i> ESC
        </nav>
        <div
            v-if="showMenu"
            id="escape-modal"
        >
            <div
                id="escape-menu"
                @click="toggleEscape()"
            >
                <div class="text-center">
                    <i>When reading an article, the ESC button<br/>
                    shows you the table of contents.</i>
                </div>
                <div
                    v-for="elem in elements"
                    v-html="elem"
                >
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            showMenu: false,
            elements: [],
        };
    },
    created() {
        console.log(this.selector);
        var elements = document.querySelectorAll(this.selector);
        elements.forEach((elem) => this.elements.push(elem.outerHTML));
    },
    methods: {
        handleKeyDown(event) {
            if (event.key === 'Escape') {
                const isNotCombinedKey = !(event.ctrlKey || event.altKey || event.shiftKey);
                if (isNotCombinedKey) {
                    this.toggleEscape();
                }
            }
        },
        toggleEscape() {
            this.showMenu = !this.showMenu;
        },
    },
    mounted() {
        document.addEventListener('keydown', this.handleKeyDown);
    },
    unmounted() {
        document.removeEventListener('keydown', this.handleKeyDown);
    }
}
