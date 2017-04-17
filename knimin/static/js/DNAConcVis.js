/**
 *
 * @class DNAConcVis
 *
 * Visualizes a matrix of DNA concentratoions
 *
 **/
function DNAConcVis(target, plate, isMod) {
  var that = this;

  // Store the plate Id and the target DOM element
  this.plate = plate;
  this.target = $('#' + target);
  this.isMod = isMod;
  this._drawGUI();
};


DNAConcVis.prototype._drawGUI = function() {
  var $table, $row, $col, $input;
  var that = this;

  $table = $('<table>');
  $table.appendTo(this.target);

  // Add the header row
  $row = $('<tr>');
  $row.appendTo($table);
  $('<th>').appendTo($row);
  for (var i = 0; i < this.plate['cols']; i++) {
    $col = $('<th>');
    $col.attr('style', 'text-align: center;')
    $col.html(i+1);
    $col.appendTo($row);
  }

  // Adding the rest of the rows
  for (var i = 0; i < this.plate['rows']; i++) {
    $row = $('<tr>');
    $row.appendTo($table);
    $col = $('<td>');
    $col.html(this._formatRowId(i));
    $col.appendTo($row);
    // Adding the rest of the cols
    for (var j = 0; j < this.plate['cols']; j++) {
      $col = $('<td>');
      $col.appendTo($row);
      $well = $('<div>');
      $input = $('<input>').addClass('form-control').attr('type', 'number').attr('step', '0.001').appendTo($well)
        .data("pm-row", i).data("pm-col", j)
        .change(function() {
            var row = $(this).data("pm-row")
            var col = $(this).data("pm-col")
            console.log(row);
            console.log(col);
            that.plate['mod_concentration'][row][col] = $(this).val();
        });
      this._formatWellStyle($input, i, j);
      $well.appendTo($col);
    }
  }
};

/**
 *
 * Formats the well Id
 *
 * @param {int} row The row of the well
 * @param {int} col The col of the well
 *
 * @return {string}
 *
 **/
DNAConcVis.prototype._formatWellId = function (row, col) {
  var rId = this._formatRowId(row);
  var sep = (this.rows > 26) ? '-' : '';
  var cId = String(col + 1);
  return rId + sep + cId;
}

/**
 *
 * Formats the row Id
 *
 * @param {int} row The row
 *
 * @return {string}
 *
 **/
DNAConcVis.prototype._formatRowId = function (row) {
  // Add a letter only if we have less than 26 rows
  if (this.plate['rows'] > 26) {
    return String(i + 1);
  } else {
    // From: http://stackoverflow.com/a/12504060
    return String.fromCharCode('A'.charCodeAt() + row);
  }
}

/**
 *
 * Defines the value in the well
 *
 * @param {int} row The row
 * @param {int} row The col
 *
 * @return {string}
 *
 **/
DNAConcVis.prototype._formatWellStyle = function ($input, row, col) {
  if (this.isMod) {
    $input.removeClass('pm-conc-blank').removeClass('pm-conc-diff').removeClass('pm-conc-min');
    $input.addClass(this.plate['color_class'][row][col]);
    $input.val(this.plate['mod_concentration'][row][col]);
  } else {
    $input.val(this.plate['raw_concentration'][row][col]);
    $input.prop('disabled', true);
  }
}
