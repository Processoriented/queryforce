$(document).ready(function(){
    var rules = []
    $('#result_table > thead > tr > th').each(function(){ 
        rules.push({data: $(this).attr('data')});
    });
    var raw = $('#tbldv').attr('data')
    $('#result_table').DataTable({
        "ajax": raw,
        "columns": rules
    });
});