import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Enter today's readings by hand, or import a file. Every value is checked before anything is saved.
Item {
    id: screen
    property string member: vigil.astronaut
    property int refresh: 0
    readonly property var form: Api.ask("log_form", { id: member, v: [vigil.version, refresh] })
    readonly property var recent: Api.ask("entries", { id: member, v: [vigil.version, refresh] }).entries || []
    readonly property var files: Api.ask("import_files", { v: refresh })
    property var values: ({})
    property var errors: ({})
    property string saved: ""
    property var imported: null

    function setValue(id, text) {
        var copy = Object.assign({}, values)
        copy[id] = text
        values = copy
    }
    function save() {
        var out = Api.ask("log_readings", { id: member, values: values })
        if (out.error) { errors = { _: out.error }; return }
        errors = out.errors
        if (out.saved > 0) {
            saved = out.saved + (out.saved === 1 ? " reading" : " readings") + " saved for day " + out.day + "."
            values = {}
            refresh += 1
        } else saved = ""
    }
    function importFile(name) {
        imported = Api.ask("import_file", { id: member, file: name })
        refresh += 1
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Log readings" }
            Placard { visible: !!screen.form.date; text: "Day " + screen.form.day + ", " + screen.form.date }
            Item { Layout.fillWidth: true }
            VButton { kind: "primary"; text: "Save readings"; onClicked: screen.save() }
        }
        Banner { tone: "error"; text: screen.form.error || "" }
        RowLayout {
            visible: (screen.form.crew || []).length > 1
            spacing: 8
            Placard { text: "Entering for" }
            Repeater {
                model: screen.form.crew || []
                VButton { required property var modelData; text: modelData.name.split(" ")[0]; selected: screen.member === modelData.id; onClicked: { screen.member = modelData.id; screen.values = {}; screen.errors = {}; screen.saved = "" } }
            }
        }
        Banner {
            visible: screen.form.days_with_readings !== undefined && screen.form.days_with_readings < screen.form.learning_days
            text: "Learning " + (screen.form.member ? screen.form.member.name.split(" ")[0] + "'s" : "your") + " normal: " + screen.form.days_with_readings + " of " + screen.form.learning_days + " days with readings. Alerts start after that."
        }
        Banner { text: screen.form.for_someone_else ? "Entering results for " + screen.form.member.name + ". Their own readings stay private. You see only what you enter." : "" }
        Banner { tone: "success"; text: screen.saved }
        Banner { tone: "error"; text: screen.errors._ || (Object.keys(screen.errors).length ? "Some values need fixing. Nothing was saved." : "") }
        Split {
            Layout.fillWidth: true
            Repeater {
                model: screen.form.groups || []
                Panel {
                    id: group
                    required property var modelData
                    Layout.fillWidth: true
                    surface: true
                    title: modelData.name
                    Repeater {
                        model: group.modelData.signals
                        ColumnLayout {
                            id: row
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Body { text: row.modelData.name }
                                    Note {
                                        text: screen.form.for_someone_else ? row.modelData.unit
                                              : row.modelData.today !== null ? "Today: " + row.modelData.today + " " + row.modelData.unit
                                              : row.modelData.last !== null ? "Last: " + row.modelData.last + " " + row.modelData.unit + " on day " + row.modelData.last_day
                                              : row.modelData.cadence > 1 ? "Every " + row.modelData.cadence + " days" : "No readings yet"
                                    }
                                }
                                TextField {
                                    id: input
                                    Layout.preferredWidth: 120
                                    implicitHeight: Theme.touch
                                    text: screen.values[row.modelData.id] || ""
                                    placeholderText: row.modelData.unit
                                    placeholderTextColor: Theme.ink2
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    horizontalAlignment: Text.AlignRight
                                    rightPadding: 14
                                    font.family: Theme.body
                                    font.pixelSize: 19
                                    font.features: { "tnum": 1 }
                                    color: Theme.ink
                                    Accessible.name: row.modelData.name + " in " + row.modelData.unit
                                    onTextEdited: screen.setValue(row.modelData.id, text)
                                    background: Rectangle {
                                        radius: 9
                                        color: Theme.panel2
                                        border.width: input.activeFocus || screen.errors[row.modelData.id] ? 2 : 0
                                        border.color: screen.errors[row.modelData.id] ? Theme.warning : Theme.action
                                    }
                                }
                            }
                            RowLayout {
                                visible: !!screen.errors[row.modelData.id]
                                spacing: 8
                                StatusIcon { status: "red"; tint: Theme.warning }
                                Note { text: screen.errors[row.modelData.id] || ""; color: Theme.warning }
                            }
                        }
                    }
                }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "Import from a file"
                    Body { color: Theme.ink2; text: "Copy a file into the import folder: an Apple Health export (export.xml or export.zip), a spreadsheet with a date column and one column per reading, or a table with date, signal and value columns. A member column lets the Medical Officer import for several people." }
                    Note { text: screen.files.folder || ""; wrapMode: Text.WrapAnywhere }
                    Banner { visible: (screen.files.files || []).length === 0; text: "No files waiting in the import folder." }
                    Repeater {
                        model: screen.files.files || []
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Body { text: modelData.name; maximumLineCount: 1; elide: Text.ElideMiddle }
                            Note { Layout.fillWidth: false; text: modelData.kb + " KB" }
                            VButton { text: "Import"; onClicked: screen.importFile(modelData.name) }
                        }
                    }
                    Banner {
                        tone: screen.imported && screen.imported.error ? "error" : screen.imported && screen.imported.skipped ? "caution" : "success"
                        text: !screen.imported ? "" : screen.imported.error ? screen.imported.error
                              : screen.imported.imported + " readings imported, " + screen.imported.skipped + " rows left out."
                    }
                    Repeater {
                        model: screen.imported && screen.imported.reasons ? screen.imported.reasons : []
                        Note { required property string modelData; text: modelData }
                    }
                },
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "Recent readings"
                    Banner { visible: screen.recent.length === 0; text: "Nothing entered yet." }
                    Repeater {
                        model: screen.recent.slice(0, 12)
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 10
                            Note { Layout.fillWidth: false; Layout.preferredWidth: 64; text: "Day " + modelData.day; font.features: { "tnum": 1 } }
                            Body { text: modelData.name; maximumLineCount: 1; elide: Text.ElideRight }
                            Text { text: modelData.value + " " + modelData.unit; font.family: Theme.body; font.pixelSize: 17; font.features: { "tnum": 1 }; color: Theme.ink }
                            VButton {
                                kind: "quiet"
                                text: "Remove"
                                Accessible.name: "Remove " + modelData.name + " from day " + modelData.day
                                onClicked: { Api.ask("delete_entry", { id: screen.member, entry: modelData.id }); screen.refresh += 1 }
                            }
                        }
                    }
                }
            ]
        }
    }
}
