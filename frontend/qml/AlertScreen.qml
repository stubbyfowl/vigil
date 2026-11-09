import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: screen
    readonly property string alertId: vigil.route.split("/")[2] || ""
    readonly property string owner: alertId.split("-")[0]
    readonly property var fresh: Api.ask("alert_detail", { id: owner, alert_id: alertId, day: vigil.day, v: vigil.version })
    property var d: null
    property bool showWhy: false
    property string actionError: ""
    onFreshChanged: if (!fresh.error) d = fresh
    Component.onCompleted: if (!fresh.error) d = fresh

    function act(action) {
        actionError = vigil.alertAction(owner, alertId, action)
        if (!actionError && action !== "escalate") vigil.back()
    }

    ErrorMessage { anchors.fill: parent; visible: screen.d === null; text: screen.fresh.error || "" }

    Loader {
        anchors.fill: parent
        active: screen.d !== null
        sourceComponent: PageScroll {
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                BackButton {}
                LevelBadge { level: screen.d.alert.level }
                Placard { text: screen.d.alert.system_name; font.pixelSize: 24 }
                Placard { visible: screen.d.closed; text: "This alert has closed" }
                Placard { visible: !!screen.d.alert.recovering; text: "Readings are recovering" }
                Item { Layout.fillWidth: true }
                VButton { text: "Why?"; onClicked: screen.showWhy = true }
            }
            Split {
                Layout.fillWidth: true
                Panel {
                    Layout.fillWidth: true
                    title: "What Vigil sees"
                    Body { text: screen.d.alert.message; font.pixelSize: 25 }
                }
                Panel {
                    Layout.fillWidth: true
                    title: "Do this"
                    Body { text: screen.d.alert.action; font.pixelSize: 25; font.bold: true }
                    Note { text: screen.d.alert.recheck_text; font.pixelSize: 18 }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    VButton { Layout.fillWidth: true; kind: "primary"; text: "Done"; onClicked: screen.act("done") }
                    VButton { Layout.fillWidth: true; text: "Snooze 2 hours"; onClicked: screen.act("snooze") }
                    VButton {
                        Layout.fillWidth: true
                        kind: "danger"
                        text: "Escalate"
                        enabled: screen.d.alert.level < 3
                        onClicked: screen.d.alert.level === 2 ? confirmEscalate.open() : screen.act("escalate")
                    }
                }
                Body { visible: screen.actionError.length > 0; text: screen.actionError; color: Theme.warning }
                Note { text: screen.d.alert.level_reason; font.pixelSize: 18 }
                Note { text: screen.d.alert.disclaimer }
                Panel {
                    Layout.fillWidth: true
                    visible: !!screen.d.protocol
                    title: screen.d.protocol ? screen.d.protocol.name + " · " + screen.d.protocol.minutes + " min" : ""
                    Body { text: screen.d.protocol ? screen.d.protocol.steps.join(" ") : "" }
                    Note { text: screen.d.protocol ? "Stop and escalate if: " + screen.d.protocol.escalate_if + " " + screen.d.protocol_label : "" }
                }
                second: [
                    Repeater {
                        model: screen.d.charts.length
                        Panel {
                            required property int index
                            Layout.fillWidth: true
                            title: screen.d.charts[index] ? screen.d.charts[index].name : ""
                            SeriesChart { Layout.fillWidth: true; series: screen.d.charts[index]; chartHeight: index === 0 ? 240 : 150 }
                        }
                    },
                    Panel {
                        Layout.fillWidth: true
                        visible: screen.d.charts.length === 0
                        title: "Dose rate"
                        Body { text: "Open Radiation for the storm view." }
                        VButton { text: "Open Radiation"; onClicked: vigil.navigate("/radiation") }
                    }
                ]
            }
        }
    }

    Dialog {
        id: confirmEscalate
        objectName: "confirmEscalate"
        anchors.centerIn: parent
        modal: true
        width: 560
        padding: 24
        background: Rectangle { color: Theme.panel; border.color: Theme.rule; radius: 4 }
        ColumnLayout {
            anchors.fill: parent
            spacing: 14
            BigTitle { text: "Send to Earth?"; font.pixelSize: 32 }
            Body { text: "Level 3 sends a priority packet. You can undo the level on this screen, but a packet already sent cannot be recalled." }
            RowLayout {
                VButton { Layout.fillWidth: true; text: "Cancel"; onClicked: confirmEscalate.close() }
                VButton { Layout.fillWidth: true; kind: "danger"; text: "Send to Earth"; onClicked: { confirmEscalate.close(); screen.act("escalate") } }
            }
        }
    }

    Rectangle {
        id: drawer
        visible: x < parent.width
        y: 0
        x: screen.showWhy ? parent.width - width : parent.width
        width: Math.min(640, parent.width)
        height: parent.height
        color: Theme.panel
        border.color: Theme.rule
        Behavior on x { enabled: !vigil.reduceMotion; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        PageScroll {
            anchors { fill: parent; margins: 18 }
            RowLayout {
                Layout.fillWidth: true
                BigTitle { text: "Why?"; Layout.fillWidth: true }
                VButton { text: "Close"; onClicked: screen.showWhy = false }
            }
            Body { text: screen.d ? screen.d.alert.level_reason : ""; color: Theme.ink2 }
            Repeater {
                model: screen.d ? screen.d.alert.why.signals : []
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 6
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.rule }
                    Body { text: modelData.name; font.bold: true; font.pixelSize: 19 }
                    GridLayout {
                        columns: 4
                        Layout.fillWidth: true
                        columnSpacing: 10
                        Placard { text: "Your normal"; font.pixelSize: 17; Layout.fillWidth: true; Layout.preferredWidth: 1 }
                        Placard { text: "Now"; font.pixelSize: 17; Layout.fillWidth: true; Layout.preferredWidth: 1 }
                        Placard { text: "Change"; font.pixelSize: 17; Layout.fillWidth: true; Layout.preferredWidth: 1 }
                        Placard { text: "Days"; font.pixelSize: 17; Layout.fillWidth: true; Layout.preferredWidth: 1 }
                        Body { text: modelData.baseline_low + " to " + modelData.baseline_high; font.bold: true; Layout.preferredWidth: 1 }
                        Body { text: modelData.current + " " + modelData.unit; font.bold: true; Layout.preferredWidth: 1 }
                        Body { text: (modelData.change > 0 ? "+" : "") + modelData.change; font.bold: true; Layout.preferredWidth: 1 }
                        Body { text: modelData.days_of_drift; font.bold: true; Layout.preferredWidth: 1 }
                    }
                    Note { text: modelData.rule }
                }
            }
            Note { text: (screen.d ? screen.d.alert.disclaimer : "") + " Thresholds are starting values, not clinical limits." }
        }
    }
}
