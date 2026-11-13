import QtQuick
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: screen
    property bool standalone: false
    property int tick: 0
    // Crew status changes only with the day or new data. The packet list moves every half second, so it is asked for on its own.
    readonly property var raw: Api.ask("ground", { day: vigil.day, v: [vigil.version, vigil.signedIn, vigil.locked] })
    readonly property var flow: Api.ask("packets", { v: [tick, vigil.version, vigil.signedIn, vigil.locked, vigil.linkUp] })
    // Signed out or locked: show an empty control room, so no stale data appears.
    readonly property var d: raw.error ? { system_keys: [], crew: [], level3: [], live: !vigil.isDemo, day: vigil.day, delay_minutes: vigil.delayMinutes } : raw
    readonly property var f: flow.error ? { packets: [], link_up: true, flight_seconds: Math.max(1, vigil.flightSeconds) } : flow
    readonly property real timeScale: d.delay_minutes * 60 / f.flight_seconds
    readonly property var systemKeys: d.system_keys
    readonly property int inFlight: f.packets.filter(function (p) { return p.state === "in_transit" || p.state === "sent" }).length
    // One line per reason, listing everyone it applies to, so a storm that hits five people reads as one event.
    readonly property var level3Groups: {
        var groups = []
        screen.d.level3.forEach(function (a) {
            var g = groups.find(function (x) { return x.system === a.system && x.reason === a.reason })
            if (g) g.people.push(a.astronaut)
            else groups.push({ system: a.system, reason: a.reason, people: [a.astronaut] })
        })
        return groups
    }
    readonly property var stateWord: ({ queued: "Queued", sent: "Sent", in_transit: "In transit", received: "Received", in_outbox: "In outbox", picked_up: "Picked up" })

    Timer { interval: 500; running: screen.visible && !!screen.Window.window && screen.Window.window.visible; repeat: true; onTriggered: screen.tick += 1 }

    function eta(seconds) {
        var total = Math.ceil(seconds * timeScale)
        return String(Math.floor(total / 60)).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0")
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton { visible: !screen.standalone }
            BigTitle { text: "Mission Control" }
            Note { Layout.fillWidth: false; text: "Earth receives this " + screen.d.delay_minutes + " minutes late" }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: screen.standalone && !screen.d.live
                implicitWidth: badge.implicitWidth + 24
                implicitHeight: 34
                radius: 17
                color: Theme.cautionBg
                Placard { id: badge; anchors.centerIn: parent; text: "Simulated data"; color: Theme.caution }
            }
            VButton { visible: !screen.d.live; text: screen.f.link_up ? "Drop link" : "Restore link"; onClicked: Api.ask("set_link", { up: !screen.f.link_up }) }
            VButton { visible: screen.standalone; text: "Lock"; onClicked: vigil.lock() }
            VButton { visible: screen.standalone; text: "Sign out"; onClicked: vigil.signOut() }
        }
        Panel {
            Layout.fillWidth: true
            visible: screen.d.level3.length > 0
            surface: true
            Repeater {
                model: screen.level3Groups
                RowLayout {
                    required property var modelData
                    spacing: 14
                    StatusPill { status: "red"; compact: true; label: "Level 3 · " + modelData.system }
                    Placard { text: modelData.people.join("  "); color: Theme.ink }
                    Body { text: modelData.reason }
                }
            }
        }
        Split {
            Layout.fillWidth: true
            stackBelow: 1000  // the crew grid needs the full width on a small window
            Panel {
                Layout.fillWidth: true
                surface: true
                title: screen.d.live ? "Latest status from each crew member" : "Crew status, day " + screen.d.day
                Banner { visible: screen.d.crew.length === 0; text: "No status yet. Each crew member sends a summary every 7 days, and whenever they call Earth." }
                GridLayout {
                    Layout.fillWidth: true
                    columns: screen.systemKeys.length + 2
                    columnSpacing: 6
                    rowSpacing: 8
                    Placard { text: "Crew" }
                    Repeater { model: screen.systemKeys; Placard { required property string modelData; text: modelData.charAt(0).toUpperCase() + modelData.slice(1) } }
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
                Component { id: tagCell; Body { text: parent.person.tag; font.weight: Font.DemiBold } }
                Component {
                    id: statusCell
                    StatusPill {
                        compact: true
                        status: parent.column === screen.systemKeys.length + 1 ? parent.person.radiation : parent.person.systems[screen.systemKeys[parent.column - 1]]
                    }
                }
                Note { text: "Earth sees each person's status and any Level 3 reason. Raw readings arrive only from people who share them." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: screen.d.live ? "Packets" : "Packet timeline, " + (screen.f.link_up ? screen.inFlight + " in flight" : "Link lost. Packets wait on board.")
                    Note { visible: screen.f.packets.length === 0; text: screen.d.live ? "No packets yet." : "No packets yet." }
                    Repeater {
                        model: Math.min(7, screen.f.packets.length)
                        ColumnLayout {
                            id: packet
                            required property int index
                            readonly property var p: screen.f.packets[index]
                            readonly property bool urgent: p.priority === 0
                            readonly property real progress: p.state === "received" || p.state === "picked_up" ? 1 : p.state === "queued" || p.state === "in_outbox" ? 0 : 1 - p.seconds_left / p.flight_seconds
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Body { text: packet.p.title; font.weight: Font.DemiBold; color: packet.urgent ? Theme.warning : Theme.ink; maximumLineCount: 1; elide: Text.ElideRight }
                                Placard { text: "Day " + packet.p.mission_day + " · " + packet.p.size_kb + " KB"; font.pixelSize: 17 }
                                Placard { text: screen.stateWord[packet.p.state]; font.pixelSize: 17 }
                                Text {
                                    Layout.preferredWidth: 78
                                    horizontalAlignment: Text.AlignRight
                                    text: packet.p.state === "in_transit" || packet.p.state === "sent" ? screen.eta(packet.p.seconds_left) : packet.p.state === "received" ? "Arrived" : packet.p.state === "picked_up" || packet.p.state === "in_outbox" ? "" : "Waiting"
                                    font.family: Theme.body; font.features: { "tnum": 1 }; font.pixelSize: 17; color: Theme.ink
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
                    Note { text: screen.d.live ? "Each packet is a file in the outbox folder until the vehicle's comm system sends it. Earth gets it about " + screen.d.delay_minutes + " minutes later." : "Countdown shows flight time. This demo plays " + screen.d.delay_minutes + " minutes as " + screen.f.flight_seconds + " seconds." }
                }
            ]
        }
    }
}
