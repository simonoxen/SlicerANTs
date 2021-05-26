import qt, ctk, slicer
from .delegates import ComboDelegate, MRMLComboDelegate, SpinBoxDelegate, TextEditDelegate
from ..util import antsTransform, antsMetric


class CustomTable(qt.QWidget):

  RowHeight = 25

  def __init__(self, columnNames):
    super().__init__()

    self.addButton = qt.QPushButton('+')
    self.addButton.clicked.connect(self.onAddButton)

    self.removeButton = qt.QPushButton('-')
    self.removeButton.clicked.connect(self.onRemoveButton)

    self.linkStagesPushButton = qt.QPushButton('Link Stages')
    self.linkStagesPushButton.checkable = True
    self.linkStagesPushButton.checked = True

    buttonsFrame = qt.QFrame()
    buttonsFrame.setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
    buttonsFrame.setLayout(qt.QHBoxLayout())
    buttonsFrame.layout().addWidget(self.addButton)
    buttonsFrame.layout().addWidget(self.removeButton)
    buttonsFrame.layout().addWidget(self.linkStagesPushButton)

    self.model = qt.QStandardItemModel(1, len(columnNames))
    for i, columnName in enumerate(columnNames):
      self.model.setHeaderData(i, qt.Qt.Horizontal, columnName)

    self.view = qt.QTableView()
    self.view.setEditTriggers(self.view.CurrentChanged + self.view.DoubleClicked + self.view.SelectedClicked)
    self.view.setSelectionMode(self.view.SingleSelection)
    self.view.setSelectionBehavior(self.view.SelectRows)
    self.view.horizontalHeader().setStretchLastSection(True)
    self.view.setHorizontalScrollMode(self.view.ScrollPerPixel)
    self.view.verticalHeader().setMaximumSectionSize(self.RowHeight)
    self.view.verticalHeader().setMinimumSectionSize(self.RowHeight)
    self.view.verticalHeader().setDefaultSectionSize(self.RowHeight)
    self.view.setFixedHeight(65)
    self.view.setModel(self.model)
    self.view.setCurrentIndex(self.model.index(0,0))

    self.view.selectionModel().selectionChanged.connect(self.onSelectionChanged)

    layout = qt.QVBoxLayout(self)
    layout.addWidget(buttonsFrame)
    layout.addWidget(self.view)

    return layout
  
  def onAddButton(self):
    self.addRowAndSetHeight()
    newRowN = self.model.rowCount()-1
    self.setDefaultNthRow(newRowN)
    self.view.setCurrentIndex(self.model.index(newRowN,0))

  def addRowAndSetHeight(self):
    self.model.insertRow(self.model.rowCount())
    self.view.setFixedHeight(self.view.height+self.RowHeight)

  def onRemoveButton(self):
    if self.model.rowCount() == 1:
      return
    else:
      self.removeSelectedRow()
  
  def removeSelectedRow(self):
    selectedRow = self.getSelectedRow()
    if selectedRow is not None:
      self.removeRowAndSetHeight(selectedRow)

  def removeRowAndSetHeight(self, rowNumber):
    self.model.removeRow(rowNumber)
    self.view.setFixedHeight(self.view.height-self.RowHeight)

  def getSelectedRow(self):
    selectedRows = self.view.selectionModel().selectedRows()
    for selectedRow in selectedRows:
      return selectedRow.row() # is a single selection view

  def onSelectionChanged(self, selection):
    pass

  def getParametersFromGUI(self):
    parameters = []
    for i in range(self.model.rowCount()):
      parameters.append(self.getNthRowParametersFromGUI(i))
    return parameters

  def getNthRowParametersFromGUI(self, N):
    parameters = {}
    for col in range(self.model.columnCount()):
      index = self.model.index(N, col)
      itemData = self.model.itemData(index)
      if qt.Qt.UserRole in itemData.keys():
        data = itemData[qt.Qt.UserRole]
      elif qt.Qt.DisplayRole in itemData.keys():
        data = itemData[qt.Qt.DisplayRole]
      else:
        data = ''
      parameters[self.camelCaseHeader(col)] = data
    return parameters

  def camelCaseHeader(self, column):
    out = self.model.headerData(column, qt.Qt.Horizontal)
    out = out.replace(' ', '')
    return out[0].lower() + out[1:]

  def setGUIFromParameters(self, parameters):
    for N,params in enumerate(parameters):
      if N == self.model.rowCount():
        self.addRowAndSetHeight()
      self.setNthRowGUIFromParameters(N, params)
    while self.model.rowCount()-1 > N:
      self.removeRowAndSetHeight(self.model.rowCount()-1)

  def setNthRowGUIFromParameters(self, N, parameters):
    for col,val in enumerate(parameters.values()):
      index = self.model.index(N, col)
      try: # check if value is mrml node and save as user role
        node = slicer.util.getNode(val)
        self.model.setData(index, val, qt.Qt.UserRole)
        val = node.GetName()
      except:
        pass
      self.model.setData(index, val, qt.Qt.DisplayRole)

