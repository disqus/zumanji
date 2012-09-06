Sparkline = (function(options){

  function floatFormat(value){
    return Math.round(value * 1000) / 1000;
  }

  var $el = $('<span class="sparkline"></span>').css({
    height: options.height,
    lineHeight: options.height
  });
  var values = [];

  $.each(options.values, function(_, value){
    values.push(value.values);
  });

  $(options.parent).append($el);

  $el.sparkline(values, {
    type: 'bar',
    width: options.width,
    height: options.height,
    barColor: '#08C',
    nullColor: '#999',
    barWidth: options.barWidth,
    barSpacing: options.barSpacing,
    tooltipClassname: 'sparktooltip',
    tooltipFormatter: function(sparkline, _, fields){
      var output = '';
      var total = 0;
      $.each(fields, function(_, f){
        total += floatFormat(f.value);
      });

      if (fields.length === 0) {
        return '(No data)';
      }
      output += '<table>';
      output += '<caption>' + options.values[sparkline.currentRegion].title + '</caption>';
      output += '<tr><th>Total</th><td>' + floatFormat(total) + '</td></tr>';
      $.each(options.columns, function(_, column){
        output += '<tr><th>' + column + '</th><td>' + floatFormat(fields[_ + 1].value) + '</td></th>';
      });
      output += '</table>';
      return output;
    },
    // colorMap: $.range_map({
    //   0: '#08C',
    //   '1:': 'red'
    // }),
    chartRangeMax: 1,
    chartRangeMin: 0
  }).bind('sparklineClick', function(e){
    var item = options.values[e.sparklines[0].currentRegion];
    if (!item.url) {
      return;
    }
    window.location.href = item.url;
  });

});