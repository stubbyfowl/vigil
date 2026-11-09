import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: screen
    property var draft: Api.ask("get_config", {}).config
    readonly property var signalList: Api.ask("get_config", {}).signals
    readonly property var groups: ["mission", "sync", "detector", "baseline", "escalation", "status", "radiation"]
    property string message: ""

    function values() {
        var out = { disabled_signals: draft.disabled_signals }
        groups.forEach(function (g) { out[g] = draft[g] })
        return out
    }
    function save() {
        var result = Api.ask("put_config", { values: values() })
        message = result.error || "Saved. The mission was recomputed."
    }
    function restore() {
        var result = Api.ask("reset_config", {})
        message = result.error || "Defaults restored."
        if (!result.error) draft = result.config
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Admin" }
            Placard { text: "Starting values, not clinical limits" }
            Item { Layout.fillWidth: true }
            VButton { text: "Restore defaults"; onClicked: screen.restore() }
            VButton { kind: "primary"; text: "Save"; onClicked: screen.save() }
        }
        Body { visible: screen.message.length > 0; text: screen.message }
        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: 12
            rowSpacing: 12
            Repeater {
                model: screen.groups
                Panel {
                    id: group
                    required property string modelData
                    readonly property string name: modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                    title: name
                    Repeater {
                        model: Object.keys(screen.draft[group.name])
                        RowLayout {
                            id: field
                            required property string modelData
                            readonly property string key: modelData
                            readonly property var current: screen.draft[group.name][key]
                            Layout.fillWidth: true
                            Body { text: field.key.replace(/_/g, " ") }
                            Toggle {
                                visible: typeof field.current === "boolean"
                                checked: field.current === true
                                onToggled: screen.draft[group.name][field.key] = checked
                            }
                            TextField {
                                id: input
                                visible: typeof field.current !== "boolean"
                                Layout.preferredWidth: 110
                                implicitHeight: Theme.touch
                                text: String(field.current)
                                font.family: Theme.body
                                font.pixelSize: 18
                                color: Theme.ink
                                Accessible.name: field.key
                                background: Rectangle { color: Theme.panel2; border.color: input.activeFocus ? Theme.action : Theme.rule }
                                onEditingFinished: screen.draft[group.name][field.key] = typeof field.current === "number" ? Number(text) : text
                            }
                        }
                    }
                }
            }
            Panel {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                title: "Signals on or off"
                Repeater {
                    model: screen.signalList
                    Toggle {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.name
                        checked: screen.draft.disabled_signals.indexOf(modelData.id) < 0
                        onToggled: {
                            var off = screen.draft.disabled_signals.filter(function (id) { return id !== modelData.id })
                            if (!checked) off.push(modelData.id)
                            screen.draft.disabled_signals = off
                        }
                    }
                }
            }
        }
    }
}
