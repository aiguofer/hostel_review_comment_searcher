$(function() {
   var app = new Vue({
      el: '#app',
      data: {
         hostels: [],
         form: {
            loc_query: "",
         },
         keyword: "",
      },
      mixins: [Vue2Filters.mixin],
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
            this.hostels = [];
            var posting = $.get(appConfig.endpoints.search, this.form);
         },
         has_keyword(keyword, text) {
            return RegExp(keyword, "i").exec(text) !== null;
         },
         find_keyword(keyword, text) {
            if(!keyword) {
               return text;
            }
            var replaced = text.replace(new RegExp(keyword, "gi"), match => {
               return '<span style="background-color:yellow"">' + match + '</span>';
            });
            return replaced != text ? replaced : null;
         }
      }
   });

   window.vue = app;
});
