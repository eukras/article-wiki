import Progress from './progress.js';
import Escape from './escape.js';

const App = {
  el: 'main',
  components: {
    'vue-progress': Progress,
    'vue-escape': Escape,
  },
  template: `
    <vue-progress />
    <vue-escape :selector='".button-menu,.table-of-contents:first-of-type"' />
  `,
}

window.addEventListener('load', () => {
    let app = Vue.createApp(App);
    app.mount('#app');
})
