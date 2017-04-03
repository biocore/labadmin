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
      console.log('Error ' + textStatus + ' ' + errorThrown);
    });
};

/**
 *
 * Helper function to initialize the object after the GET query is completed
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
    this.samples = ['sample_1', 'sample_2'];
    this.drawPlate();
};


/**
 *
 * Helper method to construct the HTML of a well
 *
 * @return {jQuery.Object} The div representing a well
 *
 **/
PlateMap.prototype.constructWell = function() {
  var d = $('<div>');
  d.addClass('form-group');
  var i = $('<input>')
  i.addClass('form-control').addClass('autocomplete');
  i.attr('placeholder', 'Type sample');
  i.appendTo(d);
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
      well = this.constructWell();
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
