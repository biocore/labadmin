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
          $('<li>').addClass('pm_study_autocomplete').css({'background-color': item.color}).append(item.category).appendTo(ul);
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

  // Store the plate ID and the target DOM element
  this.plateId = plate_id
  this.target = $('#' + target)

  // Retrieve the plate information from the server
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
 * Initializes the object after the GET query is completed
 *
 * @param {Object} data The data returned from the GET query
 *
 **/
PlateMap.prototype.initialize = function (data) {
    var study, color;

    this.name = data.name;
    this.createdOn = data.created_on;
    this.createdBy = data.email;
    this.notes = data.notes;
    this.plateType = data.plate_type.notes;
    this.rows = data.plate_type.rows;
    this.cols = data.plate_type.cols;
    this.studies = data.studies;

    // Construct a dictionary keyed by sample, for easy access to the sample
    // information
    this.samples = {}
    // This is a special list needed for initializing the sample autocompletion
    this.autoCompleteSamples = []
    // Iterate over all the studies
    for (var idx = 0; idx < this.studies.length; idx++) {
      study = this.studies[idx];
      color = PlateMap._qiimeColors[idx];
      // Iterate over all samples
      for (var sample of study.samples.all) {
        this.samples[sample] = {color: color, plate: []};
        this.autoCompleteSamples.push({label: sample, category: study.title, color: color});
      }
      // Iterate over all plates to get the already plated samples
      for (var plate in study.samples.plated) {
        if (study.samples.plated.hasOwnProperty(plate)) {
          this.samples[sample].plate.push(plate);
        }
      }
    }

    // Create a 2D array to store the per well information
    this.wellInformation = new Array(this.rows);
    for (var i = 0; i < this.wellInformation.length; i++) {
      this.wellInformation[i] = new Array(this.cols);
      for (var j = 0; j < this.wellInformation[i].length; j++) {
          this.wellInformation[i][j] = {inputTag: undefined, comment: undefined};
      }
    }

    this.drawPlate();
};

/**
 *
 * Updates the contents of the text area with a summary of the well comments
 *
 **/
PlateMap.prototype.updateWellCommentsArea = function () {
  var sample, wellId, wellInfo;
  var comments = "";
  for (var i = 0; i < this.rows; i++) {
    for (var j = 0; j < this.cols; j++) {
      wellInfo = this.wellInformation[i][j];
      if (wellInfo.comment !== undefined) {
        sample = wellInfo.inputTag.val().trim();
        if (sample.length === 0) {
          sample = 'No sample plated';
        }
        wellId = String.fromCharCode('A'.charCodeAt() + i) + (j + 1);
        comments = comments + "Well " + wellId + " (Sample: " + sample + "): " + wellInfo.comment + "\n";
      }
    }
  }
  $("#well-comments-area").val(comments);
}

/**
 *
 * Keypress event handler on the well input
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
    // Set the focus to the next input tag
    this.wellInformation[row][col].inputTag.focus();
  }
}

/**
 *
 * Change event handler on the well input
 *
 * @param {Elemnt} current The <input> element where the event has been trigered
 * @param {Event} e The event object
 *
 **/
PlateMap.prototype.changeWell = function (current, e) {
  var sample, sampleInfo, row, col;
  sample = $(current).val().trim();

  sampleInfo = this.samples[sample];

  if (sampleInfo === undefined) {
    // This sample is not recognized - mark the well as problematic
    $(current).css({'background-color': 'red'});
  } else {
    $(current).css({'background-color': sampleInfo.color});
  }

  // TODO: control the proceed to extraction button
}

/**
 *
 * Show event handler on the well comment modal
 *
 **/
