import Comment from './vue-feedback.js';

const App = {
  el: 'main',
  components: {
    'vue-comment': Comment,
  },
  template: `
    <vue-comment email-address="nigel@chapman.id.au" email-subject="Feedback" />
  `,
}

window.addEventListener('load', () => {
    if (typeof Vue !== 'undefined') {
        let app = Vue.createApp(App);
        app.mount('#app');
    }
});
