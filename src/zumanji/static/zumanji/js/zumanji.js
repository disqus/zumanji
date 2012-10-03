Sparkline = (function(options){

  function floatFormat(value){
    return Math.round(value * 1000) / 1000;
  }

  function progressBar(label, value, max_value){
    var pct = parseInt(value / max_value * 100, 10);
    var output = '<div class="progressbar">';
    output += '<div style="width:' + pct + '%;"></div>';
    output += '<span>' + label + ' (' + value + ')</span>';
    output += '</div>';
    return output;
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

  var colorMap = ['#3366cc', '#dc3912', '#ff9900', '#109618', '#66aa00',
                    '#dd4477', '#0099c6', '#990099'];
  var $sparkline = $el.sparkline(values, {
    type: 'bar',
    width: options.width,
    height: options.height,
    barColor: '#08C',
    nullColor: '#999',
    stackedBarColor: colorMap,
    barWidth: options.barWidth,
    barSpacing: options.barSpacing,
    tooltipClassname: 'sparktooltip',
    tooltipFormatter: function(sparkline, _, fields){
      var output = '';
      var total = 0;
      var value;
      var pct;

      $.each(fields, function(_, f){
        total += floatFormat(f.value);
      });

      if (fields.length === 0) {
        return '(No data)';
      }

      output += '<h4>' + options.values[sparkline.currentRegion].title + '</h4>';
      output += '<ul>';
      $.each(options.columns, function(_, column){
        value = floatFormat(fields[fields.length - 1 - _].value);
        pct = parseInt(value / total * 100, 10);
        output += '<li>' + progressBar(column, value, total) + '</li>';
      });
      output += '</ul>';
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

  var $canvas = $el.find('canvas');
  var $legend = $('<ul class="legend"></ul>');
  $.each(options.columns, function(_, column){
    $legend.append($('<li><span style="background-color:' + colorMap[_] + ';"></span> ' + column + '</li>'));
  });

  $legend.css({
    position: 'absolute',
    left: $canvas.offset().left,
    top: $canvas.offset().top
  });

  $el.prepend($legend);
});