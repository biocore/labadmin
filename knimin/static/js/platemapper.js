/**
 *
 * New widget to allow show the study labels in the dropdown menu
 *
 * Based on the example in https://jqueryui.com/autocomplete/#categories
 *
 */
$( function() {
  $.widget( "custom.catcomplete", $.ui.autocomplete, {
    _create: function() {
      this._super();
      this.widget().menu( "option", "items", "> :not(.ui-autocomplete-category)" );
    },
    _renderMenu: function( ul, items ) {
      var that = this,
          currentCategory = "";
      $.each( items, function( index, item ) {
        var li;
        if ( item.category != currentCategory ) {
          ul.append( "<li class='pm_study_autocomplete'>" + item.category + "</li>" );
          currentCategory = item.category;
        }
        li = that._renderItemData( ul, item );
        if ( item.category ) {
          li.attr( "aria-label", item.category + " : " + item.label );
        }
        });
      }
    });
});

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
    this.createdOn = data.created_on;
    this.createdBy = data.email;
    this.notes = data.notes;
    this.plateType = data.plate_type.notes;
    this.rows = data.plate_type.rows;
    this.cols = data.plate_type.cols;
    this.studies = data.studies;
    this.samples = [{label: 'sample_1_somethinglonger', category: 'study 1'},
                    {label: 'sample_2_somethinglonger', category: 'study 1'},
                    {label: 'sample_3_somethinglonger', category: 'study 1'},
                    {label: 'sample_1', category: 'study 2'},
                    {label: 'sample_2', category: 'study 2'},
                    {label: 'sample_3', category: 'study 2'}];
    this.inputTags = new Array(this.rows);
    for (var i = 0; i < this.inputTags.length; i++) {
        this.inputTags[i] = new Array(this.cols);
    }
    this.wellComments = new Array(this.rows);
    for (var i = 0; i < this.wellComments.length; i++) {
        this.wellComments[i] = new Array(this.cols);
    }
    this.drawPlate();
};

/**
 *
 * Helper method for when a user press a key on a well input
 *
 * @param {Elemnt} current The <input> element where the event has been trigered
 * @param {Event} e The event object
 *
 **/
PlateMap.prototype.keypressWell = function (current, e) {
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
    this.inputTags[row][col].focus();
  }
}

/**
 *
 * Helper method for when the comment modal gets shown
 *
 **/
PlateMap.prototype.commentModalShow = function () {
  var row = parseInt($('#comment-modal-btn').attr('pm-row'));
  var col = parseInt($('#comment-modal-btn').attr('pm-col'));
  // Magic number + 1 -> correct index because JavaScript arrays start at 0
  var wellId = String.fromCharCode('A'.charCodeAt() + row) + (col + 1);
  var sample = this.inputTags[row][col].val().trim();
  if (sample.length === 0) {
    sample = 'No sample plated';
  }
  var value = (this.wellComments[row][col] !== undefined) ? this.wellComments[row][col] : "";
  $('#well-comment-textarea').val(value);
  $('#exampleModalLabel').html('Adding comment to well ' + wellId + ' (Sample: <i>' + sample + '</i>)');
}

/**
 *
 * Helper method for when the user clicks 'save' on the comment modal
 *
 **/
PlateMap.prototype.commentModalSave = function () {
  var row = parseInt($('#comment-modal-btn').attr('pm-row'));
  var col = parseInt($('#comment-modal-btn').attr('pm-col'));
  this.wellComments[row][col] = $('#well-comment-textarea').val();
  $('#myModal').modal('hide');
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
  i.keypress(function(e) {
    obj.keypressWell(this, e);
  });
  i.focusin(function(e) {
    // Enable the comment button
    $('#comment-modal-btn').attr('pm-row', parseInt($(this).attr('pm-well-row')));
    $('#comment-modal-btn').attr('pm-col', parseInt($(this).attr('pm-well-column')));
  });
  i.addClass('form-control').addClass('autocomplete').addClass('pm-well');
  i.attr('placeholder', 'Type sample').attr('pm-well-row', row).attr('pm-well-column', column).attr('type', 'text');
  i.appendTo(d);
  // Store the input in the array for easy access when navigating on the
  // plate map
  this.inputTags[row][column] = i;
  // Return the top div
  return d;
};


/**
 *
 * Helper method to construct the HTML of the plate map
 *
 **/
PlateMap.prototype.drawPlate = function() {
  var row, col, well, table, textArea, btn, span, obj;
  obj = this;

  // Create the header and the top information
  $('<label><h3>Plate <i>' + this.name + '</i> (ID: ' + this.plate_id + ') </h3></label></br>').appendTo(this.target);
  $('<b>Plate type: </b>' + this.plateType + '</br>').appendTo(this.target);
  $('<b>Created on: </b>' + this.createdOn + '</br>').appendTo(this.target);
  $('<b>Created by: </b>' + this.createdBy + '</br>').appendTo(this.target);
  span = $('<span>').attr('data-toggle', 'tooltip').attr('data-placement', 'right').attr('title', 'Add well comment').attr('id', 'well-comment');
  span.appendTo(this.target);
  span.tooltip();
  btn =  $('<button>').addClass('btn').addClass('glyphicon glyphicon-comment');
  btn.attr('type', 'button').attr('data-toggle', 'modal').attr('data-target', '#myModal').attr('id', 'comment-modal-btn').attr('pm-row', 0).attr('pm-col', 0);
  btn.appendTo(span);
  // Add studies
  // Add hyperlink to study to JIRA and Qiita

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

  // Create the plate map
  for (var i = 0; i < this.rows; i++) {
    row = $('<tr>');
    row.appendTo(table);
    col = $('<td>');
    // Adding row name - From: http://stackoverflow.com/a/12504060
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

  // Add the Notes text area
  $('<b>Plate notes: </b></br>').appendTo(this.target);
  textArea = $('<textarea cols="200" id="notes-input"></textarea>').appendTo(this.target);
  if (this.notes !== undefined) {
    textArea.val(this.notes);
  }

  // Add the comments modal - Note that this modal gets added to the body
  // This is to avoid some undesired behavior with modals, in which they
  // get blocked "behind" the faded background
  $('<div class="modal fade" id="myModal" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabel" aria-hidden="true">' +
    '<div class="modal-dialog" role="document">' +
      '<div class="modal-content">' +
        '<div class="modal-header">' +
          '<h4 class="modal-title" id="exampleModalLabel"></h4>' +
          '<button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span>' +
          '</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<textarea class="form-control" id="well-comment-textarea"></textarea>' +
        '</div>' +
        '<div class="modal-footer">' +
          '<button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>' +
          '<button type="button" class="btn btn-primary" id="save-cmt-btn" disabled>Save comment</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
  '</div>').appendTo($('body'));

  // Attach a handler to the modal show event
  $('#myModal').on('show.bs.modal', function (e) {
    obj.commentModalShow();
  });

  // Attach a handler to the modal shown event
  $('#myModal').on('shown.bs.modal', function (e) {
    // We just need to make sure that the modal text area gets focused
    $('#well-comment-textarea').focus();
  });

  $('#save-cmt-btn').click(function(e) {
    obj.commentModalSave();
  });

  $('#well-comment-textarea').keyup(function(e) {
    var value = $('#well-comment-textarea').val().trim();
    // Only enable the button if there is some text in the textarea
    $('#save-cmt-btn').prop('disabled', value.length === 0);
  });

  $(".autocomplete").catcomplete({source: this.samples});
}
