import os
import matplotlib.patches as mpatches
import numpy as np
import pkg_resources

from PyQt5 import  QtWidgets, QtCore, uic
from PyQt5.QtCore import QSettings, QThread
from PyQt5.QtWidgets import QMenu
from PyQt5.Qt import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, \
    NavigationToolbar2QT as NavigationToolbar

from xas.xasproject import XASDataSet

from qtpy.QtWidgets import (
    QApplication,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QMainWindow,
    QWidget,
)
from bluesky_widgets.models.search import Search
from bluesky_widgets.qt.search import QtSearch
from bluesky_live.event import Event


from sys import platform
import datetime
import os
import time
from pathlib import Path
import pandas as pd


from isstools.dialogs.BasicDialogs import message_box




if platform == 'darwin':
    ui_path = pkg_resources.resource_filename('xview', 'ui/ui_xview_databroker.ui')
else:
    ui_path = pkg_resources.resource_filename('xview', 'ui/ui_xview_databroker.ui')


class UIXviewDatabroker(*uic.loadUiType(ui_path)):
    def __init__(self, db=None, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.db = db
        self.range = 30
        self.parent = parent
        self.uid_list = []
        self.mode = 'Search'
        self.counter=0
        #self.tableWidget_data.selectionChanged.connect(self.show_start_doc)
        self.push_show_latest.clicked.connect(self.show_latest)
        self.push_show_later.clicked.connect(self.show_later)
        self.push_show_earlier.clicked.connect(self.show_earlier)
        self.push_goto_folder.clicked.connect(self.goto_folder)

        self.push_search.clicked.connect(self.search_db)

        self.tableWidget_data.setColumnCount(3)
        self.tableWidget_data.setHorizontalHeaderLabels(['Date', 'UID', 'Filename'])
        #self.tableWidget_data.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.tableWidget_data.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget_data.selectionModel().selectionChanged.connect(self.show_start_doc)


    def show_latest(self):
        self.counter = 0
        self.show_record_list()

    def show_record_list(self):
        self.list_uids.clear()
        self.uids = []
        self.entries = []

        print(f'Counter {self.counter}')
        for indx in range(self.range):
            record = -(indx+1)-self.range * self.counter
            document = self.db[record]
            uid = document.start['uid']
            timestamp = datetime.datetime.fromtimestamp(document.start['time'])
            try:
                filename = os.path.basename(document.start['interp_filename'])
            except:
                filename = 'tuning scan'
            time = timestamp.strftime('%m/%d/%y %H:%M:%S')
            entry = f'{time}...{uid[0:6]}...{filename}'
            self.entries.append(entry)
            self.uids.append(uid)

        self.list_uids.addItems(self.entries)


    def search_db(self):
        self.parent.statusBar().showMessage('Search in progress...')
        self.uid_list  = list(self.db.v2.search({'element': self.lineEdit_element.text()}))
        self.parent.statusBar().showMessage('Search complete')
        self.get_records()

    def get_records(self):
        timestamps = []
        filenames = []
        self.parent.statusBar().showMessage('Getting records...')
        uids =self.uid_list[self.counter*100:((self.counter+1)*100)]
        print(uids[0:3])
        for uid in uids:
            document = self.db[uid]
            timestamps.append(datetime.datetime.fromtimestamp(document.start['time']))
            try:
                filenames.append(document.start['interp_filename'])
            except:
                filenames.append('empty')
        self.parent.statusBar().showMessage('Records received')

        self.record = pd.DataFrame(list(zip(timestamps, uids, filenames)),columns = ['Timestamp','Uid','Filename'])

        self.populate_table()

    def populate_table(self):
        for jj in range(self.tableWidget_data.rowCount()):
            self.tableWidget_data.removeRow(0)

        ptable_row_index = 0
        for jj in range(len(self.record)):
            self.tableWidget_data.insertRow(ptable_row_index)
            self.tableWidget_data.setItem(ptable_row_index, 0,
                                              QtWidgets.QTableWidgetItem(
                                                  str(self.record['Timestamp'][jj]).split('.')[0]))
            self.tableWidget_data.setItem(ptable_row_index, 1,
                                              QtWidgets.QTableWidgetItem(
                                                  self.record['Uid'][jj][:6]))
            self.tableWidget_data.setItem(ptable_row_index, 2,
                                              QtWidgets.QTableWidgetItem(
                                                  os.path.basename(self.record['Filename'][jj])))

            ptable_row_index += 1

        for jj in range(3):
            self.tableWidget_data.resizeColumnToContents(jj)

    def show_later(self):
        print(f'Counter {self.counter}')
        self.counter += 1
        try:
            self.get_records()
        except:
            message_box('Message','End of record reached')

    def show_earlier(self):
        print(f'Counter {self.counter}')
        if self.counter > 0:
            self.counter -= 1
            self.get_records()
        else:
            message_box('Message','Start of record reached')

    def show_start_doc(self):
        if self.tableWidget_data.selectedIndexes():
            indx = self.tableWidget_data.selectedIndexes()[0].row()
            uid = self.uid_list[indx+100*self.counter]
            start_doc = self.db[uid].start
            self.textEdit_start_doc.setText(str(start_doc))


    def goto_folder(self):
        if self.tableWidget_data.selectedIndexes():
            indx = self.tableWidget_data.selectedIndexes()[0].row()
            uid = self.uid_list[indx+100*self.counter]
            document = self.db[uid]
            folder = os.path.dirname(document.start['interp_filename'])
            print(folder)
            self.parent.widget_data.working_folder = folder
            self.parent.widget_data.set_working_folder()
            self.parent.tabWidget.setCurrentWidget(self.parent.tabWidget.widget(0))
            filename = os.path.basename(document.start['interp_filename']).split('.')[0]
            print(f'Filename {filename}')
            self.parent.widget_data.set_selection(filename)



#######

class SearchAndOpen(Search):
    """
    Extend Search model with a signal for when a result is "opened".

    In your application, you might have multiple such signals associated with
    different buttons.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events.add(open=Event)

    @property
    def selected_runs(self):
        # This property would be useful in general and should be added to the
        # Search itself in bluesky-widgets.
        return [self.results[uid] for uid in self.selected_uids]

class QtSearchListWithButton(QWidget):
    """
    A view for SearchAndOpen.

    Combines the QtSearches widget with a button.
    """

    def __init__(self, model: SearchAndOpen, parent, add_open_button=True, add_to_proj_button=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.db = self.model.current_catalog
        self.parent = parent
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QtSearch(model))

        if add_open_button:
            self.add_open_button()

        if add_to_proj_button:
            self.add_to_proj_button()


    def add_open_button(self):
        # Add a button that does something with the currently-selected Runs
        # when you click it.
        self._open_button = QPushButton("Open")
        self.layout.addWidget(self._open_button)

        # Register a callback (slot) for the button qt click signal.
        self._open_button.clicked.connect(self._on_click_open_button)


    def _on_click_open_button(self):
        """
        Receive the Qt signal and emit a bluesky-widgets one.

        Include a list of BlueskyRuns corresponding to the current selection.
        """
        # self.model.events.open(selected_runs=self.model.selected_runs)
        run_list = self.model.selected_runs


        if len(run_list) == 1:
            try:
                run_start = run_list[0].metadata['start']
                folder = os.path.dirname(run_start['interp_filename'])
                print(folder)
                self.parent.widget_data.working_folder = folder
                self.parent.widget_data.set_working_folder()
                self.parent.tabWidget.setCurrentWidget(self.parent.tabWidget.widget(0))
                filename = os.path.basename(run_start['interp_filename']).split('.')[0]
                print(f'Filename {filename}')
                self.parent.widget_data.set_selection(filename)
            except KeyError:
                print('This DB entry is not an experiment')
        else:
            print('Multiple scan selection is not supported yet')

    def add_to_proj_button(self):
        self._proj_button = QPushButton("Add to XAS project")
        self.layout.addWidget(self._proj_button)

        # Register a callback (slot) for the button qt click signal.
        self._proj_button.clicked.connect(self._on_click_proj_button)


    def _on_click_proj_button(self):
        # self.model.events.open(selected_runs=self.model.selected_runs)
        run_list = self.model.selected_runs

        x_list, data_list, label_list = [], [], []
        for run in run_list:
            uid = run.metadata['start']['uid']
            energy, mu, name = self.db.read_spectrum(uid)
            ds = XASDataSet(name=(f'{name} [db_proc]'), md={}, energy=energy, mu=mu, filename='',
                            datatype='experiment')
            self.parent.project.append(ds)
            # x_list.append(x)
            # data_list.append(data)
            # label_list.append(label)

        # self.parent.widget_mcr.add_references_to_specific_set(x_list, data_list, label_list)




headings = (
    "Unique ID",
    "Transient Scan ID",
    "Plan Name",
    "Sample Name",
    "Sample Comment",
    "Scanning",
    "Start Time",
    "Duration",
    "Exit Status",
)

def extract_results_row_from_run(run):
    """
    Given a BlueskyRun, format a row for the table of search results.
    """
    from datetime import datetime

    metadata = run.describe()["metadata"]
    start = metadata["start"]
    stop = metadata["stop"]
    start_time = datetime.fromtimestamp(start["time"])
    if stop is None:
        str_duration = "-"
    else:
        duration = datetime.fromtimestamp(stop["time"]) - start_time
        str_duration = str(duration)
        str_duration = str_duration[: str_duration.index(".")]
    return (
        start["uid"][:8],
        start.get("scan_id", "-"),
        start.get("plan_name", "-"),
        start.get("name", "-"),
        start.get("comment", "-"),
        str(start.get("motors", "-")),
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        str_duration,
        "-" if stop is None else stop["exit_status"],
    )

columns = (headings, extract_results_row_from_run)


headings_proc = (
    "Unique ID",
    "Sample name",
    "Compound",
    "Element",
    "Edge",
    "E0",
    "Start Time",
)

def extract_results_row_from_run_proc(run):
    """
    Given a BlueskyRun, format a row for the table of search results.
    """
    from datetime import datetime

    metadata = run.describe()["metadata"]
    start = metadata["start"]
    # stop = metadata["stop"]
    start_time = datetime.fromtimestamp(start["time"])
    # if stop is None:
    #     str_duration = "-"
    # else:
    #     duration = datetime.fromtimestamp(stop["time"]) - start_time
    #     str_duration = str(duration)
    #     str_duration = str_duration[: str_duration.index(".")]

    return (
        start["uid"][:8],
        start.get("Sample_name", "-"),
        start.get("compound", "-"),
        start.get("Element", "-"),
        start.get("Edge", "-"),
        start.get("E0", "-"),
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
    )

columns_proc = (headings_proc, extract_results_row_from_run_proc)

columns_dict = {'columns' : columns,
                'columns_proc' : columns_proc}

CATALOG_NAME = "iss"
import databroker

catalog = databroker.catalog[CATALOG_NAME]

# search_model = SearchAndOpen(catalog, columns=columns)

def get_SearchAndOpen_widget(parent, catalog=catalog, columns='columns', add_open_button=True, add_mcr_button=False):
    search_model = SearchAndOpen(catalog, columns=columns_dict[columns])
    # search_model.events.open.connect(
    #     lambda event: print(f"Opening {event.selected_runs}")
    # )
    search_view = QtSearchListWithButton(search_model, parent, add_open_button=add_open_button, add_to_proj_button=add_mcr_button)
    return search_view



    #     self.push_refresh_folder.clicked.connect(self.get_file_list)
    #     self.push_plot_data.clicked.connect(self.plot_xas_data)
    #     self.comboBox_sort_files_by.addItems(['Time','Name'])
    #     self.comboBox_sort_files_by.currentIndexChanged.connect((self.get_file_list))
    #
    #     self.comboBox_data_numerator.currentIndexChanged.connect(self.update_current_numerator)
    #     self.comboBox_data_denominator.currentIndexChanged.connect(self.update_current_denominator)
    #
    #     self.list_data.itemSelectionChanged.connect(self.select_files_to_plot)
    #     self.push_add_to_project.clicked.connect(self.add_data_to_project)
    #     self.list_data.setContextMenuPolicy(Qt.CustomContextMenu)
    #     self.list_data.customContextMenuRequested.connect(self.xas_data_context_menu)
    #
    #     self.list_data.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    #     self.addCanvas()
    #     self.keys = []
    #     self.last_keys = []
    #     self.current_plot_in = ''
    #     self.binned_data = []
    #     self.last_numerator= ''
    #     self.last_denominator = ''
    #     # Persistent settings
    #     self.settings = QSettings('ISS Beamline', 'Xview')
    #     self.working_folder = self.settings.value('working_folder', defaultValue='/GPFS/xf08id/User Data', type=str)
    #
    #     if self.working_folder != '/GPFS/xf08id/User Data':
    #         self.label_working_folder.setText(self.working_folder)
    #         self.label_working_folder.setToolTip(self.working_folder)
    #         self.get_file_list()
    #
    # def xas_data_context_menu(self,QPos):
    #     menu = QMenu()
    #     plot_action = menu.addAction("&Plot")
    #     add_to_project_action = menu.addAction("&Add to project")
    #     parentPosition = self.list_data.mapToGlobal(QtCore.QPoint(0, 0))
    #     menu.move(parentPosition+QPos)
    #     action = menu.exec_()
    #     if action == plot_action:
    #         self.plot_xas_data()
    #     elif action == add_to_project_action:
    #         self.add_data_to_project()
    #
    # def addCanvas(self):
    #     self.figure_data = Figure()
    #     #self.figure_data.set_facecolor(color='#E2E2E2')
    #     self.figure_data.ax = self.figure_data.add_subplot(111)
    #     self.canvas = FigureCanvas(self.figure_data)
    #     self.toolbar = NavigationToolbar(self.canvas, self)
    #     self.toolbar.resize(1, 10)
    #     self.layout_plot_data.addWidget(self.toolbar)
    #     self.layout_plot_data.addWidget(self.canvas)
    #     self.figure_data.tight_layout()
    #     self.canvas.draw()
    #
    # def select_working_folder(self):
    #     self.working_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select a folder", self.working_folder,
    #                                                                     QtWidgets.QFileDialog.ShowDirsOnly)
    #     if self.working_folder:
    #         self.settings.setValue('working_folder', self.working_folder)
    #         if len(self.working_folder) > 50:
    #             self.label_working_folder.setText(self.working_folder[1:20] + '...' + self.working_folder[-30:])
    #         else:
    #             self.label_working_folder.setText(self.working_folder)
    #         self.get_file_list()
    #
    # def get_file_list(self):
    #     if self.working_folder:
    #         self.list_data.clear()
    #
    #         files_bin = [f for f in os.listdir(self.working_folder) if f.endswith('.dat')]
    #
    #         if self.comboBox_sort_files_by.currentText() == 'Name':
    #             files_bin.sort()
    #         elif self.comboBox_sort_files_by.currentText() == 'Time':
    #             files_bin.sort(key=lambda x: os.path.getmtime('{}/{}'.format(self.working_folder, x)))
    #
    #             files_bin.reverse()
    #         self.list_data.addItems(files_bin)
    #
    # def select_files_to_plot(self):
    #     df, header = load_binned_df_from_file(f'{self.working_folder}/{self.list_data.currentItem().text()}')
    #     keys = df.keys()
    #     refined_keys = []
    #     for key in keys:
    #         if not (('timestamp' in key) or ('energy' in key)):
    #             refined_keys.append(key)
    #     self.keys = refined_keys
    #     if self.keys != self.last_keys:
    #         self.last_keys = self.keys
    #         self.comboBox_data_numerator.clear()
    #         self.comboBox_data_denominator.clear()
    #         self.comboBox_data_numerator.insertItems(0, self.keys)
    #         self.comboBox_data_denominator.insertItems(0, self.keys)
    #         if self.last_numerator!= '' and self.last_numerator in self.keys:
    #             indx = self.comboBox_data_numerator.findText(self.last_numerator)
    #             self.comboBox_data_numerator.setCurrentIndex(indx)
    #         if self.last_denominator!= '' and self.last_denominator in self.keys:
    #             indx = self.comboBox_data_denominator.findText(self.last_denominator)
    #             self.comboBox_data_denominator.setCurrentIndex(indx)
    #
    # def update_current_numerator(self):
    #     self.last_numerator= self.comboBox_data_numerator.currentText()
    #     print(f'Chanhin last num to {self.last_numerator}')
    #
    # def update_current_denominator(self):
    #     self.last_denominator= self.comboBox_data_denominator.currentText()
    #     print(f'I am there {self.last_denominator}')
    #
    # def plot_xas_data(self):
    #     selected_items = (self.list_data.selectedItems())
    #     update_figure([self.figure_data.ax], self.toolbar, self.canvas)
    #     if self.comboBox_data_numerator.currentText() == -1 or self.comboBox_data_denominator.currentText() == -1:
    #         message_box('Warning','Please select numerator and denominator')
    #         return
    #
    #     self.last_numerator = self.comboBox_data_numerator.currentText()
    #     self.last_denominator = self.comboBox_data_denominator.currentText()
    #
    #     energy_key = 'energy'
    #
    #     handles = []
    #
    #     for i in selected_items:
    #         path = f'{self.working_folder}/{i.text()}'
    #         print(path)
    #         df, header = load_binned_df_from_file(path)
    #         numer = np.array(df[self.comboBox_data_numerator.currentText()])
    #         denom = np.array(df[self.comboBox_data_denominator.currentText()])
    #         if self.checkBox_ratio.checkState():
    #             y_label = (f'{self.comboBox_data_numerator.currentText()} / '
    #                        f'{self.comboBox_data_denominator.currentText()}')
    #             spectrum = numer/denom
    #         else:
    #             y_label = (f'{self.comboBox_data_numerator.currentText()}')
    #             spectrum = numer
    #         if self.checkBox_log_bin.checkState():
    #             spectrum = np.log(spectrum)
    #             y_label = f'ln ({y_label})'
    #         if self.checkBox_inv_bin.checkState():
    #             spectrum = -spectrum
    #             y_label = f'- {y_label}'
    #
    #         self.figure_data.ax.plot(df[energy_key], spectrum)
    #         self.parent.set_figure(self.figure_data.ax,self.canvas,label_x='Energy (eV)', label_y=y_label)
    #
    #         self.figure_data.ax.set_xlabel('Energy (eV)')
    #         self.figure_data.ax.set_ylabel(y_label)
    #         last_trace = self.figure_data.ax.get_lines()[len(self.figure_data.ax.get_lines()) - 1]
    #         patch = mpatches.Patch(color=last_trace.get_color(), label=i.text())
    #         handles.append(patch)
    #
    #     self.figure_data.ax.legend(handles=handles)
    #     self.figure_data.tight_layout()
    #     self.canvas.draw_idle()
    #
    #
    # def add_data_to_project(self):
    #     if self.comboBox_data_numerator.currentText() != -1 and self.comboBox_data_denominator.currentText() != -1:
    #         for item in self.list_data.selectedItems():
    #             filepath = str(Path(self.working_folder) / Path(item.text()))
    #
    #             name = Path(filepath).resolve().stem
    #             df, header = load_binned_df_from_file(filepath)
    #             uid = header[header.find('UID:')+5:header.find('\n', header.find('UID:'))]
    #
    #
    #             try:
    #                 md = self.db[uid]['start']
    #             except:
    #                 print('Metadata not found')
    #                 md={}
    #
    #             df = df.sort_values('energy')
    #             num_key = self.comboBox_data_numerator.currentText()
    #             den_key = self.comboBox_data_denominator.currentText()
    #             mu = df[num_key] / df[den_key]
    #
    #             if self.checkBox_log_bin.checkState():
    #                 mu = np.log(mu)
    #             if self.checkBox_inv_bin.checkState():
    #                 mu = -mu
    #             mu=np.array(mu)
    #
    #             ds = XASDataSet(name=name,md=md,energy=df['energy'],mu=mu, filename=filepath,datatype='experiment')
    #             ds.header = header
    #             self.parent.project.append(ds)
    #             self.parent.statusBar().showMessage('Scans added to the project successfully')
    #     else:
    #         message_box('Error', 'Select numerator and denominator columns')
    #
    #
    #
    #
