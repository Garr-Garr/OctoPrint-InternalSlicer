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

        self.pathBroken = ko.observable();
        self.pathOk = ko.observable(false);
        self.pathText = ko.observable();
        self.pathHelpVisible = ko.pureComputed(function() {
            return self.pathBroken() || self.pathOk();
        });

        self.fileName = ko.observable();

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
            if (self.uploadData) {
                self.uploadData.submit();
            }
        });
        // wizard testing
        self.showNextDiv = function (data) {
            var div1 = document.getElementById("test1");
            var div2 = document.getElementById("test2");
            var div3 = document.getElementById("test3");
          
            if (data === "test1") {
              div1.style.display = "none";
              div2.style.display = "block";
            } else if (data === "test2") {
              div2.style.display = "none";
              div3.style.display = "block";
            } else if (data === "test3") {
              div3.style.display = "none";
              div1.style.display = "block";
            }};
        
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

        // Uploading profiles
        self.uploadElement.fileupload({
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            headers: OctoPrint.getRequestHeaders(),
            add: function(e, data) {
                if (data.files.length == 0) {
                    return false;
                }

                self.fileName(data.files[0].name);

                var name = self.fileName().substr(0, self.fileName().lastIndexOf("."));
                self.placeholderName(self._sanitize(name).toLowerCase());
                self.placeholderDisplayName(name);
                self.placeholderDescription("Imported from " + self.fileName() + " on " + formatDate(new Date().getTime() / 1000));

                var form = {
                    allowOverwrite: self.profileAllowOverwrite()
                };
                if (self.profileName() !== undefined) {
                    form["name"] = self.profileName();
                }
                if (self.profileDisplayName() !== undefined) {
                    form["displayName"] = self.profileDisplayName();
                }
                if (self.profileDescription() !== undefined) {
                    form["description"] = self.profileDescription();
                }

                data.formData = form;
                self.uploadData = data;
            },
            done: function(e, data) {
                self.clearUpload();

                $("#settings_plugin_internal_slicer_import").modal("hide");
                self.requestData();
                self.slicingViewModel.requestData();
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
        
        self.showSlicerCommandResponse = function(input){
			self.internal_slicer_command_response_popup.modal({keyboard: false, backdrop: "static", show: true});
			if (input === "hide"){
				self.internal_slicer_command_response_popup.modal("hide");
			}
		};

        self.onDataUpdaterPluginMessage = function(plugin, data) {
			if (plugin != "internal_slicer") {
				return;
			}
            if (data.slicerCommandResponse !== undefined ){
                //console.log(data.slicerCommandResponse);
                
                self.slicerCommandResponse(self.slicerCommandResponse() + data.slicerCommandResponse.toString());

                //get div and scroll to bottom
                self.slicerCommandResponseText = $("#slicerCommandResponseText");
                self.slicerCommandResponseText.scrollTop(self.slicerCommandResponseText[0].scrollHeight);
                self.slicerCommandResponseText2 = $("#slicerCommandResponseText2");
                self.slicerCommandResponseText2.scrollTop(self.slicerCommandResponseText2[0].scrollHeight);
            }
        };

        if(data.type == "popup") {
            new PNotify({
                title: 'Internal Slicer',
                text: data.msg,
                });
        }
        
        self.downloadSlicer = function() {
            var url = OctoPrint.getSimpleApiUrl("internal_slicer");
            OctoPrint.issueCommand(url, "download_prusaslicer_script")
                .done(function(response) {
                        //console.log(response);
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
            $("#settings_plugin_internal_slicer_import").modal("show");
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
            $.ajax({
                url: API_BASEURL + "slicing/prusa/profiles",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

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
        };

        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings;
            self.requestData();
        };

        self.onSettingsShown = function() {
            if ('slicing' in self.settings && 'defaultSlicer' in self.settings.slicing) {
                self.isDefaultSlicer(self.settings.slicing.defaultSlicer() == "prusa" ? "yes" : "no");
            } else {
                self.isDefaultSlicer("unknown");
            }
        }

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
    
        // e.g. loginStateViewModel, settingsViewModel, ...
        [ "loginStateViewModel", "settingsViewModel", "slicingViewModel"],
    
        // e.g. #settings_plugin_internal_slicer, #tab_plugin_internal_slicer, ... "#internal_slicer_command_response_popup"
        [ "#settings_plugin_internal_slicer_dialog"]
    ]);

});
