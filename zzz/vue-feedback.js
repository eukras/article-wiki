//  Show a 'comment' button when text has been selected. It should be a mailto
//  link for any rel=me address in the page, and should fill the email with a
//  the quoted text.


const debounce = (callback, msDelay = 100) => {
  let timeoutId
  return (...args) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => {
      timeoutId = null
      callback(...args)
    }, msDelay)
  }
}

export default {
    template: `
        <div
            v-if="emailAddress && selectedText !== ''"
            :title="selectedText"
            :style="styleCircle()"
            class="no-print"
        >
            <a
                :href="emailLink"
                target="_blank"
                :style="styleIcon()"
            >
                <i
                    class="fa fa-comment"
                    style="color: inherit"
                ></i>
            </a>
        </div>
    `,
    props: {
        emailAddress: {
            type: String,
            required: true,
        },
        emailSubject: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            selectedText: '',
        };
    },
    computed: {
        emailBody() {
            return [
                "SELECTED TEXT:",
                this.selectedText,
                "COMMENT:",
                "..."
            ].join("\n\n");
        },
        emailLink() {
            return [
                'mailto:', this.emailAddress,
                '?subject=', encodeURIComponent(this.emailSubject),
                '&body=', encodeURIComponent(this.emailBody),
            ].join('');
        },
    },
    methods: {
        handleSelection(event) {
            const text = document.getSelection().toString().trim();
            if (text.length > 3 && text.length < 1000) {
                this.selectedText = text.length > 997
                    ? text.slice(0, 997) + '...'
                    : text;
            } else {
                this.selectedText = '';
            }
        },
        styleCircle() {
            return {
                'position': 'fixed',
                'top': '2rem',
                'right': '2rem',
                'width': '2rem',
                'height': '2rem',
                'border': 'solid .2rem white',
                'borderRadius': '50%',
                'boxShadow': '0 0 1rem #88888888',
                'backgroundColor': 'purple',
                'padding': '1rem',
                'zIndex': 20,
                'cursor': 'pointer',
                'userSelect': 'none',
            };
        },
        styleIcon() {
            return {
                'fontSize': '2rem',
                'cursor': 'pointer',
                'textDecoration': 'none',
                'userSelect': 'none',
                'color': 'white',
            };
        },
    },
    mounted() {
        document.onselectionchange = debounce((e) => this.handleSelection(e));
    },
    unmounted() {
        document.onselectionchange = undefined;
    },
}
