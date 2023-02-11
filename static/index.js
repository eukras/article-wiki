import Progress from './vue-progress.js';
import Escape from './vue-escape.js';
import Comment from './vue-feedback.js';

const App = {
  el: 'main',
  components: {
    'vue-progress': Progress,
    'vue-escape': Escape,
    'vue-comment': Comment,
  },
  template: `
    <vue-progress />
    <vue-escape selector=".button-menu,.table-of-contents:first-of-type" />
    <vue-comment email-address="nigel@chapman.id.au" email-subject="Feedback" />
  `,
}

window.addEventListener('load', () => {
    let app = Vue.createApp(App);
    app.mount('#app');
})
