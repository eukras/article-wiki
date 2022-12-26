//  Show a 'TOP' button that contains the current percentage position
//  in the page. Designed for showing location in long documents.

//  Suggested SCSS:
//  #progress {
//      font-family: $fontFamilySansSerif;
//      bottom: 0;
//      right: 0;
//      position: fixed;
//      text-decoration: none;
//      font-size: $fontSizeMinus1;
//      padding: 1em;
//      opacity: 0.4;
//      z-index: 20;
//      cursor: pointer;
//      user-select: none;
//  }

export default {
    template: `
        <nav
            id="progress"
            @click="scrollToTop()"
        >
            {{ scrollText }} <i class="fa fa-arrow-up"></i>
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
    },
    mounted() {
        window.addEventListener('scroll', this.handleScroll);
    },
    unmounted() {
        window.removeEventListener('scroll', this.handleScroll);
    }
}
