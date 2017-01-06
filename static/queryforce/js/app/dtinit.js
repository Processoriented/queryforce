define(['jquery', 'datatables'],

function ( $ ) {
    'use strict';

    var DataTable = function ( element, options ) {
        this.init('datatable', element, options);
    };

    DataTable.prototype = {

        constructor: DataTable,

        init: function ( type, element, options ) {
            this.type = type;
            this.$element = $(element);
            this.name = this.$element.attr('id');
            this.settings = this.getOptions(options);

            this.createTable(options);
        },

        createTable: function ( options ) {
            this.$table = this.$element.dataTable(this.settings);
        },

        getOptions: function ( options ) {
            return options;
        }
    };
    return DataTable;
});