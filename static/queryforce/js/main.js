requirejs.config({
    baseUrl: '/static/queryforce/js/lib',
    paths: {
        app: '../app'
        //,
        // datatables: '../lib/datatables',
        // "datatables.net": "../lib/datatables"
    }
});

// requirejs(['jquery','bootstrap','datatables', 'app/rptParams'], function( $ ) {});

requirejs(['jquery'], function ( $ ) {
    require(['bootstrap']);
    var jsreqs = $('.templatehl').attr('data');
    console.log(jsreqs);
    jsreqs = jsreqs.replace("['",'').replace("']",'').split("', '");
    require(jsreqs);
});