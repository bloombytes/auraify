$(document).ready(function() {
  var mode = $('body').data('mode');

  $.getJSON('/get_playlists', function(data) {
      $.each(data, function(i, playlist) {
          var canvas = $('<canvas></canvas>');
          var img = $('<img />', {
              id: 'playlistImage',
              alt: playlist['name'] + ' image'
          });
          var listItem = $('<li></li>');
          listItem.append('<h3>' + playlist['name'] + '</h3><p>Tempo: ' + playlist['tempo'] + ' BPM</p><p>Mood: ' + playlist['mood'] + '</p>');
          listItem.append(canvas);
          listItem.append(img);
          $('#playlists').append(listItem);

          var ctx = canvas[0].getContext('2d');
          var chart = new Chart(ctx, {
              type: mode === 'Spectrum' ? 'pie' : 'bar',
              data: {
                  labels: ['Valence', 'Energy', 'Danceability'],
                  datasets: [{
                      data: [average(playlist['valences']), average(playlist['energies']), average(playlist['danceabilities'])],
                      backgroundColor: ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)'],
                      borderColor: ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)'],
                      borderWidth: 1
                  }]
              }
          });
      });
      $('#loading').hide();
      $('#content').show();
  });

  $('#switchMode').click(function() {
      $.get('/switch_mode', function() {
          location.reload();
      });
  });
});

function average(array) {
  var sum = array.reduce(function(a, b) {
      return a + b;
  });
  return sum / array.length;
}