PlateMap.prototype.commentModalShow = function () {
  var row = parseInt($('#comment-modal-btn').attr('pm-row'));
  var col = parseInt($('#comment-modal-btn').attr('pm-col'));
  // Magic number + 1 -> correct index because JavaScript arrays start at 0
  var wellId = String.fromCharCode('A'.charCodeAt() + row) + (col + 1);
  var wellInfo = this.wellInformation[row][col];
  var sample = wellInfo.inputTag.val().trim();
  if (sample.length === 0) {
    sample = 'No sample plated';
  }
  var value = (wellInfo.comment !== undefined) ? wellInfo.comment : "";
  $('#well-comment-textarea').val(value);
  $('#exampleModalLabel').html('Adding comment to well ' + wellId + ' (Sample: <i>' + sample + '</i>)');
}

/**
 *
 * Click event handler on the save button form the comment modal
 *
 **/
PlateMap.prototype.commentModalSave = function () {
  var row = parseInt($('#comment-modal-btn').attr('pm-row'));
  var col = parseInt($('#comment-modal-btn').attr('pm-col'));
  this.wellInformation[row][col].comment = $('#well-comment-textarea').val();
  this.updateWellCommentsArea();
  $('#myModal').modal('hide');
}


/**
 *
 * Constructs the HTML elements of a well
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
    // When the input element gets focus, store the current indices
    // so we know the well the user wants to comment on.
    $('#comment-modal-btn').attr('pm-row', parseInt($(this).attr('pm-well-row')));
    $('#comment-modal-btn').attr('pm-col', parseInt($(this).attr('pm-well-column')));
  });
  i.change(function(e) {
    obj.changeWell(this, e);
  });
  i.addClass('form-control').addClass('autocomplete').addClass('pm-well');
  i.attr('placeholder', 'Type sample').attr('pm-well-row', row).attr('pm-well-column', column).attr('type', 'text');
  i.appendTo(d);
  // Store the input in the array for easy access when navigating on the
  // plate map
  this.wellInformation[row][column].inputTag = i;
  // Return the top div
  return d;
};


/**
 *
 * Constructs the HTML elements of the plate map
 *
 **/