class TableWithSettings(CustomTable):
  def __init__(self, columnNames):
    layout = CustomTable.__init__(self, columnNames)

    self.settingsFormatText = ctk.ctkFittedTextBrowser()
    self.settingsFormatText.setSizePolicy(qt.QSizePolicy.Ignored, qt.QSizePolicy.Preferred)
    self.settingsFormatText.sizePolicy.setHorizontalStretch(1)
    self.settingsFormatText.sizePolicy.setVerticalStretch(0)
    self.settingsFormatText.setFrameShape(qt.QFrame.NoFrame)
    self.settingsFormatText.setFrameShadow(qt.QFrame.Plain)
    self.settingsFormatText.openExternalLinks = 1
    self.settingsFormatText.openLinks = 1
    self.settingsFormatText.showDetailsText = 'Show Settings Format.'
    self.settingsFormatText.hideDetailsText = 'Hide Settings Format.'

    self.settingsFormatText.setCollapsibleText('<html><br> </html>')
    # self.settingsFormatText.setCollapsibleText(\
    #   '<html>Paint with a round brush<br>.\
    #   <p><ul style=\margin: 0\>\
    #   <li><b>Left-button drag-and-drop:</b> paint strokes.</li>\
    #   <li><b>Shift + mouse wheel</b> or <b>+/- keys:</b> adjust brush size.</li>\
    #   <li><b>Ctrl + mouse wheel:</b> slice view zoom in/out.</li>\
    #   </ul><p>\
    #   Editing is available both in slice and 3D views.\
    #   <p></html>')

    layout.addWidget(self.settingsFormatText)

    self.view.setItemDelegateForColumn(0, ComboDelegate(self.model, self.antsType, self.setSettingsFormatTextFromName))
    self.view.setItemDelegateForColumn(self.model.columnCount()-1, TextEditDelegate(self.model, self.antsType))

  def onSelectionChanged(self, selection):
    super().onSelectionChanged(selection)
    indexes = selection.indexes()
    if indexes:
      key = self.model.data(indexes[0].siblingAtColumn(0))
      self.setSettingsFormatTextFromName(key)
      
  def setSettingsFormatTextFromName(self, name):
    text = self.antsType.getSubClassByName(name).settingsFormat
    self.settingsFormatText.setCollapsibleText('<html><br> ' + text + ' </html>')
    self.settingsFormatText.setMinimumHeight(self.settingsFormatText.sizeHint.height())
    if self.settingsFormatText.layout():
      self.settingsFormatText.layout().update()

