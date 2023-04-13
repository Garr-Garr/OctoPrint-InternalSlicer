# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin

from .vector import Vector

import uuid
import tempfile
import os
import time
import struct
import shutil
import sys
import math
import copy
import flask
import serial
import serial.tools.list_ports
import binascii
import re
import collections
import json
import imp
import glob
import ctypes
import _ctypes
import platform
import subprocess
import psutil
import socket
import threading
import yaml
import logging
import logging.handlers
from collections import defaultdict
from pkg_resources import parse_version

import octoprint.plugin
import octoprint.util
import octoprint.slicing
import octoprint.settings

from octoprint.util.paths import normalize as normalize_path

from .profile import Profile


class NewSlicerPlugin(octoprint.plugin.SettingsPlugin,
                   octoprint.plugin.AssetPlugin,
		   		   octoprint.plugin.SlicerPlugin,
                   octoprint.plugin.TemplatePlugin,
				   octoprint.plugin.BlueprintPlugin,
				   octoprint.plugin.StartupPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			slicer_engine=None,
			default_profile=None,
			debug_logging=False
		)

	def __init__(self):
		# setup job tracking across threads
		self._slicing_commands = dict()
		self._slicing_commands_mutex = threading.Lock()
		self._cancelled_jobs = []
		self._cancelled_jobs_mutex = threading.Lock()

	def on_startup(self, host, port):
		self._slicer_logger = self._logger
		# setup our custom logger
		slicer_logging_handler = logging.handlers.RotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="engine"), maxBytes=2*1024*1024)
		slicer_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
		slicer_logging_handler.setLevel(logging.DEBUG)

		self._slicer_logger.addHandler(slicer_logging_handler)
		self._slicer_logger.setLevel(logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.CRITICAL)
		self._slicer_logger.propagate = False




	##~~ BlueprintPlugin API
	@octoprint.plugin.BlueprintPlugin.route("/import", methods=["POST"])
	def importSlicerProfile(self):
		import datetime
		import tempfile
		input_name = "file"
		input_upload_name = input_name + "." + self._settings.global_get(["server", "uploads", "nameSuffix"])
		input_upload_path = input_name + "." + self._settings.global_get(["server", "uploads", "pathSuffix"])
		
		if input_upload_name in flask.request.values and input_upload_path in flask.request.values:
			filename = flask.request.values[input_upload_name]
			try:
				profile_dict, imported_name, imported_description = Profile.from_slicer_ini(flask.request.values[input_upload_path])
			except Exception as e:
				return flask.make_response("Something went wrong while converting imported profile: {message}".format(e.message), 500)

		elif input_name in flask.request.files:
			temp_file = tempfile.NamedTemporaryFile("wb", delete=False)
			try:
				temp_file.close()
				upload = flask.request.files[input_name]
				upload.save(temp_file.name)
				profile_dict, imported_name, imported_description = Profile.from_slicer_ini(temp_file.name)
			except Exception as e:
				return flask.make_response("Something went wrong while converting imported profile: {message}".format(e.message), 500)
			finally:
				os.remove(temp_file)
			filename = upload.filename

		else:
			return flask.make_response("No file included", 400)
		
		name, _ = os.path.splitext(filename)

		# default values for name, display name and description
		# profile_name = _sanitize_name(name)
		profile_name = name
		profile_display_name = imported_name if imported_name is not None else name
		profile_description = imported_description if imported_description is not None else "Imported from {filename} on {date}".format(filename=filename, date=octoprint.util.get_formatted_datetime(datetime.datetime.now()))
		profile_allow_overwrite = False

		# overrides
		if "name" in flask.request.values:
			profile_name = flask.request.values["name"]
		if "displayName" in flask.request.values:
			profile_display_name = flask.request.values["displayName"]
		if "description" in flask.request.values:
			profile_description = flask.request.values["description"]
		if "allowOverwrite" in flask.request.values:
			from octoprint.server.api import valid_boolean_trues
			profile_allow_overwrite = flask.request.values["allowOverwrite"] in valid_boolean_trues

		# Save profile
		self._slicing_manager.save_profile("slicer",
										profile_name,
										profile_dict,
										allow_overwrite=profile_allow_overwrite,
										display_name=profile_display_name,
										description=profile_description)

		result = dict(
			resource=flask.url_for("api.slicingGetSlicerProfile", slicer="slicer", name=profile_name, _external=True),
			displayName=profile_display_name,
			description=profile_description
		)
		r = flask.make_response(flask.jsonify(result), 201)
		r.headers["Location"] = result["resource"]
		return r


	def on_settings_save(self, data):
		old_debug_logging = self._settings.get_boolean(["debug_logging"])
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		new_debug_logging = self._settings.get_boolean(["debug_logging"])
		if old_debug_logging != new_debug_logging:
			if new_debug_logging:
				self._slicer_logger.setLevel(logging.DEBUG)
			else:
				self._slicer_logger.setLevel(logging.CRITICAL)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/stats.min.js", "js/octoprint_slicer.min.js", "js/slic3r.js"],
			css=["css/slicer.css", "css/slic3r.css"],
			less=["less/slicer.less", "less/slic3r.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			slicer=dict(
				displayName="New Slicer",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="kennethjiang",
				repo="OctoPrint-Slicer",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/Garr-R/OctoPrint-Slicer/archive/{target_version}.zip"
			)
		)

	# Event monitor
	def on_event(self, event, payload) :

		# check if event is slicing started
		if event == octoprint.events.Events.SLICING_STARTED :

			# Set processing slice
			self.processingSlice = True

		# Otherwise check if event is slicing done, cancelled, or failed
		elif event == octoprint.events.Events.SLICING_DONE or event == octoprint.events.Events.SLICING_CANCELLED or event == octoprint.events.Events.SLICING_FAILED :

			# Clear processing slice
			self.processingSlice = False

			# Restore files
			self.restoreFiles()

	def restoreFiles(self) :

		# Check if slicer was changed
		if self.slicerChanges is not None :

			# Move original files back
			os.remove(self.slicerChanges["Slicer Profile Location"])
			shutil.move(self.slicerChanges["Slicer Profile Temporary"], self.slicerChanges["Slicer Profile Location"])

			if "Model Temporary" in self.slicerChanges :
				os.remove(self.slicerChanges["Model Location"])
				shutil.move(self.slicerChanges["Model Temporary"], self.slicerChanges["Model Location"])

			# Restore printer profile
			self._printer_profile_manager.save(self.slicerChanges["Printer Profile Content"], True)

			# Clear slicer changes
			self.slicerChanges = None

	# Upload 3D model event
	@octoprint.plugin.BlueprintPlugin.route("/upload", methods=["POST"])
	def upload(self) :
		# Check if uploading everything
		if "Slicer Profile Name" in flask.request.values and "Slicer Name" in flask.request.values and "Printer Profile Name" in flask.request.values and "Slicer Profile Content" in flask.request.values and "After Slicing Action" in flask.request.values :

			# Check if printing after slicing and a printer isn't connected
			if flask.request.values["After Slicing Action"] != "none" and self._printer.is_closed_or_error() :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Set if model was modified
			modelModified = "Model Name" in flask.request.values and "Model Location" in flask.request.values and "Model Path" in flask.request.values and "Model Center X" in flask.request.values and "Model Center Y" in flask.request.values

			# Check if slicer profile, model name, or model path contain path traversal
			if "../" in flask.request.values["Slicer Profile Name"] or (modelModified and ("../" in flask.request.values["Model Name"] or "../" in flask.request.values["Model Path"])) :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Check if model location is invalid
			if modelModified and (flask.request.values["Model Location"] != "local" and flask.request.values["Model Location"] != "sdcard") :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Set model location
			if modelModified :

				if flask.request.values["Model Location"] == "local" :
					modelLocation = self._file_manager.path_on_disk(octoprint.filemanager.destinations.FileDestinations.LOCAL, flask.request.values["Model Path"] + flask.request.values["Model Name"]).replace('\\', '/')
				elif flask.request.values["Model Location"] == "sdcard" :
					modelLocation = self._file_manager.path_on_disk(octoprint.filemanager.destinations.FileDestinations.SDCARD, flask.request.values["Model Path"] + flask.request.values["Model Name"]).replace('\\', '/')

			# Check if slicer profile, model, or printer profile doesn't exist
			if (modelModified and not os.path.isfile(modelLocation)) or not self._printer_profile_manager.exists(flask.request.values["Printer Profile Name"]) :

				# Return error
				return flask.jsonify(dict(value = "Error"))

			# Move original model to temporary location
			if modelModified :
				fd, modelTemp = tempfile.mkstemp()
				os.close(fd)
				shutil.copy(modelLocation, modelTemp)

			fd, temp = tempfile.mkstemp()
			os.close(fd)

			output = open(temp, "wb")
			for character in flask.request.values["Slicer Profile Content"] :
				output.write(chr(ord(character)))
			output.close()

			self.tempProfileName = "temp-" + str(uuid.uuid1())
			if flask.request.values["Slicer Name"] == "cura" :
				self.convertCuraToProfile(temp, self.tempProfileName, self.tempProfileName, '')
			elif flask.request.values["Slicer Name"] == "slicer" :
				self.convertSlicerToProfile(temp, '', '', '')

			# Remove temporary file
			os.remove(temp)

			# Get printer profile
			printerProfile = self._printer_profile_manager.get(flask.request.values["Printer Profile Name"])

			# Save slicer changes
			self.slicerChanges = {
				"Printer Profile Content": copy.deepcopy(printerProfile)
			}

			# Check if slicer is Cura
			if flask.request.values["Slicer Name"] == "cura" :

				# Change printer profile
				search = re.findall("extruder_amount\s*?=\s*?(\d+)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["extruder"]["count"] = int(search[0])

				search = re.findall("has_heated_bed\s*?=\s*?(\S+)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					if str(search[0]).lower() == "true" :
						printerProfile["heatedBed"] = True
					else :
						printerProfile["heatedBed"] = False

				search = re.findall("machine_width\s*?=\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["volume"]["width"] = float(search[0])

				search = re.findall("machine_height\s*?=\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["volume"]["height"] = float(search[0])

				search = re.findall("machine_depth\s*?=\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["volume"]["depth"] = float(search[0])

				search = re.findall("machine_shape\s*?=\s*?(\S+)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					if str(search[0]).lower() == "circular" :
						printerProfile["volume"]["formFactor"] = "circular"
					else :
						printerProfile["volume"]["formFactor"] = "rectangular"

				search = re.findall("nozzle_size\s*?=\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["extruder"]["nozzleDiameter"] = float(search[0])

				search = re.findall("machine_center_is_zero\s*?=\s*?(\S+)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					if str(search[0]).lower() == "true" :
						printerProfile["volume"]["formFactor"] = "circular"
						printerProfile["volume"]["origin"] = "center"
					else :
						printerProfile["volume"]["formFactor"] = "rectangular"
						printerProfile["volume"]["origin"] = "lowerleft"

				search = re.findall("extruder_offset_(x|y)(\d)\s*?=\s*?(-?\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				vectors = [Vector(0, 0)] * printerProfile["extruder"]["count"]

				for offset in search :
					if offset[0] == 'x' :
						vectors[int(offset[1]) - 1].x = float(offset[2])
					else :
						vectors[int(offset[1]) - 1].y = float(offset[2])

				index = 0
				while index < len(vectors) :
					value = (vectors[index].x, vectors[index].y)
					printerProfile["extruder"]["offsets"][index] = value
					index += 1

			# Otherwise check if slicer is Slic3r
			elif flask.request.values["Slicer Name"] == "slicer" :

				# Change printer profile
				search = re.findall("bed_size\s*?=\s*?(\d+.?\d*)\s*?,\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["volume"]["width"] = float(search[0][0])
					printerProfile["volume"]["depth"] = float(search[0][1])

				search = re.findall("nozzle_diameter\s*?=\s*?(\d+.?\d*)", flask.request.values["Slicer Profile Content"])
				if len(search) :
					printerProfile["extruder"]["nozzleDiameter"] = float(search[0])

			# Check if modifying model
			if modelModified :

				# Save model locations
				self.slicerChanges["Model Location"] = modelLocation
				self.slicerChanges["Model Temporary"] = modelTemp

				# Adjust printer profile so that its center is equal to the model's center
				printerProfile["volume"]["width"] += float(flask.request.values["Model Center X"]) * 2
				printerProfile["volume"]["depth"] += float(flask.request.values["Model Center Y"]) * 2

			# Otherwise check if using a Micro 3D printer
			elif not self._settings.get_boolean(["NotUsingAMicro3DPrinter"]) :

				# Set extruder center
				extruderCenterX = (self.bedLowMaxX + self.bedLowMinX) / 2
				extruderCenterY = (self.bedLowMaxY + self.bedLowMinY + 14.0) / 2

				# Adjust printer profile so that its center is equal to the model's center
				printerProfile["volume"]["width"] += (-(extruderCenterX - (self.bedLowMaxX + self.bedLowMinX) / 2) + self.bedLowMinX) * 2
				printerProfile["volume"]["depth"] += (extruderCenterY - (self.bedLowMaxY + self.bedLowMinY) / 2 + self.bedLowMinY) * 2

			# Apply printer profile changes
			self._printer_profile_manager.save(printerProfile, True)

			fd, destFile = tempfile.mkstemp()
			os.close(fd)
			self._slicing_manager.slice(flask.request.values["Slicer Name"],
					modelLocation, #source path
					destFile,
					self.tempProfileName,
					self)

			# Return ok
			return flask.jsonify(dict(value = "OK"))

		# Return error
		return flask.jsonify(dict(value = "Error"))

	def __call__(self, *callback_args, **callback_kwargs):
		self._slicing_manager.delete_profile("cura", self.tempProfileName)

	def convertCuraToProfile(self, input, name, displayName, description) :

		# Cura Engine plugin doesn't support solidarea_speed, perimeter_before_infill, raft_airgap_all, raft_surface_thickness, raft_surface_linewidth, plugin_config, object_center_x, and object_center_y

		# Clean up input
		fd, curaProfile = tempfile.mkstemp()
		os.close(fd)
		self.curaProfileCleanUp(input, curaProfile)

		# Import profile manager
		profileManager = imp.load_source("Profile", self._slicing_manager.get_slicer("cura")._basefolder.replace('\\', '/') + "/profile.py")

		# Create profile
		profile = octoprint.slicing.SlicingProfile("cura", name, profileManager.Profile.from_cura_ini(curaProfile), displayName, description)

		# Remove temporary file
		os.remove(curaProfile)

		# Save profile
		return self._slicing_manager.save_profile("cura", name, profile, None, True, displayName, description)

	# Cura profile cleanup
	def curaProfileCleanUp(self, input, output) :

		# Create output
		output = open(output, "wb")

		# Go through all lines in input
		for line in open(input) :

			# Fix G-code lines
			match = re.findall("^(.+)(\d+)\.gcode", line)
			if len(match) :
				line = match[0][0] + ".gcode" + match[0][1] + line[len(match[0][0]) + len(match[0][1]) + 6 :]

			# Remove comments from input
			if ';' in line and ".gcode" not in line and line[0] != '\t' :
				output.write(line[0 : line.index(';')] + '\n')
			else :
				output.write(line)

		# Close output
		output.close()

	# Slic3r profile cleanup
	#TODO: I don't think this is needed anymore, disabled for now (4/13/2023)
	def slic3rProfileCleanUp(self, input, output) :
		# Create output
		output = open(output, "wb")

		# Go through all lines in input
		for line in open(input) :
			# Remove comments from input
			if ';' in line and "_gcode" not in line and line[0] != '\t' :
				output.write(line[0 : line.index(';')] + '\n')
			else :
				output.write(line)
		# Close output
		output.close()

	def is_slicer_configured(self):
		slicer_engine = normalize_path(self._settings.get(["slicer_engine"]))
		return slicer_engine is not None and os.path.exists(slicer_engine)
	
	def get_slicer_properties(self):
		return dict(
			type="slicer",
			name="slicer",
			same_device=True,
			progress_report=False,
		)

	def get_slicer_default_profile(self):
		path = self._settings.get(["default_profile"])
		if not path:
			path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "profiles", "default.profile.ini")
		return self.get_slicer_profile(path)

	def get_slicer_profile(self, path):
		profile_dict, display_name, description = self._load_profile(path)
		properties = self.get_slicer_properties()
		return octoprint.slicing.SlicingProfile(properties["type"], "unknown", profile_dict, display_name=display_name, description=description)
	
	def save_slicer_profile(self, path, profile, allow_overwrite=True, overrides=None):
		from octoprint.util import dict_merge
		if overrides is not None:
			new_profile = dict_merge(profile.data, overrides)
		else:
			new_profile = profile.data
		self._save_profile(path, new_profile, allow_overwrite=allow_overwrite, display_name=profile.display_name, description=profile.description)

	# Slicing process
	def do_slice(self, model_path, printer_profile, machinecode_path=None, profile_path=None, position=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		if on_progress is not None:
			if on_progress_args is None:
				on_progress_args = ()
			if on_progress_kwargs is None:
				on_progress_kwargs = dict()
			on_progress_kwargs["_progress"] = 0
			on_progress(*on_progress_args, **on_progress_kwargs)

		if not profile_path:
			profile_path = self._settings.get(["default_profile"])
		if not machinecode_path:
			path, _ = os.path.splitext(model_path)
			machinecode_path = path + ".gcode"
    
		if position and isinstance(position, dict) and "x" in position and "y" in position:
			posX = position["x"]
			posY = position["y"]
		elif printer_profile["volume"]["formFactor"] == "circular" or printer_profile["volume"]["origin"] == "center" :
			posX = 0
			posY = 0
		else:
			posX = printer_profile["volume"]["width"] / 2.0
			posY = printer_profile["volume"]["depth"] / 2.0
    
		self._slicer_logger.info("### Slicing %s to %s using profile stored at %s" % (model_path, machinecode_path, profile_path))

		executable = normalize_path(self._settings.get(["slicer_engine"]))
		if not executable:
			return False, "Path to Slicer is not configured "

		#This previously worked?
		args = ['"%s"' % executable, '--export-gcode', '--center', '"%f,%f"' % (posX, posY), '--load', '"%s"' % profile_path,  '-o', '"%s"' % machinecode_path, '"%s"' % model_path]

		env = {}
    
		try:
			import subprocess
			help_process = subprocess.Popen((executable, '--help'), stdout=subprocess.PIPE)
			help_text_all = help_process.communicate()
      
			# help output includes a trace statement now on the first line. If we find it, use the second
			# line instead
			# [2022-04-22 21:44:51.396082] [0x75527010] [trace]   Initializing StaticPrintConfigs

			# Actually, I think this needs to be set to the forth line instead
			if help_text_all[0].find(b'trace') >= 0:
				help_text = help_text_all[1]
			else:
				help_text = help_text_all[0]
			self._logger.debug(help_text)

			if help_text.startswith(b'PrusaSlicer-2.3') or help_text.startswith(b'PrusaSlicer-2.4'):
				args = ['"%s"' % executable, '-g --load', '"%s"' % profile_path, '--center', '"%f,%f"' % (posX, posY), '-o', '"%s"' % machinecode_path, '"%s"' % model_path]
				env['SLICER_LOGLEVEL'] = "9"
				self._logger.info("Running Prusa Slicer >= 2.3")
			elif help_text.startswith(b'PrusaSlicer-2'):
				args = ['"%s"' % executable, '--slice --load', '"%s"' % profile_path, '--center', '"%f,%f"' % (posX, posY), '-o', '"%s"' % machinecode_path, '"%s"' % model_path]
				self._logger.info("Running Prusa Slicer >= 2")
		except e:
			self._logger.info("Error during Prusa Slicer detection:" + str(e))

		import sarge
		working_dir, _ = os.path.split(executable)
		command = " ".join(args)
		self._logger.info("Running %r in %s" % (command, working_dir))
		
		try:
			if parse_version(sarge.__version__) >= parse_version('0.1.5'): # Because in version 0.1.5 the name was changed in sarge.
				async_kwarg = 'async_'
			else:
				async_kwarg = 'async'
			p = sarge.run(command, cwd=working_dir, stdout=sarge.Capture(buffer_size=1), stderr=sarge.Capture(buffer_size=1), env=env, **{async_kwarg: True})
			p.wait_events()
			last_error=""
			
			try:
				with self._slicing_commands_mutex:
					self._slicing_commands[machinecode_path] = p.commands[0]

				stdout_buffer = b""
				stderr_buffer = b""
				total_layers = 1
				matched_lines = 0
				
				while p.returncode is None:
					p.commands[0].poll()
					# Can't use readline because it removes newlines and we can't tell if we have gotten a full line.
					stdout_buffer += p.stdout.read(block=False)
					stderr_buffer += p.stderr.read(block=False)

					stdout_lines = stdout_buffer.split(b'\n')
					stdout_buffer = stdout_lines[-1]
					stdout_lines = stdout_lines[0:-1]
					for stdout_line in stdout_lines:
						self._slicer_logger.debug("stdout: " + str(stdout_line))
						print(stdout_line.decode('utf-8'))
						m = re.search(r"\[trace\].*layer ([0-9]+)", stdout_line.decode('utf-8'))
						if m:
							matched_lines += 1
							current_layer = int(m.group(1))
							total_layers = max(total_layers, current_layer)
							if on_progress is not None:
								print("sending progress" + str(matched_lines / total_layers / 4))
								on_progress_kwargs["_progress"] = matched_lines / total_layers / 4
								on_progress(*on_progress_args, **on_progress_kwargs)

					stderr_lines = stderr_buffer.split(b'\n')
					stderr_buffer = stderr_lines[-1]
					stderr_lines = stderr_lines[0:-1]
					for stderr_line in stderr_lines:
						self._slicer_logger.debug("stderr: " + str(stderr_line))
						if len(stderr_line.strip()) > 0:
							last_error = stderr_line.strip()
			finally:
				if stdout_buffer:
					stdout_lines = stdout_buffer.split(b'\n')
					for stdout_line in stdout_lines:
						self._slicer_logger.debug("stdout: " + str(stdout_line))

				if stderr_buffer:
					stderr_lines = stderr_buffer.split(b'\n')
					for stderr_line in stderr_lines:
						self._slicer_logger.debug("stderr: " + str(stderr_line))
						if len(stderr_line.strip()) > 0:
							last_error = stderr_line.strip()
				p.close()

				with self._cancelled_jobs_mutex:
					if machinecode_path in self._cancelled_jobs:
						self._slicer_logger.info("### Cancelled")
						raise octoprint.slicing.SlicingCancelled()

				self._slicer_logger.info("### Finished, returncode %d" % p.returncode)
				
				#TODO: get analysis from gcode
				#if p.returncode == 0:
				#	analysis = get_analysis_from_gcode(machinecode_path)
				#	self._slic3r_logger.info("Analysis found in gcode: %s" % str(analysis))
				#	if analysis:
				#		analysis = {'analysis': analysis}
				#	return True, analysis
				#else:
				#	self._logger.warn("Could not slice via Slic3r, got return code %r" % p.returncode)
				#	self._logger.warn("Error was: %s" % last_error)
				#	return False, "Got returncode %r: %s" % (p.returncode, last_error)

		except octoprint.slicing.SlicingCancelled as e:
			raise e
		except:
			self._logger.exception("Could not slice via Slicer, got an unknown error")
			return False, "Unknown error, please consult the log file"

		finally:
			with self._cancelled_jobs_mutex:
				if machinecode_path in self._cancelled_jobs:
					self._cancelled_jobs.remove(machinecode_path)
			with self._slicing_commands_mutex:
				if machinecode_path in self._slicing_commands:
					del self._slicing_commands[machinecode_path]
			self._slicer_logger.info("-" * 40)

	def cancel_slicing(self, machinecode_path):
		with self._slicing_commands_mutex:
			if machinecode_path in self._slicing_commands:
				with self._cancelled_jobs_mutex:
					self._cancelled_jobs.add(machinecode_path)
				self._slicing_commands[machinecode_path].terminate()
				self._logger.info("Cancelled slicing of %s" % machinecode_path)

	def _load_profile(self, path):
		profile, display_name, description = Profile.from_slicer_ini(path)
		return profile, display_name, description

	def _save_profile(self, path, profile, allow_overwrite=True, display_name=None, description=None):
		if not allow_overwrite and os.path.exists(path):
			raise IOError("Cannot overwrite {path}".format(path=path))
		Profile.to_slicer_ini(profile, path, display_name=display_name, description=description)

	#TODO: Re-enable this later
	def _sanitize_name(name):
		if name is None:
			return None
		
		if "/" in name or "\\" in name:
			raise ValueError("Name must not contain slashes")
		
		import string
		valid_chars = "-_.() {ascii}{digits}".format(ascii=string.ascii_letters, digits=string.digits)
		sanitized_name = ''.join(c for c in name if c in valid_chars)
		sanitized_name = sanitized_name.replace(" ", "_")
		return sanitized_name.lower()


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Slicer"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = NewSlicerPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
