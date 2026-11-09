import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: home
    readonly property var d: Api.ask("astronaut", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var names: {
        var out = {}
        Api.ask("crew", {}).signals.forEach(function (s) { out[s.id] = s.name })
        return out
    }
    readonly property var watching: d.systems.filter(function (s) { return s.status !== "green" }).map(function (s) { return s.name })
    readonly property var topAlert: d.alerts.length ? d.alerts[0] : null
    readonly property int worst: {
        var best = -1, score = -1
        d.systems.forEach(function (s, i) { if (s.status !== "green" && s.score > score) { best = i; score = s.score } })
        return best
    }
    onWorstChanged: if (worst >= 0) cards.positionViewAtIndex(worst, ListView.Contain)

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            Layout.minimumHeight: 110
            Layout.maximumHeight: 110
            spacing: 16
            Column {
                Layout.preferredWidth: 250
                Text { text: home.d.astronaut.name; font.family: Theme.body; font.bold: true; font.pixelSize: 26; color: Theme.ink }
                Body { text: home.d.astronaut.role; color: Theme.ink2 }
            }
            Rectangle {
                visible: !home.topAlert
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.panel
                border.color: Theme.rule
                radius: 4
                RowLayout {
                    anchors { fill: parent; leftMargin: 20; rightMargin: 20 }
                    spacing: 18
                    Text {
                        text: home.d.learning ? "LEARNING" : home.watching.length ? "WATCHING" : "ALL CLEAR"
                        font.family: Theme.label; font.pixelSize: 76; font.letterSpacing: 3.8
                        color: home.d.learning || home.watching.length ? Theme.ink : Theme.nominal
                    }
                    Body {
                        color: Theme.ink2
                        text: home.d.learning ? "Vigil is learning your normal. It will not raise alerts until it has enough days of readings."
                            : home.watching.length ? "No alerts. " + home.watching.join(" and ") + " moved a little from your normal. Vigil is keeping an eye on it."
                            : "Every system is inside your own normal today."
                    }
                }
            }
            AbstractButton {
                visible: !!home.topAlert
                Layout.fillWidth: true
                Layout.fillHeight: true
                Accessible.role: Accessible.Button
                Accessible.name: home.topAlert ? "Open alert. " + home.topAlert.message : ""
                onClicked: vigil.navigate("/alert/" + home.topAlert.id)
                background: Rectangle {
                    color: Theme.panel
                    radius: 4
                    border.width: 2
                    border.color: home.topAlert && home.topAlert.level >= 3 ? Theme.warning : Theme.caution
                }
                contentItem: RowLayout {
                    spacing: 16
                    Column {
                        leftPadding: 14
                        spacing: 4
                        Text { text: home.d.alerts.length + (home.d.alerts.length > 1 ? " ALERTS" : " ALERT"); font.family: Theme.label; font.pixelSize: 48; font.letterSpacing: 2; color: Theme.ink }
                        LevelBadge { level: home.topAlert ? home.topAlert.level : 0 }
                    }
                    Body { text: home.topAlert ? home.topAlert.message : ""; font.pixelSize: 20; maximumLineCount: 3; elide: Text.ElideRight }
                    Placard { visible: home.d.alerts.length > 1; text: "+" + (home.d.alerts.length - 1) + " more"; rightPadding: 14 }
                }
            }
        }

        // Swipe, drag or use the dots. All four systems stay in the same order.
        ListView {
            id: cards
            objectName: "cards"
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: ListView.Horizontal
            snapMode: ListView.SnapToItem
            boundsBehavior: Flickable.StopAtBounds
            spacing: 14
            clip: true
            cacheBuffer: 2000
            model: 4
            delegate: AbstractButton {
                id: card
                required property int index
                readonly property var s: home.d.systems[index]
                width: 372
                height: ListView.view.height
                Accessible.role: Accessible.Button
                Accessible.name: s.name + ". " + (s.learning ? "Learning." : Theme.statusWord(s.status) + ". Drift " + s.score + " of 100.") + " Open details."
                onClicked: vigil.navigate("/system/" + s.id)
                background: Rectangle {
                    color: Theme.panel
                    radius: 4
                    border.color: card.visualFocus ? Theme.action : Theme.rule
                    border.width: card.visualFocus ? 3 : 1
                }
                contentItem: ColumnLayout {
                    spacing: 6
                    anchors { fill: parent; margins: 16; leftMargin: 18; rightMargin: 18 }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: card.s.name; font.family: Theme.label; font.pixelSize: 28; font.letterSpacing: 0.9; font.capitalization: Font.AllUppercase; color: Theme.ink; Layout.fillWidth: true; elide: Text.ElideRight }
                        Placard { visible: card.s.learning; text: "Learning" }
                        Annunciator { visible: !card.s.learning; status: card.s.status }
                    }
                    RowLayout {
                        spacing: 10
                        Text { text: card.s.learning ? "--" : card.s.score; font.family: Theme.mono; font.bold: true; font.pixelSize: 72; color: Theme.ink }
                        Placard { text: "drift / 100"; Layout.alignment: Qt.AlignBottom; bottomPadding: 12 }
                    }
                    Sparkline { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 70; values: card.s.trend; label: card.s.name }
                    Note {
                        maximumLineCount: 1
                        elide: Text.ElideRight
                        text: card.s.learning ? "Learning your normal" : card.s.flagged.length ? "Moved: " + card.s.flagged.map(function (id) { return home.names[id] || id }).join(", ") : "Inside your normal"
                    }
                    RowLayout {
                        spacing: 10
                        Placard { text: "Confidence" }
                        Rectangle {
                            Layout.fillWidth: true
                            height: 8
                            color: Theme.panel2
                            border.color: Theme.rule
                            Rectangle { width: parent.width * card.s.confidence; height: parent.height; color: Theme.ink2 }
                        }
                        Text { text: Math.round(card.s.confidence * 100) + "%"; font.family: Theme.mono; font.pixelSize: 17; color: Theme.ink }
                    }
                }
            }
        }

        Row {
            Layout.alignment: Qt.AlignHCenter
            visible: !vigil.demo.active
            spacing: 2
            Repeater {
                model: 4
                AbstractButton {
                    required property int index
                    implicitWidth: Theme.touch
                    implicitHeight: Theme.touch
                    readonly property bool current: Math.round(cards.contentX / 386) === index
                    Accessible.role: Accessible.Button
                    Accessible.name: "Show " + home.d.systems[index].name
                    onClicked: cards.positionViewAtIndex(index, ListView.Beginning)
                    background: Item {}
                    contentItem: Item {
                        Rectangle {
                            anchors.centerIn: parent
                            width: 14; height: 14; radius: 7
                            color: parent.parent.current ? Theme.ink : "transparent"
                            border.color: parent.parent.current ? Theme.ink : Theme.ink2
                            border.width: 2
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Repeater {
                model: [["/checkin", "Check-in", "normal"], ["/radiation", "Radiation", "normal"], ["/crew", "Crew", "normal"], ["/earth", "Call Earth", "primary"]]
                VButton {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 72
                    textSize: 27
                    text: modelData[1]
                    kind: modelData[2]
                    onClicked: vigil.navigate(modelData[0])
                }
            }
        }
    }
}
