odoo.define('kts_field_force.web_gmaps', function(require){
	'use strict';
	var ajax = require('web.ajax');
	var core = require('web.core');	
	var Widget = require('web.Widget');
	var common = require('web.form_common');
	var Model = require('web.Model');
	var bus = require('bus.bus').bus;
	var QWeb = core.qweb;
	var map;
	var cordlist=[];
	var dataid;     
	
	var MyTest = common.FormWidget.extend({
		
		template: "gps_base_gmap_marker", 
		          
        start: function(view, node) {
            //this._super(); 	
        	console.log('In Start method');
            var self = this;
            window.init = this.on_ready1;
            $.getScript('https://maps.googleapis.com/maps/api/js?key=AIzaSyB3ghpGMTrWuBg9qit3WH9_P1CvKL7Mrto&callback=init');           
            this.channel = JSON.stringify(["erp10", "gps.coords.set"]);                 
            bus.add_channel(this.channel);
            bus.on('notification', this, this.on_ready1);
            bus.start_polling();    
        },
        
        bus_notification: function(notifications) {
        	console.log('Notification');
        	
        },    
             
        
        render_map: function (self, cords){
        	console.log('This is render map');
        	console.log('global cords');
        	console.log(cordlist);
        	var flightPlanCoordinates=[]
        	var div_map=self.$el[0]; 
       	    var map = new google.maps.Map(div_map, {
               zoom: 8,
               center: new google.maps.LatLng(parseFloat(self.field_manager.get_field_value('location_latitude')),parseFloat(self.field_manager.get_field_value('location_longitude'))),
               
             });
       	 var marker = new google.maps.Marker({
             position: new google.maps.LatLng(parseFloat(self.field_manager.get_field_value('location_latitude')),parseFloat(self.field_manager.get_field_value('location_longitude'))),
             map: map,
            });
        	
       	 $.each(cords, function(index, data){
       		    
        		flightPlanCoordinates.push({lat:parseFloat(data.location_latitude),lng:parseFloat(data.location_longitude)});
        	    cordlist.push({lat:parseFloat(data.location_latitude),lng:parseFloat(data.location_longitude)});
       	    });
        	console.log('this is list of coords');
        	console.log(flightPlanCoordinates);
        	console.log('global cords2');
        	console.log(cordlist);
        	var flightPlanCoordinates1 = [
        	                              {lat: 37.772, lng: -122.214},
        	                              {lat: 21.291, lng: -157.821},
        	                              {lat: -18.142, lng: 178.431},
        	                              {lat: -27.467, lng: 153.027}
        	                            ];
        	 console.log(flightPlanCoordinates1);
        	 self.flightPath = new google.maps.Polyline({
        	                              path: flightPlanCoordinates,
        	                              geodesic: true,
        	                              strokeColor: '#FF0000',
        	                              strokeOpacity: 1.0,
        	                              strokeWeight: 2
        	                            });
        	                            
            self.flightPath.setMap(map);
            
            return 
        },
        
        
        
        
        on_ready1:function(){
        	 
        	 var self = this;
        	 
        	 //var def = new $.Deferred();         	 
          	 var flightPlanCoordinates = []
          	 new Model('kts.fieldforce.employee.location').call('search_read',[[["employee_location_rel", "=", self.field_manager.datarecord.id]],[]]) 
               .then(function(result) { 
              	 console.log('This is onready');
            	 console.log(result);
              	 self.render_map(self,result);
              	 //def.resolve(); 
                 
               }); 
               //def.done(self.test_fun());
          	 dataid = self.field_manager.datarecord.id;   
          	 setInterval(self.test_fun,3000); 
        
        },	

              
 
 
			
     		
		
		
//		start: function(field_manager, node) {
//    	        this._super(field_manager, node);
//    	        this.field_manager.on("field_changed:latitude_aux", this, this.display_map);
//    	        this.field_manager.on("field_changed:longitude_aux", this, this.display_map);
//    	        this.display_map();
//    	      
//    	   },
//    	    display_map: function() {
//    	    		this.$el.html(QWeb.render("WidgetCoordinates", {
//    	            "latitude": this.field_manager.get_field_value("latitude_aux") || 0,
//    	            "longitude": this.field_manager.get_field_value("longitude_aux") || 0,   
//    	        }));
//    	    }    
    	    
	});
	//core.form_widget_registry.add('mytest', MyTest);
	core.form_tag_registry.add('mytest', MyTest)
	core.form_tag_registry.add('mylocation', MyLocation)
	
	return { MyTest:MyTest, };
    //return MyTest
});









//odoo.define('gps_base.web_gmaps', function(require){
//	var core = require('web.core');
//	var data = require('web.data');
//	var common = require('web.form_common');
//    var Model = require('web.Model')
//	var session = require('web.session');
//    var utils = require('web.utils');
//
//    var Qweb = core.qweb
//    
//    var GpsWidgetTest =  common.FormWidget.extend({
//    	    
//        start: function() {
//    		this._super.apply(this, arguments);
//            this.field_manager.on("field_changed:latitude_aux", this, this.display_map);
//            this.field_manager.on("field_changed:longitude_aux", this, this.display_map);
//            this.display_map();
//        },
//        display_map: function() {
//            this.$el.html(QWeb.render("WidgetCoordinates", {
//                "latitude": this.field_manager.get_field_value("latitude_aux") || 0,
//                "longitude": this.field_manager.get_field_value("longitude_aux") || 0,
//            }));
//        }
//        
//    }); 
//   core.form_widget_registry.add('gps_base_gmap_marker2', GpsWidgetTest);
//  
//});
