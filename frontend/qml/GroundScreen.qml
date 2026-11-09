import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    property bool standalone: false
    property int tick: 0
    readonly property var d: Api.ask("ground", { day: vigil.day, v: [vigil.version, tick] })
    readonly property real timeScale: d.delay_minutes * 60 / d.flight_seconds
    readonly property var systemKeys: Object.keys(d.crew[0].systems)
    readonly property int inFlight: d.packets.filter(function (p) { return p.state === "in_transit" || p.state === "sent" }).length
    readonly property var stateWord: ({ queued: "Queued", sent: "Sent", in_transit: "In transit", received: "Received" })

    Timer { interval: 400; running: true; repeat: true; onTriggered: screen.tick += 1 }

    function eta(seconds) {
        var total = Math.ceil(seconds * timeScale)
        return String(Math.floor(total / 60)).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0")
    }

    Rectangle { anchors { fill: parent; margins: -16 } color: Theme.bg }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton { visible: !screen.standalone }
            BigTitle { text: "Mission control" }
            Placard { text: "Earth receives this " + screen.d.delay_minutes + " minutes late" }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: screen.standalone
                implicitWidth: badge.implicitWidth + 20
                implicitHeight: 36
                color: "transparent"
                border.color: Theme.caution
                border.width: 2
                Placard { id: badge; anchors.centerIn: parent; text: "Simulated data"; color: Theme.caution; font.pixelSize: 18 }
            }
            VButton { text: screen.d.link_up ? "Drop link" : "Restore link"; onClicked: Api.ask("set_link", { up: !screen.d.link_up }) }
        }
        Panel {
            Layout.fillWidth: true
            visible: screen.d.level3.length > 0
            border.color: Theme.warning
            border.width: 2
            Repeater {
                model: screen.d.level3
                RowLayout {
                    required property var modelData
                    spacing: 14
                    Annunciator { status: "red"; label: modelData.astronaut + " Level 3" }
                    Body { text: modelData.system; font.bold: true; Layout.fillWidth: false }
                    Body { text: modelData.reason }
                }
            }
        }
        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                title: "Crew status · Day " + screen.d.day
                GridLayout {
                    Layout.fillWidth: true
                    columns: screen.systemKeys.length + 2
                    columnSpacing: 6
                    rowSpacing: 8
                    Placard { text: "Crew" }
                    Repeater { model: screen.systemKeys; Placard { required property string modelData; text: modelData } }
                    Placard { text: "Radiation" }
                    Repeater {
                        model: screen.d.crew.length * (screen.systemKeys.length + 2)
                        Loader {
                            required property int index
                            readonly property int columns: screen.systemKeys.length + 2
                            readonly property var person: screen.d.crew[Math.floor(index / columns)]
                            readonly property int column: index % columns
                            sourceComponent: column === 0 ? tagCell : statusCell
                        }
                    }
                }
                Component { id: tagCell; Body { text: parent.person.tag; font.bold: true } }
                Component {
                    id: statusCell
                    Annunciator {
                        compact: true
                        status: parent.column === screen.systemKeys.length + 1 ? parent.person.radiation : parent.person.systems[screen.systemKeys[parent.column - 1]]
                    }
                }
                Note { text: "Ground sees summaries and Level 3 reasons. Raw values stay on the ship unless the astronaut shares them." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    title: "Packet timeline · " + (screen.d.link_up ? screen.inFlight + " in flight" : "Link lost. Packets wait on board.")
                    Note { visible: screen.d.packets.length === 0; text: "No packets yet. Run the mission to send some." }
                    Repeater {
                        model: Math.min(7, screen.d.packets.length)
                        ColumnLayout {
                            id: packet
                            required property int index
                            readonly property var p: screen.d.packets[index]
                            readonly property bool urgent: p.priority === 0
                            readonly property real progress: p.state === "received" ? 1 : p.state === "queued" ? 0 : 1 - p.seconds_left / p.flight_seconds
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Body { text: packet.p.title; font.bold: true; color: packet.urgent ? Theme.warning : Theme.ink; maximumLineCount: 1; elide: Text.ElideRight }
                                Placard { text: "Day " + packet.p.mission_day + " · " + packet.p.size_kb + " KB"; font.pixelSize: 17 }
                                Placard { text: screen.stateWord[packet.p.state]; font.pixelSize: 17 }
                                Text {
                                    Layout.preferredWidth: 78
                                    horizontalAlignment: Text.AlignRight
                                    text: packet.p.state === "in_transit" || packet.p.state === "sent" ? screen.eta(packet.p.seconds_left) : packet.p.state === "received" ? "Arrived" : "Waiting"
                                    font.family: Theme.mono; font.pixelSize: 17; color: Theme.ink
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 4
                                color: Theme.rule
                                Rectangle { x: Math.max(0, Math.min(packet.progress, 1)) * (parent.width - width); y: -4; width: 12; height: 12; color: packet.urgent ? Theme.warning : Theme.ink }
                            }
                        }
                    }
                    Note { text: "Countdown shows flight time. This demo plays " + screen.d.delay_minutes + " minutes as " + screen.d.flight_seconds + " seconds." }
                }
            ]
        }
    }
}
