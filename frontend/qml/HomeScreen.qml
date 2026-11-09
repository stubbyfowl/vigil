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
    readonly property int cardWidth: 340
    readonly property int firstVisible: Math.round(cards.contentX / (cardWidth + 16))
    onWorstChanged: if (worst >= 0) cards.positionViewAtIndex(worst, ListView.Contain)

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            spacing: 10
            Layout.topMargin: 8
            Text { text: home.d.astronaut.name; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 18; color: Theme.ink }
            Text { text: home.d.astronaut.role; font.family: Theme.body; font.pixelSize: 18; color: Theme.ink2 }
        }

        Statement {
            Layout.topMargin: 14
            Layout.maximumWidth: 800
            size: (lead + detail).length < 90 ? 46 : (lead + detail).length < 145 ? 40 : 34
            lead: home.topAlert ? Theme.lead(home.topAlert.message)
                : home.d.learning ? "Learning your normal."
                : home.watching.length ? "Keeping an eye on " + home.watching.join(" and ") + "."
                : "All clear."
            detail: home.topAlert ? Theme.rest(home.topAlert.message)
                : home.d.learning ? "Vigil needs a few more days of readings before it can raise an alert."
                : home.watching.length ? "No alerts. It moved a little from your normal."
                : "Every system is inside your own normal today."
        }

        RowLayout {
            Layout.topMargin: 12
            Layout.preferredHeight: Theme.touch
            visible: !!home.topAlert
            spacing: 12
            VButton { kind: "primary"; text: "See what to do  ›"; onClicked: vigil.navigate("/alert/" + home.topAlert.id) }
            LevelBadge { level: home.topAlert ? home.topAlert.level : 0 }
            Text {
                visible: home.d.alerts.length > 1
                text: "and " + (home.d.alerts.length - 1) + " more"
                font.family: Theme.body; font.pixelSize: 16; color: Theme.ink2
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: 6 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 0
            Text { text: "Systems"; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 18; color: Theme.ink; Layout.fillWidth: true }
            VButton { text: "‹"; textSize: 24; Accessible.name: "Previous system"; enabled: home.firstVisible > 0; onClicked: cards.positionViewAtIndex(home.firstVisible - 1, ListView.Beginning) }
            VButton { Layout.leftMargin: 8; text: "›"; textSize: 24; Accessible.name: "Next system"; enabled: !cards.atXEnd; onClicked: cards.positionViewAtIndex(home.firstVisible + 1, ListView.Beginning) }
        }

        // Swipe, drag or use the arrows. All four systems stay in the same order.
        ListView {
            id: cards
            objectName: "cards"
            Layout.fillWidth: true
            Layout.preferredHeight: 226
            Layout.leftMargin: -14
            Layout.rightMargin: -14
            leftMargin: 14
            rightMargin: 14
            orientation: ListView.Horizontal
            snapMode: ListView.SnapToItem
            boundsBehavior: Flickable.StopAtBounds
            spacing: 16
            clip: false
            cacheBuffer: 2000
            model: 4
            delegate: AbstractButton {
                id: card
                required property int index
                readonly property var s: home.d.systems[index]
                width: home.cardWidth
                height: 212
                y: 2
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.Button
                Accessible.name: s.name + ". " + (s.learning ? "Learning." : Theme.statusWord(s.status) + ". Drift " + s.score + " of 100.") + " Open details."
                onClicked: vigil.navigate("/system/" + s.id)
                background: Rectangle {
                    color: Theme.panel
                    radius: Theme.radius
                    border.color: card.visualFocus ? Theme.action : Theme.isLight ? "transparent" : Theme.rule
                    border.width: card.visualFocus ? 2 : Theme.isLight ? 0 : 1
                    SoftShadow {}
                }
                contentItem: ColumnLayout {
                    spacing: 2
                    anchors { fill: parent; margins: 18 }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: card.s.name; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 19; color: Theme.ink; Layout.fillWidth: true; elide: Text.ElideRight }
                        Placard { visible: card.s.learning; text: "Learning" }
                        StatusPill { visible: !card.s.learning; status: card.s.status; compact: true }
                    }
                    RowLayout {
                        spacing: 8
                        Text { text: card.s.learning ? "-" : card.s.score; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 54; font.letterSpacing: -1.6; font.features: { "tnum": 1 }; color: Theme.ink }
                        Note { text: "drift of 100"; Layout.fillWidth: false; Layout.alignment: Qt.AlignBottom; bottomPadding: 11 }
                        Item { Layout.fillWidth: true }
                        Note { text: Math.round(card.s.confidence * 100) + "% confidence"; Layout.fillWidth: false; Layout.alignment: Qt.AlignBottom; bottomPadding: 11 }
                    }
                    Sparkline { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 40; values: card.s.trend; label: card.s.name; status: card.s.learning ? "green" : card.s.status }
                    Note {
                        maximumLineCount: 1
                        elide: Text.ElideRight
                        text: card.s.learning ? "Learning your normal" : card.s.flagged.length ? "Moved: " + card.s.flagged.map(function (id) { return home.names[id] || id }).join(", ") : "Inside your normal"
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 12
            visible: !vigil.demo.active
            spacing: 12
            Repeater {
                model: [["/checkin", "Check-in", "normal"], ["/radiation", "Radiation", "normal"], ["/crew", "Crew", "normal"], ["/earth", "Call Earth", "primary"]]
                VButton {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 62
                    textSize: 20
                    text: modelData[1]
                    kind: modelData[2]
                    onClicked: vigil.navigate(modelData[0])
                }
            }
        }
    }
}