PlateMap.prototype.drawPlate = function() {
  var row, col, well, table, textArea, btn, span, obj, study;
  obj = this;

  // Add the header
  $('<label><h3>Plate <i>' + this.name + '</i> (ID: ' + this.plateId + ') &nbsp;&nbsp;</h3></label>').appendTo(this.target);
  // Add the buttons next to the header
  // Save button
  btn = $('<button>').addClass('btn btn-info').attr('type', 'button').appendTo(this.target).append(' Save');
  $('<span>').addClass('glyphicon glyphicon-save').prependTo(btn);
  this.target.append(' ');
  // Proceed to extraction button
  btn = $('<button>').addClass('btn btn-success').attr('type', 'button').appendTo(this.target).append(' Extract');
  $('<span>').addClass('glyphicon glyphicon-share').prependTo(btn);
  this.target.append(' ');
  // Add the comment button. We need to add it in a span so we can have both
  // the bootstrap tooltip and the modal triggered
  span = $('<span>').attr('data-toggle', 'tooltip').attr('data-placement', 'right').attr('title', 'Add well comment').attr('id', 'well-comment');
  span.appendTo(this.target);
  span.tooltip();
  btn =  $('<button>').addClass('btn').append(' Comment well');
  btn.attr('type', 'button').attr('data-toggle', 'modal').attr('data-target', '#myModal').attr('id', 'comment-modal-btn').attr('pm-row', 0).attr('pm-col', 0);
  $('<span>').addClass('glyphicon glyphicon-comment').prependTo(btn);
  btn.appendTo(span);
  // Add the plate information
  $('</br><b>Plate type: </b>' + this.plateType + '</br>').appendTo(this.target);
  $('<b>Created on: </b>' + this.createdOn + '</br>').appendTo(this.target);
  $('<b>Created by: </b>' + this.createdBy + '</br>').appendTo(this.target);
  // Add studies
  $('<b>Studies:</b>').appendTo(this.target);
  $.each(this.studies, function(idx, study) {
      obj.target.append(' ');
      $('<span>').css({'background-color': PlateMap._qiimeColors[idx]}).html("&nbsp;&nbsp;&nbsp;&nbsp;").appendTo(obj.target);
      obj.target.append(' ' + study.title + ' (');
      $('<a>').attr('target', '_blank').attr('href', 'https://qiita.ucsd.edu/study/description/' + study.study_id).text('Qiita: ' + study.study_id).appendTo(obj.target);
      obj.target.append(', ');
      $('<a>').attr('target', '_blank').attr('href', 'http://kl-jira.ucsd.edu:8080/projects/' + study.jira_id).text('Jira: ' + study.jira_id).appendTo(obj.target);
      obj.target.append(')');
  });


  // Add the table that represents the plate map
  table = $('<table>');
  table.appendTo(this.target);

  // Add the header row
  row = $('<tr>');
  row.appendTo(table);
  $('<th>').appendTo(row);
  for (var i = 0; i < this.cols; i++) {
    col = $('<th>');
    col.attr('style', 'text-align: center;')
    col.html(i+1);
    col.appendTo(row);
  }

  // Adding the rest of the rows
  for (var i = 0; i < this.rows; i++) {
    row = $('<tr>');
    row.appendTo(table);
    // Adding row name - From: http://stackoverflow.com/a/12504060
    col = $('<td>');
    col.html(String.fromCharCode('A'.charCodeAt() + i));
    col.appendTo(row);
    // Adding the rest of the rows
    for (var j = 0; j < this.cols; j++) {
      col = $('<td>');
      col.appendTo(row);
      well = this.constructWell(i, j);
      well.appendTo(col);
    }
  }

  // Add the Notes text area
  $('<b>Plate notes: </b></br>').appendTo(this.target);
  textArea = $('<textarea cols="200" id="notes-input"></textarea></br>').appendTo(this.target);
  if (this.notes !== undefined) {
    textArea.val(this.notes);
  }

  // Add the per well comments summary
  $('<b>Per well comments: </b></br>').appendTo(this.target);
  $('<textarea cols="200" id="well-comments-area" readonly></textarea></br>').appendTo(this.target);


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

  // Attach a handler to the save button
  $('#save-cmt-btn').click(function(e) {
    obj.commentModalSave();
  });

  // Attach a handler to the keyup event of the well comment text area
  $('#well-comment-textarea').keyup(function(e) {
    var value = $('#well-comment-textarea').val().trim();
    // Only enable the button if there is some text in the textarea
    $('#save-cmt-btn').prop('disabled', value.length === 0);
  });

  // Enable autocompletion
  $(".autocomplete").catcomplete({source: this.autoCompleteSamples});
}


// This is a modified QIIME color palette grabbed from Emperor
// https://github.com/biocore/emperor/blob/new-api/emperor/support_files/js/color-view-controller.js
// The colors have been represented in rgba so we can change the alpha value to 0.25
// The original QIIME color palette had 24 colors. We have added 2 extra colors
// The first one is a transparent color, and the last one is a custom gray
/** @private */
PlateMap._qiimeColors = ['rgba(0,0,0,0)', 'rgba(255,0,0,0.25)', 'rgba(0,0,255,0.25)',
  'rgba(242,115,4,0.25)', 'rgba(0,128,0,0.25)', 'rgba(145,39,141,0.25)',
  'rgba(255,255,0,0.25)', 'rgba(124,236,244,0.25)', 'rgba(244,154,194,0.25)',
  'rgba(93,160,158,0.25)', 'rgba(107,68,11,0.25)', 'rgba(128,128,128,0.25)',
  'rgba(247,150,121,0.25)', 'rgba(125,169,216,0.25)', 'rgba(252,198,136,0.25)',
  'rgba(128,201,155,0.25)', 'rgba(162,135,191,0.25)', 'rgba(255,248,153,0.25)',
  'rgba(196,156,107,0.25)', 'rgba(192,192,192,0.25)', 'rgba(237,0,138,0.25)',
  'rgba(0,182,255,0.25)', 'rgba(165,71,0,0.25)', 'rgba(128,128,0,0.25)',
  'rgba(0,128,128,0.25)', 'rgba(169,169,169,0.50)'];
