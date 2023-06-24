//  Show a 'TOP' button that contains the current percentage position
//  in the page. Designed for showing reading progress in long documents.
//  
//  Part of Article Wiki ().


export default {
    template: `
        <nav
            @click="scrollToTop()"
            :style="style()"
            class="no-print"
        >
            <span class="no-compact">{{ scrollText }}</span> <i class="fa fa-arrow-up"></i>
        </nav>
    `,
    data() {
        return {
            scrollPercent: 0,
        };
    },
    computed: {
        scrollText() {
            const scaledPixelWidth = $(document).width();
            if (scaledPixelWidth > 768) {
                if (this.scrollPercent > 99) { 
                    return 'END'
                } else if (this.scrollPercent > 1) { 
                    return this.scrollPercent + '%'; 
                } else { 
                    return 'TOP'; 
                }
            } else { 
                return '...'; 
            }
        }
    },
    methods: {
        handleScroll(event) {
            const s = $(window).scrollTop(),
                  d = $(document).height(),
                  c = window.innerHeight;
            this.scrollPercent = Math.round((s / (d-c)) * 100);
        },
        scrollToTop() {
            window.scrollTo(0,0);
        },
        style() {
            return {
                'position': 'fixed',
                'bottom': 0,
                'right': 0,
                'fontFamily': 'sans-serif',
                'textDecoration': 'none',
                'fontSize': '0.9rem',
                'padding': '1rem',
                'opacity': 0.4,
                'zIndex': 20,
                'cursor': 'pointer',
                'userSelect': 'none',
            };
        },
    },
    mounted() {
        window.addEventListener('scroll', this.handleScroll);
    },
    unmounted() {
        window.removeEventListener('scroll', this.handleScroll);
    }
}
