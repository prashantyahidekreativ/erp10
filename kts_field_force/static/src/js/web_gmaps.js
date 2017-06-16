odoo.define('kts_field_force.web_gmaps', function(require){
	'use strict';
	var ajax = require('web.ajax');
	var core = require('web.core');	
	var Widget = require('web.Widget');
	var common = require('web.form_common');
	var Model = require('web.Model');
	var bus = require('bus.bus').bus;
	var QWeb = core.qweb;
	
	$.getScript('https://maps.googleapis.com/maps/api/js?key=AIzaSyB3ghpGMTrWuBg9qit3WH9_P1CvKL7Mrto');           
    
	var MyTest = common.FormWidget.extend({
		
		template: "gps_base_gmap_marker", 
		          
        start: function(view, node) {
            //this._super(); 	
        	console.log('In Start method');
            var self = this;
            this.field_manager.on("field_changed:filter_date", this,  function() {
                this.filter_field_set();
                this.on_ready1();
            });
            this.on_ready1();
            this._super();
        },
        
        filter_field_set: function(){
        	  this.set("filter_date",this.field_manager.get_field_value("filter_date"));
         
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
        	if (typeof google== 'undefined') {
	    		$.getScript('https://maps.googleapis.com/maps/api/js?key=AIzaSyB3ghpGMTrWuBg9qit3WH9_P1CvKL7Mrto');
                           
            }
        	 var self = this;
        	 if (this.get("filter_date") || this.field_manager.get_field_value('filter_date')) {
        		 if (this.get("filter_date")){
        		 var tmp = this.get("filter_date");}
        		 else{
        			 var tmp = this.field_manager.get_field_value('filter_date');
        		 }
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
	
var MyTest1 = common.FormWidget.extend({
		
		template: "gps_base_gmap_marker1", 
		
		start: function(view, node) {
            //this._super(); 	
            var res = this._super(this);
			var self = this;
            this.field_manager.on("field_changed:filter_date", this,  this.ready2);
            this.channel = JSON.stringify(["erp10", "gps.coords.set"]);                 
            bus.add_channel(this.channel);
            bus.on('notification', this, function(notification){
            	for (var i = 0; i < notification.length; i++) {
                    var channel = notification[i][0];
                    var message = notification[i][1];
                    var dict = JSON.parse(message);
                    var latlng = new google.maps.LatLng(dict['lat'],dict['long']);
                    var markermain2 = new google.maps.Marker({
                        position: latlng,
                        map: self.map1,
                        
                  	   })
            	}
            });
            
            bus.start_polling();    
            
            this.ready2();
            
            //return this._super();
		},	
		
		render_map: function (self, lat, lng){ 
            var myLatlng = new google.maps.LatLng(lat, lng); 
            var mapOptions = { 
                zoom: 8, 
                center: myLatlng 
            };

            var div_gmap = self.$el[0];

            self.map1 = new google.maps.Map(div_gmap, mapOptions);

            self.marker = new google.maps.Marker({ 
                position: myLatlng, 
                map: self.map1, 
                draggable:false, 
            });

            google.maps.event.addListener(self.marker, 'dragend',function(NewPoint){ 
                lat = NewPoint.latLng.lat(); 
                lng = NewPoint.latLng.lng(); 
                
            }); 
        },

	    ready2:function(){
	    	if (typeof google== 'undefined') {
	    		$.getScript('https://maps.googleapis.com/maps/api/js?key=AIzaSyB3ghpGMTrWuBg9qit3WH9_P1CvKL7Mrto');
                           
            }
	    	 var call_back= this.render_map;
	    	 var self = this;
	    	 
	       	   console.log('These are value from ready2');
	           console.log(self.field_manager.get_field_value('location_latitude'));
	           console.log(self.field_manager.get_field_value('location_longitude'));
	       	   
	           var def = new $.Deferred(); 
               new Model("kts.fieldforce.employee") 
                   .query(['location_latitude','location_longitude']) 
                   .filter([["id", "=", this.field_manager.datarecord.id]]) 
                   .first() 
                   .then(function(result) { 
                       if(!result || result.length === 0){ 
                           call_back(self, 0, 0); 
                           def.reject(); 
                       }else{ 
                           call_back(self, result['location_latitude'], result['location_longitude']); 
                           def.resolve(); 
                       } 
                   });

	         
	       	
	       	return def.promise();
      },
      
      
      
});       
    
	
	core.form_tag_registry.add('mytest', MyTest);
	core.form_tag_registry.add('mytest1', MyTest1);
	//core.form_tag_registry.add('mytest2', MyTest2);
	
	return { MyTest:MyTest,
		     MyTest1:MyTest1,
	      };
	

});
