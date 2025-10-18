// Do NOT redeclare "var google;" — the API provides it.
// Expose init so the script callback can find it.
window.init = function () {
  // 1) Your target coordinates (from your Maps link)
  const myLatlng = { lat: 14.568269359450321, lng: 121.00717145898005 };

  // 2) Map options (your original styles kept)
  const mapOptions = {
    zoom: 15,                       // start closer
    center: myLatlng,
    scrollwheel: false,
    mapTypeId: google.maps.MapTypeId.HYBRID,
    styles: [
      {"elementType":"geometry","stylers":[{"color":"#f5f5f5"}]},
      {"elementType":"labels.icon","stylers":[{"visibility":"off"}]},
      {"elementType":"labels.text.fill","stylers":[{"color":"#ffffff"}]},
      {"elementType":"labels.text.stroke","stylers":[{"color":"#000000"}]},
      {"featureType":"administrative.land_parcel","elementType":"labels.text.fill","stylers":[{"color":"#bdbdbd"}]},
      {"featureType":"poi","elementType":"geometry","stylers":[{"color":"#eeeeee"}]},
      {"featureType":"poi","elementType":"labels.text.fill","stylers":[{"color":"#757575"}]},
      {"featureType":"poi.park","elementType":"geometry","stylers":[{"color":"#e5e5e5"}]},
      {"featureType":"poi.park","elementType":"labels.text.fill","stylers":[{"color":"#9e9e9e"}]},
      {"featureType":"road","elementType":"geometry","stylers":[{"color":"#6b6166"}]},
      {"featureType":"road.arterial","elementType":"labels.text.fill","stylers":[{"color":"#ffffff"}]},
      {"featureType":"road.highway","elementType":"geometry","stylers":[{"color":"#dadada"}]},
      {"featureType":"road.highway","elementType":"labels.text.fill","stylers":[{"color":"#ffffff"}]},
      {"featureType":"road.local","elementType":"labels.text.fill","stylers":[{"color":"#ffffff"}]},
      {"featureType":"transit.line","elementType":"geometry","stylers":[{"color":"#e5e5e5"}]},
      {"featureType":"transit.station","elementType":"geometry","stylers":[{"color":"#eeeeee"}]},
      {"featureType":"water","elementType":"geometry","stylers":[{"color":"#c9c9c9"}]},
      {"featureType":"water","elementType":"labels.text.fill","stylers":[{"color":"#ffffff"}]}
    ]
  };

  // 3) Create map
  const mapEl = document.getElementById('map');
  if (!mapEl) { console.error('No #map element found'); return; }
  const map = new google.maps.Map(mapEl, mapOptions);

  // 4) Always drop a marker at your exact coords
  new google.maps.Marker({
    position: myLatlng,
    map,
    title: 'Clinic',
    // icon: '{% static "website/images/loc.png" %}' // optional custom pin
  });

  // 5) (Optional) If you still want to place markers by address,
  //    use the Maps JS Geocoder (NOT the old $.getJSON URL).
  const addresses = []; // e.g., ['Manila, Philippines']
  if (addresses.length) {
    const geocoder = new google.maps.Geocoder();
    addresses.forEach(addr => {
      geocoder.geocode({ address: addr }, (results, status) => {
        if (status === 'OK' && results[0]) {
          const loc = results[0].geometry.location;
          new google.maps.Marker({ position: loc, map, title: addr });
          // Center on the first geocoded address if you like:
          map.setCenter(loc);
          map.setZoom(15);
        } else {
          console.error('Geocode failed for "' + addr + '":', status);
        }
      });
    });
  }
};
