$(function() {
   var app = new Vue({
      el: '#app',
      data: {
         hostels: [],
         form: {
            loc_query: ""
         }
      },
      created() {
         var _this = this;
         var source = new EventSource(appConfig.sse_stream);

         source.addEventListener('search_results', function(event) {
            console.log("Received search_results");
            _this.hostels.push(JSON.parse(event.data));
         }, false);

         source.addEventListener('error', function(event) {
            console.log("Failed to connect to event stream. Is Redis running?");
         }, false);

         // keep stream alive
         setInterval(function(){
            $.get(appConfig.endpoints.ping);
         }, 27000);
      },

      methods: {
         search: function(event) {
            var posting = $.get(appConfig.endpoints.search, this.form);
         }
      }
   });
   Vue.use(Vue2Filters);
   window.vue = app;
});