class StagesTable(TableWithSettings):
  def __init__(self):
    columnNames = ['Transform', 'Settings']
    self.antsType = antsTransform()
    TableWithSettings.__init__(self, columnNames)

    self.settingsFormatText.setToolTip("The gradientStep or learningRate characterizes the gradient descent optimization and is scaled appropriately for each transform using the shift scales estimator. Subsequent parameters are transform-specific and can be determined from the usage. For the B-spline transforms one can also specify the smoothing in terms of spline distance (i.e. knot spacing).")
    self.linkStagesPushButton.delete()

  def setDefaultNthRow(self, N):
    index = self.model.index(N, 0)
    aboveData =  self.model.data(index.siblingAtRow(N-1))
    if aboveData == 'Rigid':
      newData = 'Affine'
    else:
      newData = 'SyN'
    self.model.setData(index, newData)

  def onRemoveButton(self):
    pass # this is handled by antsRegistration Widget
  
class MetricsTable(TableWithSettings):
  def __init__(self):
    columnNames = ['Type', 'Fixed', 'Moving', 'Settings']
    self.antsType = antsMetric()
    TableWithSettings.__init__(self, columnNames)

    self.settingsFormatText.setToolTip(" The 'metricWeight' variable is used to modulate the per stage weighting of the metrics. The metrics can also employ a sampling strategy defined by a sampling percentage. The sampling strategy defaults to 'None' (aka a dense sampling of one sample per voxel), otherwise it defines a point set over which to optimize the metric. The point set can be on a regular lattice or a random lattice of points slightly perturbed to minimize aliasing artifacts. samplingPercentage defines the fraction of points to select from the domain.")

    self.view.setItemDelegateForColumn(1, MRMLComboDelegate(self.model))
    self.view.setItemDelegateForColumn(2, MRMLComboDelegate(self.model))

  def setDefaultNthRow(self, N):
    index = self.model.index(N, 0)
    self.model.setData(index, 'MI')

class LevelsTable(CustomTable):

  def __init__(self):
    columnNames = ['Convergence', 'Smoothing Sigmas', 'Shrink Factors']
    layout = CustomTable.__init__(self, columnNames)

    self.view.setItemDelegateForColumn(0, SpinBoxDelegate(self.model))
    self.view.setItemDelegateForColumn(1, SpinBoxDelegate(self.model))
    self.view.setItemDelegateForColumn(2, SpinBoxDelegate(self.model))

    self.smoothingSigmasUnitComboBox = qt.QComboBox()
    self.smoothingSigmasUnitComboBox.addItems(['vox', 'mm'])

    self.convergenceThresholdSpinBox = qt.QSpinBox()

    self.convergenceWindowSizeSpinBox = qt.QSpinBox()

    levelsSettingsFrame = qt.QFrame()
    levelsSettingsFrame.setLayout(qt.QFormLayout())
    levelsSettingsFrame.layout().addRow('Smoothing Sigmas Unit: ', self.smoothingSigmasUnitComboBox)
    levelsSettingsFrame.layout().addRow('Convergence Threshold (1e-N): ', self.convergenceThresholdSpinBox)
    levelsSettingsFrame.layout().addRow('Convergence Window Size: ', self.convergenceWindowSizeSpinBox)

    layout.addWidget(levelsSettingsFrame)

  def setDefaultNthRow(self, N):
    for column in range(3):
      index = self.model.index(N, column)
      aboveIndex =  index.siblingAtRow(N-1)
      newData = max(1, round(self.model.data(aboveIndex) * 0.5))
      self.model.setData(index, newData)

  def getParametersFromGUI(self):
    parameters = {}
    parameters['steps'] = super().getParametersFromGUI()
    parameters['smoothingSigmasUnit'] = self.smoothingSigmasUnitComboBox.currentText
    parameters['convergenceThreshold'] = self.convergenceThresholdSpinBox.value
    parameters['convergenceWindowSize'] = self.convergenceWindowSizeSpinBox.value
    return parameters

  def setGUIFromParameters(self, parameters):
    super().setGUIFromParameters(parameters['steps'])
    self.smoothingSigmasUnitComboBox.currentText = parameters['smoothingSigmasUnit']
    self.convergenceThresholdSpinBox.value = int(parameters['convergenceThreshold'])
    self.convergenceWindowSizeSpinBox.value = int(parameters['convergenceWindowSize'])