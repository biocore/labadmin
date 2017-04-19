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
          $('<li>').addClass('pm-study-autocomplete').css({'background-color': item.color}).append(item.category).appendTo(ul);
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
 * @param {int} plateId The plate id
 *
 * @return {PlateMap}
 * @constructs PlateMap
 *
 **/
function PlateMap(target, plateId) {
  var that = this;

  // Store the plate ID and the target DOM element
  this.plateId = plateId;
  this.target = $('#' + target);

  // Retrieve the plate information from the server
  $.get('/pm_sample_plate?plate_id=' + plateId, function (data) {
    that.initialize(data);
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      if(jqXHR.status === 404) {
        var data = $.parseJSON(jqXHR.responseText);
        $('<h3 class="warning">').html(data.message).appendTo(that.target);
      } else {
        $('<div>').html(jqXHR.responseText).appendTo(that.target);
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
    this.technicalReplicates = [];

    // Construct a dictionary keyed by sample, for easy access to the sample
    // information
    this.samples = {};
    // This is a special list needed for initializing the sample autocompletion
    this.autoCompleteSamples = [];
    // Iterate over all the studies
    for (var idx = 0; idx < this.studies.length; idx++) {
      study = this.studies[idx];
      color = PlateMap._qiimeColors[idx];
      // Iterate over all samples
      for (var sample of study.samples.all) {
        this.samples[sample] = {color: color, plates: [], wells: [], sampleId: sample};
        this.autoCompleteSamples.push({label: sample, category: study.title, color: color});
      }
      // Iterate over all plates to get the already plated samples
      for (var plate in study.samples.plated) {
        if (study.samples.plated.hasOwnProperty(plate)) {
          for (var sample of study.samples.plated[plate]) {
            this.samples[sample].plates.push(plate);
          }
        }
      }
    }

    // Add the blanks information
    color = PlateMap._qiimeColors[PlateMap._qiimeColors.length - 1];
    for (var blank of data.blanks) {
      this.samples[blank] = {color: color, plates: [], wells: [], sampleId: blank};
      this.autoCompleteSamples.push({label: blank, category: 'Controls', color: color});
    }

    // Create a 2D array to store the per well information
    this.wellInformation = new Array(this.rows);
    for (var i = 0; i < this.wellInformation.length; i++) {
      this.wellInformation[i] = new Array(this.cols);
      for (var j = 0; j < this.wellInformation[i].length; j++) {
        this.wellInformation[i][j] = {inputTag: null, comment: null};
      }
    }

    // Create the GUI
    this._drawPlate();

    // If this plate was already partially full, populate the interface with
    // the information received
    if (data.layout.length > 0) {
      this._populatePlate(data.layout);
    }
};

/**
 *
 * Populates the GUI with the plate information
 *
 * @param {Array} layout The plate information
 **/
PlateMap.prototype._populatePlate = function (layout) {
  var well, sample;
  for (var i = 0; i < this.rows; i++) {
    for (var j = 0; j < this.cols; j++) {
      well = layout[i][j];
      this.updateWellComment(i, j, well.notes);
      sample = "";
      if (well.sample_id) {
        sample = well.sample_id;
      } else if (well.name) {
        sample = well.name;
      }
      this.wellInformation[i][j].inputTag.val(sample);
      this.wellInformation[i][j].inputTag.trigger('change');
    }
  }
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
 PlateMap.prototype._formatRowId = function (row, col) {
   if (this.rows > 28) {
     return String(i + 1);
   }
   else {
     return String.fromCharCode('A'.charCodeAt() + row);
   }
 }
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
PlateMap.prototype._formatWellId = function (row, col) {
  var rId = this._formatRowId(row);
  var sep = (this.rows > 28) ? '-' : '';
  var cId = String(col + 1);
  return rId + sep + cId;
}

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
      if (wellInfo.comment !== null) {
        sample = wellInfo.inputTag.val().trim();
        if (sample.length === 0) {
          sample = 'No sample plated';
        }
        wellId = this._formatWellId(i, j);
        comments += "Well " + wellId + " (Sample: " + sample + "): " + wellInfo.comment + "\n";
      }
    }
  }
  $("#well-comments-area").val(comments);
}

/**
 *
 * Constructs the layout to be sent to the server
 *
 * @return {Array}
 *
 **/
PlateMap.prototype._constructLayout = function () {
  var layout, row, wellInfo, sample;

  layout = [];
  for (var wellRow of this.wellInformation) {
    row = [];
    for (var well of wellRow) {
      wellInfo = {};
      wellInfo.notes = well.comment;
      sample = well.inputTag.val().trim();
      if (sample.length > 0) {
        if (this.samples.hasOwnProperty(sample)) {
          wellInfo.sample_id = sample;
        } else {
          wellInfo.name = sample;
        }
      }
      row.push(wellInfo);
    }
    layout.push(row);
  }
  return layout;
}

/**
 *
 * Saves the current layout in the server
 *
 **/
PlateMap.prototype.savePlate = function () {
  var layout = this._constructLayout();
  $('#save-btn-icon').removeClass('glyphicon glyphicon-save').addClass('glyphicon glyphicon-refresh');
  $.post($(location).attr('href'), {action: 'save', layout: JSON.stringify(layout), plate_id: this.plateId}, function(data) {
    $('#save-btn-icon').removeClass('glyphicon glyphicon-refresh').addClass('glyphicon glyphicon-ok');
    setTimeout(function() {
      $('#save-btn-icon').removeClass('glyphicon glyphicon-ok').addClass('glyphicon glyphicon-save');
    }, 5000);
  });
}

/**
 *
 * Proceeds to the plate extraction page
 *
 **/
PlateMap.prototype.extractPlate = function () {

  var layout = this._constructLayout();
  var form = $('<form>', {action: $(location).attr('href'), method: 'post'});
  var fields = {action: 'extract', plate_id: this.plateId,
                layout: JSON.stringify(layout)};
  $.each(fields, function(key, val) {
    $('<input>').attr({type: "hidden", name: key, value: val}).appendTo(form);
  });
  form.appendTo('body').submit();
}

/**
 *
 * Keypress event handler on the well input
 *
 * @param {Element} current The <input> element where the event has been trigered
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
 * Updates the GUI to show the technical replicates
 *
 * @param {Object} sampleInfo The sample information object
 *
 **/
PlateMap.prototype._updateTechnicalReplicate = function (sampleInfo) {
  if (sampleInfo.wells.length > 1) {
    // Update the list of technical replicates
    if ($.inArray(sampleInfo, this.technicalReplicates) == -1) {
      this.technicalReplicates.push(sampleInfo);
    }
    // Mark all wells as technical
    for (var well of sampleInfo.wells) {
      // Well is an array of two ints, in which well[0] -> row and well[1] -> col
      this.wellInformation[well[0]][well[1]].inputTag.addClass('pm-technical-replicate');
    }
  } else {
    // Using a for loop to avoid to special case - If the wells list is
    // empty, this for loop will not execute anything. If there is one element
    // it will correctly remove the mark for techincal replicates
    for (var well of sampleInfo.wells) {
      this.wellInformation[well[0]][well[1]].inputTag.removeClass('pm-technical-replicate');
    }
    // Remove from the techincal replicates list
    this.technicalReplicates = $.grep(this.technicalReplicates, function(value) {
      return value != sampleInfo;
    });
  }
}

/**
 *
 * Updates the GUI to show the error list
 *
 **/
PlateMap.prototype.updateErrorList = function () {
  var well, message, $li;
  // Empty the current list
  $("#pm-error-list").html("");

  // First look for any warning/error in a per well basis
  for (var i = 0; i < this.rows; i++) {
    for (var j = 0; j < this.cols; j++) {
      well = this.wellInformation[i][j];
      if (well.inputTag.hasClass('pm-wrong-sample')) {
        // Add an error to the list
        message = 'Well ' + this._formatWellId(i, j) + ': Sample "' + well.inputTag.val().trim() + '" not found in any study';
        $('<li>').addClass('list-group-item').addClass('list-group-item-danger').html(message).appendTo('#pm-error-list');
      } else if (well.inputTag.hasClass('pm-sample-plated')) {
        // Add a warning to the list
        sample = well.inputTag.val().trim();
        message = 'Well ' + this._formatWellId(i, j) + ': Sample "' + sample + '" previously plated in plate(s): ';
        $li = $('<li>').addClass('list-group-item').addClass('list-group-item-warning').html(message).appendTo('#pm-error-list');
        // Add a link for each plate that the sample is already plated
        for (var plate of this.samples[sample].plates) {
          $('<a>').attr('href', '/pm_plate_map?plate_id=' + plate).attr('target', '_blank').text(plate + ' ').appendTo($li);
        }
      }
    }
  }

  for (var sampleInfo of this.technicalReplicates) {
    message = 'Sample "' + sampleInfo.sampleId + '" plated multiple times on wells: ';
    for (var well of sampleInfo.wells) {
      message += this._formatWellId(well[0], well[1]) + ' ';
    }
    $('<li>').addClass('list-group-item').addClass('list-group-item-info').html(message).appendTo('#pm-error-list');
  }
};

/**
 *
 * Change event handler on the well input
 *
 * @param {Element} current The <input> element where the event has been trigered
 * @param {Event} e The event object
 *
 **/
PlateMap.prototype.changeWell = function (current, e) {
  var sample, sampleInfo, prevSampleInfo, wellId;
  sample = $(current).val().trim();

  sampleInfo = this.samples[sample];

  // Clean any extra style that we added
  $(current).removeClass('pm-sample-plated').removeClass('pm-wrong-sample').removeClass('pm-technical-replicate');

  // Check if there was a sample plated here, so we can update technical
  // duplicate information
  prevSampleInfo = this.samples[$(current).data('pm-sample')];
  // Store the well Id as a list with 2 elements: the row # and the col #
  // This will simplify updating the interface
  wellId = [parseInt($(current).attr('pm-well-row')),
            parseInt($(current).attr('pm-well-column'))];
  if (prevSampleInfo !== undefined) {
    // We had another sample in this well before, update the wells list
    // of that sample
    prevSampleInfo.wells = $.grep(prevSampleInfo.wells, function(value) {
      return (value[0] !== wellId[0]) || (value[1] !== wellId[1]);
    });
    this._updateTechnicalReplicate(prevSampleInfo);
  }

  if (sample.length > 0) {
    if (sampleInfo === undefined) {
      // This sample is not recognized - mark the well as problematic
      $(current).css({'background-color': 'red'}).addClass('pm-wrong-sample');
    } else {
      // This sample belongs to a study - label the background with the
      // same color as the study
      $(current).css({'background-color': sampleInfo.color});

      // Add the current well to the sample information
      $(current).data('pm-sample', sample);
      sampleInfo.wells.push(wellId);
      // Check for technical duplicates
      this._updateTechnicalReplicate(sampleInfo);

      // Check if it has been plated before
      if (sampleInfo.plates.length > 0) {
        $(current).addClass('pm-sample-plated');
      }
    }
  } else {
    $(current).css({'background-color': 'rgba(0,0,0,0)'});
  }

  // Control the proceed to extraction button
  $('#extract-btn').prop('disabled', $('.pm-wrong-sample').length > 0);

  // Update the plate errors/warnings text area
  this.updateErrorList();
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
  var wellId = this._formatWellId(row, col);
  var wellInfo = this.wellInformation[row][col];
  var sample = wellInfo.inputTag.val().trim();
  if (sample.length === 0) {
    sample = 'No sample plated';
  }
  var value = wellInfo.comment || "";
  $('#well-comment-textarea').val(value);
  $('#wellCommentModalLabel').html('Adding comment to well ' + wellId + ' (Sample: <i>' + sample + '</i>)');
}

/**
 *
 * Updates the comment of a well and handles all the GUI changes
 *
 * @param {int} row The row of the well
 * @param {int} col The col of the well
 * @param {string} comment The comment to attach to the well
 *
 **/
PlateMap.prototype.updateWellComment = function (row, col, comment) {
  var wellInfo = this.wellInformation[row][col];
  wellInfo.comment = comment;
  if (comment) {
    wellInfo.inputTag.addClass('pm-well-commented');
  } else {
    wellInfo.inputTag.removeClass('pm-well-commented');
  }
  this.updateWellCommentsArea();
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
  var that = this;
  // Div holding well
  var $d = $('<div>');
  $d.addClass('input-group');
  // The input tag
  var $i = $('<input>');
  $i.keypress(function(e) {
    that.keypressWell(this, e);
  });
  $i.focusin(function(e) {
    // When the input element gets focus, store the current indices
    // so we know the well the user wants to comment on.
    $('#comment-modal-btn').attr('pm-row', parseInt($(this).attr('pm-well-row')));
    $('#comment-modal-btn').attr('pm-col', parseInt($(this).attr('pm-well-column')));
  });
  $i.change(function(e) {
    that.changeWell(this, e);
  });
  $i.addClass('form-control').addClass('autocomplete').addClass('pm-well');
  $i.attr('placeholder', 'Type sample').attr('pm-well-row', row).attr('pm-well-column', column).attr('type', 'text');
  $i.appendTo($d);
  $i.data('pm-sample', null);
  // Store the input in the array for easy access when navigating on the
  // plate map
  this.wellInformation[row][column].inputTag = $i;
  // Return the top div
  return $d;
};


/**
 *
 * Constructs the HTML elements of the plate map
 *
 **/
PlateMap.prototype._drawPlate = function() {
  var $row, $col, $well, $table, $textArea, $btn, $span, that, study;
  that = this;

  // Add the header
  $('<label><h3>Plate <i>' + this.name + '</i> (ID: ' + this.plateId + ') &nbsp;&nbsp;</h3></label>').appendTo(this.target);
  // Add the buttons next to the header
  // Save button
  $btn = $('<button>').addClass('btn btn-info').appendTo(this.target).append(' Save');
  $btn.click(function (e) {
    that.savePlate();
  });
  $('<span>').attr('id', 'save-btn-icon').addClass('glyphicon glyphicon-save').prependTo($btn);
  this.target.append(' ');
  // Proceed to extraction button
  $btn = $('<button>').addClass('btn btn-success').attr('id', 'extract-btn').appendTo(this.target).append(' Extract');
  $('<span>').addClass('glyphicon glyphicon-share').prependTo($btn);
  $btn.click(function (e) {
    that.extractPlate();
  });
  this.target.append(' ');
  // Add the comment button. We need to add it in a span so we can have both
  // the bootstrap tooltip and the modal triggered
  $span = $('<span>').attr('data-toggle', 'tooltip').attr('data-placement', 'right').attr('title', 'Add well comment').attr('id', 'well-comment');
  $span.appendTo(this.target);
  $span.tooltip();
  $btn =  $('<button>').addClass('btn').append(' Comment well');
  $btn.attr('data-toggle', 'modal').attr('data-target', '#wellCommentModal').attr('id', 'comment-modal-btn').attr('pm-row', 0).attr('pm-col', 0);
  $('<span>').addClass('glyphicon glyphicon-comment').prependTo($btn);
  $btn.appendTo($span);
  this.target.append(' ');
  // Add the help button
  $btn = $('<button>').addClass('btn btn-info').appendTo(this.target).append(' Help');
  $btn.attr('data-toggle', 'modal').attr('data-target', '#myHelpModal');
  $('<span>').addClass('glyphicon glyphicon-info-sign').prependTo($btn);


  // Add the plate information
  $('</br><b>Plate type: </b>' + this.plateType + '</br>').appendTo(this.target);
  $('<b>Created on: </b>' + this.createdOn + '</br>').appendTo(this.target);
  $('<b>Created by: </b>' + this.createdBy + '</br>').appendTo(this.target);
  // Add studies
  $('<b>Studies:</b>').appendTo(this.target);
  $.each(this.studies, function(idx, study) {
      that.target.append(' ');
      $('<span>').css({'background-color': PlateMap._qiimeColors[idx]}).html("&nbsp;&nbsp;&nbsp;&nbsp;").appendTo(that.target);
      that.target.append(' ' + study.title + ' (');
      $('<a>').attr('target', '_blank').attr('href', 'https://qiita.ucsd.edu/study/description/' + study.study_id).text('Qiita: ' + study.study_id).appendTo(that.target);
      that.target.append(', ');
      $('<a>').attr('target', '_blank').attr('href', 'http://kl-jira.ucsd.edu:8080/projects/' + study.jira_id).text('Jira: ' + study.jira_id).appendTo(that.target);
      that.target.append(')');
  });

  // Add the table that represents the plate map
  $table = $('<table>');
  $table.appendTo(this.target);

  // Add the header row
  $row = $('<tr>');
  $row.appendTo($table);
  $('<th>').appendTo($row);
  for (var i = 0; i < this.cols; i++) {
    $col = $('<th>');
    $col.attr('style', 'text-align: center;')
    $col.html(i+1);
    $col.appendTo($row);
  }

  // Adding the rest of the rows
  for (var i = 0; i < this.rows; i++) {
    $row = $('<tr>');
    $row.appendTo($table);
    // Adding row name - From: http://stackoverflow.com/a/12504060
    $col = $('<td>');
    $col.html(this._formatRowId(i));
    $col.appendTo($row);
    // Adding the rest of the rows
    for (var j = 0; j < this.cols; j++) {
      $col = $('<td>');
      $col.appendTo($row);
      $well = this.constructWell(i, j);
      $well.appendTo($col);
    }
  }

  // Add the Notes text area
  $('<b>Plate notes: </b></br>').appendTo(this.target);
  $textArea = $('<textarea cols="200" id="notes-input"></textarea></br>').appendTo(this.target);
  if (this.notes !== undefined) {
    $textArea.val(this.notes);
  }

  // Add the per well comments summary
  $('<b>Per well comments: </b></br>').appendTo(this.target);
  $('<textarea cols="200" id="well-comments-area" readonly></textarea></br>').appendTo(this.target);

  // Add the plate warnings/error summary
  $('<b>Plate errors and warnings: </b></br>').appendTo(this.target);
  $('<ul class="list-group" id="pm-error-list">').appendTo(this.target);

  // Add the comments modal - Note that this modal gets added to the body
  // This is to avoid some undesired behavior with modals, in which they
  // get blocked "behind" the faded background
  $('<div class="modal fade" id="wellCommentModal" tabindex="-1" role="dialog" aria-labelledby="wellCommentModalLabel" aria-hidden="true">' +
    '<div class="modal-dialog" role="document">' +
      '<div class="modal-content">' +
        '<div class="modal-header">' +
          '<h4 class="modal-title" id="wellCommentModalLabel"></h4>' +
          '<button class="close" data-dismiss="modal" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span>' +
          '</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<textarea class="form-control" id="well-comment-textarea"></textarea>' +
        '</div>' +
        '<div class="modal-footer">' +
          '<button class="btn btn-secondary" data-dismiss="modal">Cancel</button>' +
          '<button class="btn btn-primary" id="save-cmt-btn" disabled>Save comment</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
  '</div>').appendTo($('body'));

  // Attach a handler to the modal show event
  $('#wellCommentModal').on('show.bs.modal', function (e) {
    that.commentModalShow();
  });

  // Attach a handler to the modal shown event
  $('#wellCommentModal').on('shown.bs.modal', function (e) {
    // We just need to make sure that the modal text area gets focused
    $('#well-comment-textarea').focus();
  });

  // Attach a handler to the save button
  $('#save-cmt-btn').click(function(e) {
    var row = parseInt($('#comment-modal-btn').attr('pm-row'));
    var col = parseInt($('#comment-modal-btn').attr('pm-col'));
    var cmt = $('#well-comment-textarea').val();
    that.updateWellComment(row, col, cmt);
    $('#wellCommentModal').modal('hide');
  });

  // Attach a handler to the keyup event of the well comment text area
  $('#well-comment-textarea').keyup(function(e) {
    var value = $('#well-comment-textarea').val().trim();
    // Only enable the button if there is some text in the textarea
    $('#save-cmt-btn').prop('disabled', value.length === 0);
  });

  // Add the helps modal - Note that this modal gets added to the body
  // This is to avoid some undesired behavior with modals, in which they
  // get blocked "behind" the faded background
  $('<div class="modal fade" id="myHelpModal" tabindex="-1" role="dialog" aria-labelledby="myHelpModalLabel" aria-hidden="true">' +
    '<div class="modal-dialog" role="document">' +
      '<div class="modal-content">' +
        '<div class="modal-header">' +
          '<h4 class="modal-title" id="myHelpModalLabel">Plate Map legend</h4>' +
          '<button class="close" data-dismiss="modal" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span>' +
          '</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<span><input placeholder="Example sample" type="text" disabled="True" class="pm-sample-plated" /> &nbsp;&nbsp; Sample already plated</span>' +
          '<span><input placeholder="Example sample" type="text" disabled="True" class="pm-well-commented" /> &nbsp;&nbsp; Well has a comment</span>' +
          '<span><input placeholder="Example sample" type="text" disabled="True" style="background-color: red;" /> &nbsp;&nbsp; Sample not recognized</span>' +
        '</div>' +
      '</div>' +
    '</div>' +
  '</div>').appendTo($('body'));

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
