import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: screen
    property var draft: Api.ask("get_config", {}).config
    readonly property var signalList: Api.ask("get_config", {}).signals
    readonly property var groups: ["mission", "sync", "detector", "baseline", "escalation", "status", "radiation"]
    // Names for settings whose keys do not read as words.
    readonly property var labels: ({
        z_limit: "Z-score limit", ewma_lambda: "EWMA weight (λ)", ewma_l: "EWMA limit (L)", cusum_k: "CUSUM slack (k)",
        cusum_h: "CUSUM limit (h)", bandwidth_kb_s: "Bandwidth (kb/s)", one_way_delay_minutes: "One-way delay (min)",
        seed: "Random seed", sigma_floor: "Smallest spread (σ)", days_per_second: "Demo days per second"
    })
    property string message: ""

    function values() {
        var out = { disabled_signals: draft.disabled_signals }
        groups.forEach(function (g) { out[g] = draft[g] })
        return out
    }
    function save() {
        var result = Api.ask("put_config", { values: values() })
        message = result.error || "Saved and recalculated."
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
            BigTitle { text: "Thresholds" }
            Placard { text: "Not reviewed by a flight surgeon" }
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
                    divider: true
                    title: name.charAt(0).toUpperCase() + name.slice(1)
                    Repeater {
                        model: Object.keys(screen.draft[group.name])
                        RowLayout {
                            id: field
                            required property string modelData
                            readonly property string key: modelData
                            readonly property var current: screen.draft[group.name][key]
                            Layout.fillWidth: true
                            Body { text: screen.labels[field.key] || field.key.charAt(0).toUpperCase() + field.key.slice(1).replace(/_/g, " ") }
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
                                background: Rectangle { color: Theme.panel2; border.color: input.activeFocus ? Theme.action : "transparent"; radius: 9 }
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
                divider: true
                title: "Signals in use"
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
