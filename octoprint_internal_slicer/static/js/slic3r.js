$(function() {
    function Slic3rViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        self.slicingViewModel = parameters[2];
        
        self.internal_slicer_command_response_popup = $("#internal_slicer_command_response_popup");
        self.slicerCommandResponse = ko.observable("");
    
        self.isDefaultSlicer = ko.observable();
        self.currentDiv = ko.observable("");

		self.step = ko.observable(1);
		self.wizardComplete = ko.observable(false);
        self.slicerInstalled = ko.observable(false);
        self.hasProfiles = ko.observable(false);
        self.installedVersion = ko.observable("");

        self.pathBroken = ko.observable();
        self.pathOk = ko.observable(false);
        self.pathText = ko.observable();
        self.pathHelpVisible = ko.pureComputed(function() {
            return self.pathBroken() || self.pathOk();
        });

        self.fileName = ko.observable();
        self.enableSlicingDialog = ko.observable();

        self.placeholderName = ko.observable();
        self.placeholderDisplayName = ko.observable();
        self.placeholderDescription = ko.observable();

        self.profileName = ko.observable();
        self.profileDisplayName = ko.observable();
        self.profileDescription = ko.observable();
        self.profileAllowOverwrite = ko.observable(true);
        
        self.uploadElement = $("#settings-internal_slicer-import");
        self.uploadButton = $("#settings-internal_slicer-import-start");
        self.uploadData = null;
        self.uploadButton.on("click", function() {
			// Trigger the submit handler which will set the latest form data
            if (self.uploadData) {
                self.uploadData.submit();
            }
        });
        // wizard testing
        self.nextStep = function() {
			if (self.step() < 3) {
				self.step(self.step() + 1);
			}
		};
		
		self.prevStep = function() {
			if (self.step() > 1) {
				self.step(self.step() - 1);
			}
		};

		self.skipWizard = function() {
			showConfirmationDialog({
				title: gettext("Skip Setup Wizard"),
				message: gettext("Are you sure you want to skip the setup wizard? You can always configure the slicer later through OctoPrint's settings."),
				proceed: gettext("Skip"),
				onproceed: function() {
					self.settingsViewModel.saveData({
						plugins: {
							internal_slicer: {
								wizard_version: 1
							}
						}
					});
					self.wizardComplete(true);
				}
			});
		};
		
		self.finishWizard = function() {
			self.settingsViewModel.saveData({
				plugins: {
					internal_slicer: {
						wizard_version: 1
					}
				}
			});
			self.wizardComplete(true);
		};

        self.resetWizard = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "test_reset_wizard")
                .done(function(response) {
                    new PNotify({
                        title: "Wizard Reset",
                        text: "Setup wizard has been reset. Please refresh the page.",
                        type: "success"
                    });
                    self.slicerCommandResponse("Wizard has been reset. Please refresh the page to start the wizard again.");
                })
                .fail(function(xhr, status, error) {
                    new PNotify({
                        title: "Error",
                        text: "Failed to reset wizard: " + error,
                        type: "error"
                    });
                    self.slicerCommandResponse("Failed to reset wizard: " + error);
                });
        };

        self.pluginIncludesNewVersion = ko.computed(function() {
            return self.slicerInstalled() && 
                   self.installedVersion() !== "2.6.1"; // Hardcoded version for this plugin release
        });

        // Check if slicer is installed and executable
        self.checkSlicerInstallation = function() {
            var enginePath = self.settings.plugins.internal_slicer.slicer_engine();
            if (enginePath) {
                OctoPrint.util.testExecutable(enginePath)
                    .done(function(response) {
                        self.slicerInstalled(response.result);
                    })
                    .fail(function() {
                        self.slicerInstalled(false);
                    });
            } else {
                self.slicerInstalled(false);
            }
        };

        // Check if any profiles exist
        self.checkProfiles = function() {
            // Use the existing profiles.items observable array instead of making a new API call
            var hasExistingProfiles = self.profiles.items().length > 0;
            self.hasProfiles(hasExistingProfiles);
        };
        
        // Settings menu profile list
        self.profiles = new ItemListHelper(
            "plugin_internal_slicer_profiles",
            {
                "id": function(a, b) {
                    if (a["key"].toLocaleLowerCase() < b["key"].toLocaleLowerCase()) return -1;
                    if (a["key"].toLocaleLowerCase() > b["key"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "name": function(a, b) {
                    // sorts ascending
                    var aName = a.name();
                    if (aName === undefined) {
                        aName = "";
                    }
                    var bName = b.name();
                    if (bName === undefined) {
                        bName = "";
                    }

                    if (aName.toLocaleLowerCase() < bName.toLocaleLowerCase()) return -1;
                    if (aName.toLocaleLowerCase() > bName.toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "id",
            [],
            [],
            5
        );

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };

        self.clearUpload = function() {
            self.fileName(undefined);
            self.placeholderName(undefined);
            self.placeholderDisplayName(undefined);
            self.placeholderDescription(undefined);
            self.profileName(undefined);
            self.profileDisplayName(undefined);
            self.profileDescription(undefined);
            self.profileAllowOverwrite(true);
            self.uploadData = null;
        };

        // Initialize file upload on both settings and wizard inputs
        self.initFileUpload = function() {
            $("#settings-internal_slicer-import, #wizard-slicer-import").fileupload({
                dataType: "json",
                maxNumberOfFiles: 1,
                autoUpload: false,
                headers: OctoPrint.getRequestHeaders(),
                add: function(e, data) {
                    if (data.files.length == 0) {
                        return false;
                    }
                    
                    self.fileName(data.files[0].name);
                    
                    // Read the file to extract settings
                    var reader = new FileReader();
                    reader.onload = function(e) {
                        var content = e.target.result;
                        var printSettingsId = "";
        
                        // Extract print_settings_id from the config file
                        var match = content.match(/print_settings_id\s*=\s*(.+)/);
                        if (match && match[1]) {
                            printSettingsId = match[1].trim();
                        }
                    
                        // If no print_settings_id found, use filename without extension
                        if (!printSettingsId) {
                            var name = self.fileName().substr(0, self.fileName().lastIndexOf("."));
                            printSettingsId = self._sanitize(name).toLowerCase();
                        }
                    
                        // Update the form fields with extracted data
                        self.profileName(printSettingsId);
                        self.profileDisplayName(printSettingsId);
                        self.placeholderName(printSettingsId);
                        self.placeholderDisplayName(printSettingsId);
                        self.placeholderDescription("Imported from " + self.fileName() + " on " + formatDate(new Date().getTime() / 1000));
                        self.profileDescription(self.placeholderDescription());
                    };
                    reader.readAsText(data.files[0]);
                    
                    self.uploadData = data;
                },
                submit: function(e, data) {
                    data.formData = {
                        name: self.profileName(),
                        displayName: self.profileDisplayName(),
                        description: self.profileDescription(),
                        allowOverwrite: self.profileAllowOverwrite()
                    };
                },
                done: function(e, data) {
                    self.clearUpload();
                    $("#settings_plugin_internal_slicer_import, #wizard_slicer_import").modal("hide");
                    self.requestData();
                    self.slicingViewModel.requestData();
                    if (self.step && self.step() === 3) {
                        new PNotify({
                            title: "Profile Imported",
                            text: "Profile was successfully imported. You can now click 'Finish' to complete the setup.",
                            type: "success"
                        });
                    }
                }
            });
        };

        // Initialize upload handlers after binding
        self.onAfterBinding = function() {
            self.initFileUpload();
            
            // Request profile data first
            self.requestData();
        
            // Only run checks if we're in the wizard
            if ($("#wizard_plugin_internal_slicer").length) {
                self.checkSlicerInstallation();
                // Initialize version information from settings
                self.installedVersion(self.settings.plugins.internal_slicer.installed_prusaslicer_version());
                // Check profiles after a small delay to ensure data is loaded
                setTimeout(function() {
                    self.checkProfiles();
                }, 500);
            }
        };
        
        // Make sure both Confirm buttons trigger submit
        $("button[id$='slicer-import-start']").click(function() {
            if (self.uploadData) {
                self.uploadData.submit();
            }
        });

        self.removeProfile = function(data) {
            if (!data.resource) {
                return;
            }

            self.profiles.removeItem(function(item) {
                return (item.key == data.key);
            });

            $.ajax({
                url: data.resource(),
                type: "DELETE",
                success: function() {
                    self.requestData();
                    self.slicingViewModel.requestData();
                }
            });
        };

        self.makeProfileDefault = function(data) {
            if (!data.resource) {
                return;
            }

            _.each(self.profiles.items(), function(item) {
                item.isdefault(false);
            });
            var item = self.profiles.getItem(function(item) {
                return item.key == data.key;
            });
            if (item !== undefined) {
                item.isdefault(true);
            }

            $.ajax({
                url: data.resource(),
                type: "PATCH",
                dataType: "json",
                data: JSON.stringify({default: true}),
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    self.requestData();
                }
            });
        };
        
        self.showSlicerCommandResponse = function(input) {
            if (input === "hide") {
                self.internal_slicer_command_response_popup.modal("hide");
            } else {
                self.internal_slicer_command_response_popup.modal({
                    keyboard: false,
                    backdrop: "static",
                    show: true
                });
                self.slicerCommandResponse(""); // Clear previous content
                self.internal_slicer_command_response_popup.modal("show");
                // Initialize scrolling after modal is shown
                // var textarea = document.getElementById("slicerCommandResponseText");
                // if (textarea) {
                //     setTimeout(function() {
                //         textarea.scrollTop = textarea.scrollHeight;
                //     }, 100);
                // }
            }
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "internal_slicer") {
                return;
            }
            if (data.type === "download_complete") {
                self.installedVersion(data.installed_version);
                // Refresh status checks
                self.checkSlicerInstallation();
                
                // Show appropriate notification
                if (data.was_update) {
                    new PNotify({
                        title: "PrusaSlicer Updated",
                        text: "Successfully updated to version " + data.installed_version,
                        type: "success"
                    });
                } else {
                    new PNotify({
                        title: "PrusaSlicer Installed",
                        text: "Successfully installed version " + data.installed_version,
                        type: "success"
                    });
                }
            } else if (data.slicerCommandResponse !== undefined) {
                // Update the text
                self.slicerCommandResponse(self.slicerCommandResponse() + data.slicerCommandResponse.toString());
                    
                // Simple auto-scroll
                var textarea = document.getElementById("slicerCommandResponseText");
                if (textarea) {
                    textarea.scrollTop = textarea.scrollHeight;
                }
            }
        };
        
        self.downloadSlicer = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "download_prusaslicer_script")
                .done(function(response) {
                    // Wait a bit for the installation to complete
                    // might not be long enough
                    setTimeout(function() {
                        self.checkSlicerInstallation();
                    }, 2000);
                });
        };

        self.installCPULimit = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "installCPULimit")
                .done(function(response) {
                        //console.log(response);
            });
        };

        self.extractSlicer = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "extract_prusaslicer_script")
                .done(function(response) {
                        //console.log(response);
            });
        };

        self.cancel_slice = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "cancel_slice")
                .done(function(response) {
                        //console.log(response);
            });
        };

        self.resetWizard = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "test_reset_wizard")
                .done(function(response) {
                        //console.log(response);
            });
        };

        self.showImportProfileDialog = function() {
            self.clearUpload();
            
            // Determine which modal to show based on context
            var modalElement = $("#wizard_plugin_internal_slicer").length ? 
                $("#wizard_slicer_import") : 
                $("#settings_plugin_internal_slicer_import");
            
            modalElement.modal("show");
        };

        self.setAsDefaultSlicer = function() {
            if (self.settings.slicing.defaultSlicer() != "prusa") {
                self.settings.slicing.defaultSlicer("prusa");
                self.isDefaultSlicer("after_save");
            }
        };

        self.testEnginePath = function() {
            OctoPrint.util.testExecutable(self.settings.plugins.internal_slicer.slicer_engine())
                .done(function(response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.pathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.pathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.pathText(gettext("The path is not an executable"));
                        }
                    } else {
                        self.pathText(gettext("The path is valid"));
                    }
                    self.pathOk(response.result);
                    self.pathBroken(!response.result);
                });
        };

        self.requestData = function() {
			return $.ajax({
				url: API_BASEURL + "slicing/prusa/profiles",
				type: "GET",
				dataType: "json",
				success: self.fromResponse,
				error: function(xhr, status, error) {
					console.error("Error fetching profiles:", error);
					// Optionally show an error message to the user
					// new PNotify({
					//     title: 'Error',
					//     text: 'Could not load slicer profiles',
					//     type: 'error'
					// });
				}
			});
		};
		
		// Add profile check after importing new profile
        self.fromResponse = function(data) {
            var profiles = [];
            _.each(_.keys(data), function(key) {
                profiles.push({
                    key: key,
                    name: ko.observable(data[key].displayName),
                    description: ko.observable(data[key].description),
                    isdefault: ko.observable(data[key].default),
                    resource: ko.observable(data[key].resource)
                });
            });
            self.profiles.updateItems(profiles);
            
            // Update profile status after loading profiles
            self.checkProfiles();
        };
		

        self.onBeforeBinding = function () {
            //self.enableSlicingDialog = (self.settings.plugins.internal_slicer.disableGUI());
            self.settings = self.settingsViewModel.settings;
            self.requestData();
        };

        self.onSettingsShown = function() {
			// Handle default slicer state
			if ('slicing' in self.settings && 'defaultSlicer' in self.settings.slicing) {
				self.isDefaultSlicer(self.settings.slicing.defaultSlicer() == "prusa" ? "yes" : "no");
			} else {
				self.isDefaultSlicer("unknown");
			}
		
			// Refresh the profile list
			self.requestData();
			self.slicingViewModel.requestData();
		};

        self.onSettingsHidden = function() {
            self.resetPathTest();
        };

        self.resetPathTest = function() {
            self.pathBroken(false);
            self.pathOk(false);
            self.pathText("");
        };

    }

    // view model class, parameters for constructor, container to bind to
    OCTOPRINT_VIEWMODELS.push([
		Slic3rViewModel,
		["loginStateViewModel", "settingsViewModel", "slicingViewModel"],
		["#settings_plugin_internal_slicer_dialog", "#wizard_plugin_internal_slicer"]
	]);

});
