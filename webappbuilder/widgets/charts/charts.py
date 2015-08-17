from webappbuilder.webbappwidget import WebAppWidget
import os
from PyQt4.QtGui import QIcon
import json
from webappbuilder.utils import findLayerByName

class ChartTool(WebAppWidget):

    _parameters = {"charts": {}}

    def write(self, appdef, folder, app, progress):
        li = "\n".join(["<li><a onclick=\"openChart('%s')\" href=\"#\">%s</a></li>" % (c,c)
                        for c in self._parameters["charts"]])
        app.tools.append('''<li class="dropdown">
                            <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                            <i class="glyphicon glyphicon-stats"></i> Charts <span class="caret"><span></a>
                            <ul class="dropdown-menu">
                              %s
                            </ul>
                          </li>''' % li)
        self.addScript("d3.min.js", folder, app)
        self.addScript("c3.min.js", folder, app)
        self.addScript("charts.js", folder, app)
        self.addCss("c3.min.css", folder, app)
        self.addCss("charts.css", folder, app)
        app.scripts.append('<script src="./charts.js"></script>')
        app.panels.append('''<div class="chart-panel" id="chart-panel">
                        <span class="chart-panel-info" id="chart-panel-info"></span>
                        <a href="#" id="chart-panel-closer" class="chart-panel-closer">Close</a>
                        <div id="chart"></div></div>''')
        chartsFilepath = os.path.join(folder, "charts.js")
        with open(chartsFilepath, "w") as f:
            f.write("var AGGREGATION_MIN = 0;")
            f.write("var AGGREGATION_MAX = 1;")
            f.write("var AGGREGATION_SUM = 2;")
            f.write("var AGGREGATION_AVG = 3;")
            f.write("var DISPLAY_MODE_FEATURE = 0;")
            f.write("var DISPLAY_MODE_CATEGORY = 1;")
            f.write("var DISPLAY_MODE_COUNT = 2;")
            f.write("var charts = " + json.dumps(self._parameters["charts"]))

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "chart-tool.png"))

    def description(self):
        return "Charts"

    def configure(self):
        dlg = ChartToolDialog(self._parameters["charts"])
        dlg.exec_()
        self._parameters = dlg.charts

    def checkProblems(self, appdef, problems):
        widgetNames = [w.name() for w in appdef["Widgets"].values()]
        charts = self._parameters["charts"]
        if len(charts) == 0:
            problems.append("Chart tool added, but no charts have been defined. "
                        "You should configure the chart tool and define at least one chart")
        if "selection" not in widgetNames:
            problems.append("Chart tool added, but the web app has no selection tools. "
                        "Charts are created based on selected features, so you should add selection "
                        "tools to the web app, to allow the user selecting features in the map")
        for name, chart in charts.iteritems():
            layer = findLayerByName(chart["layer"], appdef["Layers"])
            if layer is None:
                problems.append("Chart tool %s uses a layer (%s) that is not added to web app" % (name, chart["layer"]))
            if not layer.allowSelection:
                problems.append(("Chart tool %s uses a layer (%s) that does not allow selection. " +
                            "Selection should be enabled for that layer.") % (name, chart["layer"]))

from qgis.core import *
from PyQt4 import QtCore, QtGui
from ui_charttooldialog import Ui_ChartToolDialog
import copy
import sys

