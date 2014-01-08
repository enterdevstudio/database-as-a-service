(function($) {


    /**
     * setup JQuery's AJAX methods to setup CSRF token in the request before sending it off.
     * http://stackoverflow.com/questions/5100539/django-csrf-check-failing-with-an-ajax-post-request
     */
     
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = $.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
     
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
     
    $.ajaxSetup({
         beforeSend: function(xhr, settings) {
             if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                 // Only send the token to relative URLs i.e. locally.
                 xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
             }
         }
    });

    var DatabaseInfra = function() {
        // this.engine_changed();
    };

    DatabaseInfra.prototype = {
        engine_changed: function() {
            this.update_components();
        },
        update_components: function() {
            var el = $("#id_engine");
            var engine_id = el.val() || "none";
            var engine_name = $('#id_engine :selected').text() || "none";

            if (engine_name.match(/mongo/g)) {
                this.hide_endpoint();
            } else {
                if (engine_id == "none") {
                    this.hide_endpoint();
                } else {
                    this.show_endpoint();
                };
            };
        },
        hide_endpoint: function() {
            var endpoint = $(".control-group.field-endpoint");
            if (endpoint.is(":visible")) {
                endpoint.hide();
            };
        },
        show_endpoint: function() {
            var endpoint = $(".control-group.field-endpoint");
            if (! endpoint.is(":visible")) {
                endpoint.show();
            };
        },
    };
    
    // Document READY
    $(function() {
        
        var databaseinfra = new DatabaseInfra();
        
        //hide endpoint
        databaseinfra.hide_endpoint();
        
        // 
        $("#id_engine").on("change", function() {
            // alert("engine change");
            databaseinfra.engine_changed();
        });

    });

})(django.jQuery);
