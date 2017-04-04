/**
 *
 * @class PlateMap
 *
 * Represents a Plate
 *
 * @param {string} target The name of the target container for the plate map
 * @param {int} rows The number of rows in the plate
 * @param {int} cols The number of columns in the plate
 * @param {string[]} samples The list of samples to populate the autocomplete
 *
 * @return {PlateMap}
 * @constructs PlateMap
 *
 **/
function PlateMap(target, plate_id) {
  var obj = this;
  this.plate_id = plate_id
  this.target = $('#' + target)
  $.get('/pm_sample_plate?plate_id=' + plate_id, function (data) {
    obj.initialize(data);
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      if(jqXHR.status === 404) {
        var data = $.parseJSON(jqXHR.responseText)
        $('<h3 class="warning">').html(data.message).appendTo(obj.target);
      } else {
        $('<div>').html(jqXHR.responseText).appendTo(obj.target);
      }
    });
};

/**
 *
 * Helper function to initialize the object after the GET query is completed
 *
 * @param {Object} data The data returned from the GET query
 *
 **/
PlateMap.prototype.initialize = function (data) {
    this.name = data.name;
    this.created_on = data.created_on;
    this.created_by = data.email;
    this.notes = data.notes;
    this.plate_type = data.plate_type.notes;
    this.rows = data.plate_type.rows;
    this.cols = data.plate_type.cols;
    this.studies = data.studies;
    this.samples = ['sample_1_lets_try_something_longer', 'sample_2'];
    this.input_tags = new Array(this.rows);
    for (var i = 0; i < this.input_tags.length; i++) {
        this.input_tags[i] = new Array(this.cols);
    }
    this.drawPlate();
};

/**
 *
 * Helper method to change the focus of the input
 *
 **/
PlateMap.prototype.on_keypress = function (current, e) {
  var row, col;
  if (e.which === 13) {
    // The user hit enter, which means that we have to move down one row
    // Retrieve which is the current row and column
    row = parseInt($(current).attr('pm-well-row'));
    col = parseInt($(current).attr('pm-well-column'));
    // Update indices
    row = row + 1;
    if (row === this.rows) {
      row = 0;
      col = col + 1;
      if (col === this.cols) {
        col = 0;
      }
    }
    this.input_tags[row][col].focus();
  }
}


/**
 *
 * Helper method to construct the HTML of a well
 *
 * @param {int} row The row of the well
 * @param {int} column The column of the well
 *
 * @return {jQuery.Object} The div representing a well
 *
 **/
PlateMap.prototype.constructWell = function(row, column) {
  var obj = this;
  // Div holding well
  var d = $('<div>');
  d.addClass('input-group');
  // The input tag
  var i = $('<input>');
  i.on('keypress', function(e) {
    obj.on_keypress(this, e);
  });
  this.input_tags[row][column] = i;
  i.addClass('form-control').addClass('autocomplete');
  i.attr('placeholder', 'Type sample').attr('pm-well-row', row).attr('pm-well-column', column).attr('type', 'text');
  i.appendTo(d);
  // A span to locate the comments button next to the input
  var s = $('<span>');
  s.addClass('input-group-btn');
  s.appendTo(d);
  // The comment button
  var b = $('<button>');
  b.addClass('btn').addClass('btn-default').addClass('glyphicon').addClass('glyphicon-comment');
  b.attr('type', 'button')
  b.appendTo(s);
  // Return the top div
  return d;
};


/**
 *
 * Helper method to construct the HTML of the plate map
 *
 **/
PlateMap.prototype.drawPlate = function() {
  var row, col, well, table, textArea;

  // Create the header and the top information
  $('<label><h3>Plate <i>' + this.name + '</i> (ID: ' + this.plate_id + ') </h3></label></br>').appendTo(this.target);
  $('<b>Plate type: </b>' + this.plate_type + '</br>').appendTo(this.target);
  $('<b>Created on: </b>' + this.created_on + '</br>').appendTo(this.target);
  $('<b>Created by: </b>' + this.created_by + '</br>').appendTo(this.target);

  table = $('<table>');
  table.appendTo(this.target);

  // Create the header row
  row = $('<tr>');
  row.appendTo(table);
  $('<th>').appendTo(row);
  for (var i = 0; i < this.cols; i++) {
    col = $('<th>');
    col.attr('style', 'text-align: center;')
    col.html(i+1);
    col.appendTo(row);
  }

  for (var i = 0; i < this.rows; i++) {
    row = $('<tr>');
    row.appendTo(table);
    col = $('<td>');
    // From: http://stackoverflow.com/a/12504060
    col.html(String.fromCharCode('A'.charCodeAt() + i));
    col.appendTo(row);
    for (var j = 0; j < this.cols; j++) {
      col = $('<td>');
      col.appendTo(row);
      // Construct the well
      well = this.constructWell(i, j);
      well.appendTo(col);
    }
  }

  $('<b>Notes: </b></br>').appendTo(this.target);
  textArea = $('<textarea cols="200" id="notes-input"></textarea>').appendTo(this.target);

  if (this.notes !== undefined) {
    textArea.val(this.notes);
  }


  $(".autocomplete").autocomplete({source: this.samples});
}