class ChartToolDialog(QtGui.QDialog, Ui_ChartToolDialog):
    def __init__(self, charts):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)
        self.charts = charts
        self._charts = copy.deepcopy(charts)
        self.populateLayers()
        self.populateList()
        if self.layers:
            self.populateFieldCombos(self.layers.keys()[0])
        self.layerCombo.currentIndexChanged.connect(self.layerComboChanged)
        self.displayModeCombo.currentIndexChanged.connect(self.displayModeComboChanged)
        self.addButton.clicked.connect(self.addChart)
        self.removeButton.clicked.connect(self.removeChart)
        self.chartsList.currentItemChanged.connect(self.selectionChanged)
        self.displayModeComboChanged()

    def displayModeComboChanged(self):
        visible = self.displayModeCombo.currentIndex() == 1
        self.operationCombo.setVisible(visible)
        self.operationLabel.setVisible(visible)
        visible = self.displayModeCombo.currentIndex() != 2
        isMac = sys.platform == 'darwin'
        self.valueFieldsCombo.setVisible(visible and not isMac)
        self.valueFieldsList.setVisible(visible and isMac)
        self.valueFieldsLabel.setVisible(visible)

    def selectionChanged(self):
        try:
            name = self.chartsList.currentItem().text()
        except:
            return
        self.nameBox.setText(name)
        idx = self.layerCombo.findText(self._charts[name]["layer"])
        self.layerCombo.setCurrentIndex(idx)
        idx = self.categoryFieldCombo.findText(self._charts[name]["categoryField"])
        self.categoryFieldCombo.setCurrentIndex(idx)
        self.displayModeCombo.setCurrentIndex(self._charts[name]["displayMode"])
        try:
            idx = self.operationCombo.findText()
            self.operationCombo.setCurrentIndex(self._charts[name]["operation"])
        except:
            pass
        try:
            offset = 0 if sys.platform == "darwin" else 1
            valueFields = self._charts[name]["valueFields"]
            for i in xrange(offset, self.model.rowCount()):
                item = self.model.item(i)
                item.setData(QtCore.Qt.Checked if item.text() in valueFields else QtCore.Qt.Unchecked,
                         QtCore.Qt.CheckStateRole)
        except:
            pass

    def layerComboChanged(self):
        self.populateFieldCombos(self.layerCombo.currentText())

    def populateList(self):
        self.chartsList.clear()
        toDelete = []
        for chartName, chart in self._charts.iteritems():
            if chart["layer"] in self.layers:
                fields = [f.name() for f in self.layers[chart["layer"]].pendingFields()]
                if chart["categoryField"] in fields:
                    item = QtGui.QListWidgetItem()
                    item.setText(chartName)
                    self.chartsList.addItem(item)
                else:
                    toDelete.append(chartName)
            else:
                toDelete.append(chartName)
        for d in toDelete:
            del self._charts[d]



    def populateLayers(self):
        self.layers = {}
        root = QgsProject.instance().layerTreeRoot()
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                for subchild in child.children():
                    if isinstance(subchild, QgsLayerTreeLayer):
                        if isinstance(subchild.layer(), QgsVectorLayer):
                            self.layers[subchild.layer().name()] = subchild.layer()
            elif isinstance(child, QgsLayerTreeLayer):
                if isinstance(child.layer(), QgsVectorLayer):
                    self.layers[child.layer().name()] = child.layer()

        self.layerCombo.addItems(self.layers.keys())

    def populateFieldCombos(self, layerName):
        fields = [f.name() for f in self.layers[layerName].pendingFields()]
        self.categoryFieldCombo.clear()
        self.categoryFieldCombo.addItems(fields)
        self.model = QtGui.QStandardItemModel(len(fields), 1)
        item = QtGui.QStandardItem("Select fields")
        if  sys.platform == 'darwin':
            self.valueFieldsCombo.setVisible(False)
            self.valueFieldsCombo.setVisible(True)
            toUse = self.valueFieldsList
            offset = 0
        else:
            self.valueFieldsCombo.setVisible(True)
            self.valueFieldsList.setVisible(False)
            toUse = self.valueFieldsCombo
            self.model.setItem(0, 0, item);
            offset = 1
        for i, f in enumerate(fields):
            item = QtGui.QStandardItem(f)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setData(QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole);
            self.model.setItem(i + offset, 0, item);
        toUse.setModel(self.model)

    def addChart(self):
        name = self.nameBox.text()
        if name.strip():
            self.nameBox.setStyleSheet("QLineEdit{background: white}")
        else:
            self.nameBox.setStyleSheet("QLineEdit{background: yellow}")
            return
        layer = self.layerCombo.currentText()
        displayMode = self.displayModeCombo.currentIndex()
        categoryField = self.categoryFieldCombo.currentText()
        operation = self.operationCombo.currentIndex()
        valueFields = []
        for i in xrange(self.model.rowCount()):
            item = self.model.item(i)
            checked = item.data(QtCore.Qt.CheckStateRole)
            if checked == QtCore.Qt.Checked:
                valueFields.append(item.text())
        if valueFields or displayMode == 2:
            self._charts[name] = {"layer": layer,
                              "categoryField": categoryField,
                              "valueFields": valueFields,
                              "displayMode": displayMode,
                              "operation": operation}
        else:
            QtGui.QMessageBox.warning(self, "Cannot create chart", "At least one value field must be selected")
            return
        self.populateList()

    def removeChart(self):
        try:
            name = self.chartsList.currentItem().text()
            del self._charts[name]
            self.populateList()
            self.nameBox.setText("")
            self.layerCombo.setCurrentIndex(0)
            self.populateFieldCombos(self.layerCombo.currentText())
        except:
            pass

    def okPressed(self):
        self.charts = self._charts
        self.close()

    def cancelPressed(self):
        self.close()


