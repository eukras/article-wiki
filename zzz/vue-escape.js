//  Displays an 'ESC' button. When ESC is pressed, toggle a full-screen overlay
//  that shows selected elements of the page. Helps access menu and navigation
//  items on long pages.

export default {
    props: {
        selector: String, // Selectors for DOM elements to copy into the menu
    },
    template: `
        <nav
            @click="toggleEscape()"
            :style="styleButton()"
            class="no-print"
        >
            <i class="fa fa-bars"></i> <span class="no-compact">ESC</span>
        </nav>
        <div
            v-if="showMenu"
            :style="styleModal()"
        >
            <div
                @click="toggleEscape()"
                :style="styleMenu()"
            >
                <div class="text-center">
                    <i>When reading an article, the Escape menu<br/>
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
        styleButton() {
            return {
                'fontFamily': 'sans-serif',
                'position': 'fixed',
                'top': 0,
                'left': 0,
                'textDecoration': 'none',
                'fontSize': '0.9rem',
                'padding': '0.9rem',
                'opacity': 0.4,
                'zIndex': 20,
                'textAlign': 'left',
                'cursor': 'pointer',
                'userSelect': 'none',
            };
        },
        styleModal() {
            return {
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'start',
                'position': 'fixed',
                'top': 0,
                'left': 0,
                'width': '100vw',
                'height': '100vh',
                'overflowY': 'auto',
                'backgroundColor': 'white',
            };
        },
        styleMenu() {
            return {
                'width': '44rem',
                'padding': '2rem 1rem',
            };
        },

    },
    mounted() {
        document.addEventListener('keydown', this.handleKeyDown);
    },
    unmounted() {
        document.removeEventListener('keydown', this.handleKeyDown);
    }
}
