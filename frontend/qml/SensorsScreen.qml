import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("sensors", { id: vigil.astronaut, day: vigil.day, v: vigil.version })

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: screen.d.live ? "Data sources" : "Sensors" }
            Item { Layout.fillWidth: true }
            Placard { text: screen.d.reporting + " of " + screen.d.sensors.length + " reported today" }
        }
        Note { text: screen.d.live ? "Which kinds of reading arrived today. A missing reading lowers confidence. It never counts as a health change. Log readings by hand or import a device export." : "A missing reading lowers confidence. It never counts as a health change. These wearables and their batteries are simulated." }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 12
            rowSpacing: 12
            Repeater {
                model: screen.d.sensors
                Panel {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    divider: true
                    RowLayout {
                        Layout.fillWidth: true
                        Body { text: modelData.name; font.pixelSize: 20; font.weight: Font.Medium }
                        StatusPill { compact: true; status: modelData.connected ? "green" : "yellow"; label: modelData.connected ? "Reporting" : "No reading" }
                    }
                    Note { visible: modelData.battery === null; text: modelData.last_day ? "Last reading on day " + modelData.last_day : "No readings yet" }
                    RowLayout {
                        visible: modelData.battery !== null
                        Layout.fillWidth: true
                        spacing: 10
                        Placard { text: "Battery" }
                        Rectangle {
                            Layout.fillWidth: true
                            height: 6
                            radius: 3
                            color: Theme.panel2
                            Rectangle { width: parent.width * (modelData.battery || 0) / 100; height: parent.height; radius: 3; color: Theme.action }
                        }
                        Text { text: modelData.battery + "%"; font.family: Theme.body; font.features: { "tnum": 1 }; font.pixelSize: 17; color: Theme.ink }
                        Placard { text: modelData.power; font.pixelSize: 17 }
                    }
                    Note { visible: modelData.missing.length > 0; text: "Missing today: " + modelData.missing.join(", ") }
                }
            }
        }
    }
}
