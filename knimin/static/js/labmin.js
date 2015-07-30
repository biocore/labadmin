// http://stackoverflow.com/a/20354786
function iframeform(url)
{
    var object = this;
    object.time = new Date().getTime();
    object.form = $('<form action="'+url+'" method="POST" style="display:none;" id="form'+object.time+'" name="form'+object.time+'"></form>');

    object.addParameter = function(parameter,value)
    {
        $("<input type='hidden' />")
         .attr("name", parameter)
         .attr("value", value)
         .appendTo(object.form);
    }

    object.send = function()
    {
        $( "body" ).append(object.form);
        object.form.submit();
        iframe.load(function(){  $('#form'+$(this).data('time')).remove();  $(this).remove();   });
    }
}