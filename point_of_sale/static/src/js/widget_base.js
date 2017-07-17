odoo.define('point_of_sale.BaseWidget', function (require) {
"use strict";

var formats = require('web.formats');
var utils = require('web.utils');
var Widget = require('web.Widget');

var round_di = utils.round_decimals;

// This is a base class for all Widgets in the POS. It exposes relevant data to the 
// templates : 
// - widget.currency : { symbol: '$' | '€' | ..., position: 'before' | 'after }
// - widget.format_currency(amount) : this method returns a formatted string based on the
//   symbol, the position, and the amount of money.
// if the PoS is not fully loaded when you instanciate the widget, the currency might not
// yet have been initialized. Use __build_currency_template() to recompute with correct values
// before rendering.
var PosBaseWidget = Widget.extend({
    init:function(parent,options){
        this._super(parent);
        options = options || {};
        this.pos    = options.pos    || (parent ? parent.pos : undefined);
        this.chrome = options.chrome || (parent ? parent.chrome : undefined);
        this.gui    = options.gui    || (parent ? parent.gui : undefined); 
    },
    
    convertNumberToWords1: function(amount){
        //var amt = convertNumberToWords(amount);	
        //return amt;
        	var words = new Array();
            words[0] = '';
            words[1] = 'One';
            words[2] = 'Two';
            words[3] = 'Three';
            words[4] = 'Four';
            words[5] = 'Five';
            words[6] = 'Six';
            words[7] = 'Seven';
            words[8] = 'Eight';
            words[9] = 'Nine';
            words[10] = 'Ten';
            words[11] = 'Eleven';
            words[12] = 'Twelve';
            words[13] = 'Thirteen';
            words[14] = 'Fourteen';
            words[15] = 'Fifteen';
            words[16] = 'Sixteen';
            words[17] = 'Seventeen';
            words[18] = 'Eighteen';
            words[19] = 'Nineteen';
            words[20] = 'Twenty';
            words[30] = 'Thirty';
            words[40] = 'Forty';
            words[50] = 'Fifty';
            words[60] = 'Sixty';
            words[70] = 'Seventy';
            words[80] = 'Eighty';
            words[90] = 'Ninety';
            amount = amount.toString();
            var atemp = amount.split(".");
            var number = atemp[0].split(",").join("");
            var n_length = number.length;
            var words_string = "";
            if (n_length <= 9) {
                var n_array = new Array(0, 0, 0, 0, 0, 0, 0, 0, 0);
                var received_n_array = new Array();
                for (var i = 0; i < n_length; i++) {
                    received_n_array[i] = number.substr(i, 1);
                }
                for (var i = 9 - n_length, j = 0; i < 9; i++, j++) {
                    n_array[i] = received_n_array[j];
                }
                for (var i = 0, j = 1; i < 9; i++, j++) {
                    if (i == 0 || i == 2 || i == 4 || i == 7) {
                        if (n_array[i] == 1) {
                            n_array[j] = 10 + parseInt(n_array[j]);
                            n_array[i] = 0;
                        }
                    }
                }
                var value;
                for (var i = 0; i < 9; i++) {
                    if (i == 0 || i == 2 || i == 4 || i == 7) {
                        value = n_array[i] * 10;
                    } else {
                        value = n_array[i];
                    }
                    if (value != 0) {
                        words_string += words[value] + " ";
                    }
                    if ((i == 1 && value != 0) || (i == 0 && value != 0 && n_array[i + 1] == 0)) {
                        words_string += "Crores ";
                    }
                    if ((i == 3 && value != 0) || (i == 2 && value != 0 && n_array[i + 1] == 0)) {
                        words_string += "Lakhs ";
                    }
                    if ((i == 5 && value != 0) || (i == 4 && value != 0 && n_array[i + 1] == 0)) {
                        words_string += "Thousand ";
                    }
                    if (i == 6 && value != 0 && (n_array[i + 1] != 0 && n_array[i + 2] != 0)) {
                        words_string += "Hundred and ";
                    } else if (i == 6 && value != 0) {
                        words_string += "Hundred ";
                    }
                }
                words_string = words_string.split("  ").join(" ");
            }
            return words_string;

        },

    format_currency: function(amount,precision){
        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};

        amount = this.format_currency_no_symbol(amount,precision);

        if (currency.position === 'after') {
            return amount + ' ' + (currency.symbol || '');
        } else {
            return (currency.symbol || '') + ' ' + amount;
        }
    },
    format_currency_no_symbol: function(amount, precision) {
        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
        var decimals = currency.decimals;

        if (precision && this.pos.dp[precision] !== undefined) {
            decimals = this.pos.dp[precision];
        }

        if (typeof amount === 'number') {
            amount = round_di(amount,decimals).toFixed(decimals);
            amount = formats.format_value(round_di(amount, decimals), { type: 'float', digits: [69, decimals]});
        }

        return amount;
    },
    show: function(){
        this.$el.removeClass('oe_hidden');
    },
    hide: function(){
        this.$el.addClass('oe_hidden');
    },
    format_pr: function(value,precision){
        var decimals = precision > 0 ? Math.max(0,Math.ceil(Math.log(1.0/precision) / Math.log(10))) : 0;
        return value.toFixed(decimals);
    },
    format_fixed: function(value,integer_width,decimal_width){
        value = value.toFixed(decimal_width || 0);
        var width = value.indexOf('.');
        if (width < 0 ) {
            width = value.length;
        }
        var missing = integer_width - width;
        while (missing > 0) {
            value = '0' + value;
            missing--;
        }
        return value;
    },
});

return PosBaseWidget;

});
