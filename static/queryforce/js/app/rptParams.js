$(document).ready(function(){
    $('#result_table').hide();
    var rules = []
    $('#result_table > thead > tr > th').each(function(){ 
        rules.push({data: $(this).attr('data')});
    });
    var raw = $('#tbldv').attr('data');

    if ($("#params_div").attr('data') == 'None') {
        $('#result_table').show();
        $('#result_table').DataTable({
            "ajax": raw,
            "columns": rules
        });
    }

    $('#set_params').click(function( event ){
        event.preventDefault();
        var form_data = $('#params_form').serializeArray();
        var param_data = {}
        $(form_data).each(function(){
            var fd_obj = $(this)[0].name.split('-');
            if (fd_obj.length == 3) {
                var param_datum = param_data[fd_obj[1]] || {};
                param_datum[fd_obj[2]] = $(this)[0].value;
                param_data[fd_obj[1]] = param_datum;
            }
        });
        var params_obj = {}
        $(param_data).each(function(){
            var param_obj = {};
            param_obj['operator'] = $(this)[0][0]['operator'];
            param_obj['value'] = $(this)[0][0]['value'];
            params_obj[$(this)[0][0]['parameter']] = param_obj;
        });
        var purl = raw.replace('raw', 'param');
        var rdata = {};
        rdata['ps'] = params_obj;
        rdata['csrfmiddlewaretoken'] = form_data[0]['value'];
        $('#result_table').show();
        var table = $('#result_table').DataTable({
            ajax: { 
                url: purl,
                type: "POST",
                data: rdata},
            columns: rules
        });
        var bc = $('.col-sm-6:eq(1) > div', table.table().container() )
        new $.fn.dataTable.Buttons( table, { 
            buttons: [
                {
                    extend: 'excelHtml5',
                    text: 'Export',
                    filename: $('#report_name').text()
                }
            ] 
        } );
        var btn = table.buttons( 0, null ).container();
        $(bc).append( btn );
    });
});