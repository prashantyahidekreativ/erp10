odoo.define('kts_field_force.web_gmaps', function(require){
	'use strict';
	var ajax = require('web.ajax');
	var core = require('web.core');	
	var Widget = require('web.Widget');
	var common = require('web.form_common');
	var Model = require('web.Model');
	var bus = require('bus.bus').bus;
	var QWeb = core.qweb;
	
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
            bus.on('notification', this, this.bus_notification);
            bus.start_polling();    
            this.field_manager.on("field_changed:filter_date", this,  function() {
                this.filter_field_set();
                this.on_ready1();
            });
        },
        
        filter_field_set: function(){
        	if (! this.field_manager.get_field_value('live_track')){
        	  this.set("filter_date",this.field_manager.get_field_value("filter_date"));
        	}
        	else{
        		var now = new Date();
       		    var tmp = now.toISOString().slice(0,10);
        		this.set("filter_date",tmp);
        	} 
        },
        
        bus_notification: function(notification) {
        	console.log(notification);
        	
        	for (var i = 0; i < notification.length; i++) {
                var channel = notification[i][0];
                var message = notification[i][1];
                var dict = JSON.parse(message);
                var d1=new Date().toISOString().slice(0,10);
                var filterdate = new Date(this.get("filter_date"));
                if (filterdate == d1 && this.field_manager.get_field_value('live_track')){
                    var latlng = new google.maps.LatLng(dict['lat'],dict['long']);
                    var path = this.snappedPolyline.getPath();
                    path.push(latlng);
                  }
            }
        },    
             
        
        render_map: function (self, cords){
        	var markerdata=[];
        	var pathValues = [];
        	var div_map=self.$el[0]; 
       	    var map = new google.maps.Map(div_map, {
               zoom: 15,
               center: new google.maps.LatLng(parseFloat(self.field_manager.get_field_value('location_latitude')),parseFloat(self.field_manager.get_field_value('location_longitude'))),
               mapTypeId: google.maps.MapTypeId.ROADMAP
             });
       	 
       	   var markermain = new google.maps.Marker({
             position: new google.maps.LatLng(parseFloat(self.field_manager.get_field_value('location_latitude')),parseFloat(self.field_manager.get_field_value('location_longitude'))),
             map: map,
             
       	   });
        
       	 $.each(cords, function(index, data){
        		markerdata.push([parseFloat(data.location_latitude),parseFloat(data.location_longitude),data.write_date,data.last_location]);
        		pathValues.push(parseFloat(data.location_latitude)+','+parseFloat(data.location_longitude));    
        		
       	    });
       	
       	var infowindow = new google.maps.InfoWindow({
            maxWidth: 160
          });

        var markers = new Array();
        for (var i = 0; i < markerdata.length; i++) {  
            var marker = new google.maps.Marker({
              position: new google.maps.LatLng(markerdata[i][0], markerdata[i][1]),
              map: map,
              icon: 'http://maps.google.com/mapfiles/ms/micons/man.png',
            });

            markers.push(marker); 
            google.maps.event.addListener(marker, 'click', (function(marker, i) {
                return function() {
                  infowindow.setContent(markerdata[i][2]+' At '+markerdata[i][3]);
                  infowindow.open(map, marker);
                }
              })(marker, i));
        }
        
        function autoCenter() {
            //  Create a new viewpoint bound
            var bounds = new google.maps.LatLngBounds();
            //  Go through each...
            for (var i = 0; i < markers.length; i++) {  
      				bounds.extend(markers[i].position);
            }
            //  Fit these bounds to the map
            map.fitBounds(bounds);
          }
        if (markers.length > 0){  
        autoCenter();        
        }
       	 function snappedpts(pathValues1){
       		return $.ajax({
        		 url:'https://roads.googleapis.com/v1/snapToRoads', 
        		 data:{ interpolate: true,
                       key: 'AIzaSyB3ghpGMTrWuBg9qit3WH9_P1CvKL7Mrto',
                       path: pathValues1.join('|'),    
        	          }, 
        	    type: 'GET',  
        	    success:
        	function(mdata) {
        	     
        	    }
        	});   	    
          	  
       	 }
       	 
       	 var i,j,temp,chunk = 100;
       	
       	
       	var snappedCoordinates1=[];
       	for (i=0,j=pathValues.length; i<j; i+=chunk) {
       		temp = pathValues.slice(i,i+chunk);
       		snappedCoordinates1.push(snappedpts(temp)); 
       	}
       	
       	$.when.apply(self, snappedCoordinates1).done(
       	    function() {
       	        console.log('In then')
       	    	console.log(arguments);
       	    var snappedCoordinates=[]; 
       	    var placeIdArray=[];
       	    for (var i = 0; i < arguments.length; i++) {
       	     if (arguments[i][0]){  
       	         var values = arguments[i][0]['snappedPoints'];
       	    	 $.each(values, function(index, data2){
   		             var latlng = new google.maps.LatLng(
   		             data2.location.latitude,
 	                 data2.location.longitude);
 	                 snappedCoordinates.push(latlng);
 	                 placeIdArray.push(data2.placeId); 
   		          });
       	     }
       	     else{
       	    	var values = arguments[0]['snappedPoints'];
      	    	 $.each(values, function(index, data2){
  		             var latlng = new google.maps.LatLng(
  		             data2.location.latitude,
	                 data2.location.longitude);
	                 snappedCoordinates.push(latlng);
	                 placeIdArray.push(data2.placeId); 
  		          });
       	     break;
       	     }
       	    }
       	 self.snappedPolyline = new google.maps.Polyline({
  		    path: snappedCoordinates,
  		    strokeColor: 'red',
  		    strokeWeight: 5
  		  });
         self.snappedPolyline.setMap(map);
       	});
       	
       	    
                          
            return ;
        },
        
                
        on_ready1:function(){
        	 
        	 var self = this;
        	 if (this.get("filter_date")) {
        		 var tmp = this.get("filter_date");
        		 var date1=tmp+" 00:00:00";
        		 var date2=tmp+" 23:59:59";

        		 new Model('kts.fieldforce.employee.location')
        		 .query([])
                 .filter([["employee_location_rel", "=", self.field_manager.datarecord.id],['create_date','>=',date1],['create_date','<=',date2]])
                 .all() 
                 .then(function(result) { 
                	 console.log('This is onready');
              	     console.log(result);
                	 self.render_map(self,result);
                   
                 }); 
                  
              
        	 }
        	 
        	 else{
        		 var now = new Date();
        		 var tmp = now.toISOString().slice(0,10);
        		 var date1=tmp+" 00:00:00";
        		 var date2=tmp+" 23:59:59";
        		 new Model('kts.fieldforce.employee.location').call('search_read',[[["employee_location_rel", "=", self.field_manager.datarecord.id],['create_date','>=',date1],['create_date','<=',date2]],[]]) 
               .then(function(result) { 
              	 console.log('This is onready');
            	 console.log(result);
              	 self.render_map(self,result);
              	  
                 
               }); 
            
        	 }
        },	

    	    
	});
	
	core.form_tag_registry.add('mytest', MyTest)
	
	
	return { MyTest:MyTest, };

});
