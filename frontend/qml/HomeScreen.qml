import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: home
    readonly property var d: Api.ask("astronaut", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var story: vigil.narrator ? (Api.ask("narration", { id: vigil.astronaut, day: vigil.day, v: vigil.version }).lines || []) : []
    readonly property var notices: (Api.ask("notices", { id: vigil.astronaut, v: [vigil.version, vigil.day] }).notices || []).slice(0, 3)
    readonly property var names: {
        var out = {}
        Api.ask("crew", {}).signals.forEach(function (s) { out[s.id] = s.name })
        return out
    }
    readonly property var drifting: d.systems.filter(function (s) { return !s.learning && s.status !== "green" })
    readonly property var waiting: d.systems.filter(function (s) { return s.learning })
    readonly property var topAlert: d.alerts.length ? d.alerts[0] : null
    readonly property var hottest: {
        var best = null
        d.systems.forEach(function (s) { if (!s.learning && (!best || s.score > best.score)) best = s })
        return best
    }
    readonly property int worst: {
        var best = -1, score = -1
        d.systems.forEach(function (s, i) { if (s.status !== "green" && s.score > score) { best = i; score = s.score } })
        return best
    }
    readonly property string headline: topAlert ? topAlert.system_name + " alert"
        : d.learning ? "Building baseline"
        : drifting.length ? drifting.map(function (s) { return s.name }).join(" and ") + " drifting"
        : waiting.length ? "No drift found"
        : "All systems normal"
    readonly property int cardWidth: 340
    // Where the carousel is, in cards. Arrows step to the next card that is even partly hidden.
    readonly property real position: (cards.contentX - cards.originX) / (cardWidth + cards.spacing)
    onWorstChanged: if (worst >= 0) cards.positionViewAtIndex(worst, ListView.Contain)

    function signed(row) {
        var v = Math.round(row.change * 100) / 100
        var unit = row.unit === "C" ? "°C" : row.unit
        return (v >= 0 ? "+" : "−") + (/ to /.test(unit) ? Math.abs(v) + (Math.abs(v) === 1 ? " point" : " points") : Theme.amount(Math.abs(v), unit))
    }

    // Fills the page when it fits. A short window scrolls, so the buttons at the bottom stay reachable.
    Flickable {
        id: homeFlick
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: Math.max(height, homeColumn.implicitHeight)
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        readonly property bool scrolls: homeColumn.implicitHeight > height + 1
        ScrollBar.vertical: ScrollBar { policy: homeFlick.scrolls ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff }
    ColumnLayout {
        id: homeColumn
        width: homeFlick.width - (homeFlick.scrolls ? 18 : 0)
        height: homeFlick.contentHeight
        spacing: 0

        LabTicker { Layout.fillWidth: true; Layout.bottomMargin: 6 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 40

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 10
                Placard { Layout.topMargin: 10; text: home.d.astronaut.name + "  ·  " + home.d.astronaut.role + "  ·  Day " + home.d.day }
                Text {
                    text: home.headline
                    font.family: Theme.display
                    font.weight: Font.ExtraBold
                    font.pixelSize: home.headline.length > 22 ? 46 : 58
                    font.letterSpacing: -1.6
                    color: Theme.ink
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.Heading
                    Accessible.name: text
                }
                RowLayout {
                    visible: !!home.topAlert
                    Layout.fillWidth: true
                    spacing: 12
                    LevelBadge { level: home.topAlert ? home.topAlert.level : 0 }
                    Note { text: home.topAlert ? home.topAlert.level_reason : "" }
                }
                Note {
                    visible: !home.topAlert
                    Layout.maximumWidth: 640
                    text: home.d.learning ? "Vigil needs about 10 days of readings before it can tell a change from this person's usual range."
                        : home.drifting.length ? "The change is too small to raise an alert."
                        : home.waiting.length ? home.waiting.map(function (s) { return s.name }).join(" and ") + (home.waiting.length === 1 ? " needs" : " need") + " more readings. The other systems are inside this person's usual range."
                        : "Every system is inside this person's usual range."
                }

                // What changed, as a table: reading, change from usual, how long.
                ColumnLayout {
                    visible: !!home.topAlert
                    Layout.topMargin: 6
                    Layout.maximumWidth: 640
                    spacing: 0
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.rule }
                    Repeater {
                        model: home.topAlert ? home.topAlert.why.signals.slice(0, 3) : []
                        ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 0
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 40
                                spacing: 16
                                Body { text: modelData.name; Layout.fillWidth: true; elide: Text.ElideRight; maximumLineCount: 1 }
                                Text { text: home.signed(modelData); font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 18; font.features: { "tnum": 1 }; color: Theme.ink }
                                Placard { Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight; text: modelData.days_of_drift + (modelData.days_of_drift === 1 ? " day" : " days") }
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.rule }
                        }
                    }
                }

                // The narrator reads the top reminder, the way a wildlife film would. Off unless chosen in the Menu.
                Rectangle {
                    visible: home.story.length > 0
                    Layout.fillWidth: true
                    Layout.maximumWidth: 640
                    Layout.topMargin: 8
                    implicitHeight: narratorRow.implicitHeight + 24
                    radius: Theme.radius
                    color: Theme.panel
                    border.width: 1
                    border.color: Theme.rule
                    RowLayout {
                        id: narratorRow
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 16; rightMargin: 12 }
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Placard { text: "Narrator" }
                            Text { Layout.fillWidth: true; text: home.story[0] || ""; wrapMode: Text.WordWrap; font.family: Theme.body; font.italic: true; font.pixelSize: 17; color: Theme.ink }
                        }
                        VButton { visible: vigil.canSpeak; text: "Listen"; Accessible.name: "Read the narrator's line aloud"; onClicked: vigil.speak(home.story[0]) }
                    }
                }

                Flow {
                    Layout.topMargin: 8
                    Layout.fillWidth: true
                    spacing: 8
                    visible: !!home.topAlert || (home.notices.length > 0 && !vigil.demo.active)
                    VButton { visible: !!home.topAlert; kind: "primary"; text: "View alert"; onClicked: vigil.navigate("/alert/" + home.topAlert.id) }
                    Repeater {
                        model: vigil.demo.active ? [] : home.notices
                        VButton {
                            required property var modelData
                            kind: modelData.kind === "crew" ? "danger" : "quiet"
                            text: modelData.title
                            onClicked: vigil.navigate(modelData.route)
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 6
                spacing: 6
                Gauge {
                    Layout.alignment: Qt.AlignHCenter
                    size: 230
                    numberSize: 72
                    value: home.hottest ? home.hottest.score : 0
                    status: home.hottest ? home.hottest.status : "green"
                    learning: !home.hottest
                    label: "Highest drift today"
                }
                Placard { Layout.alignment: Qt.AlignHCenter; Layout.maximumWidth: 260; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: !home.hottest ? "No baseline yet" : home.hottest.score > 0 ? "Highest drift · " + home.hottest.name : "No drift today" }
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: 6 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Placard { text: "Systems  ·  tap one for its readings and more"; Layout.fillWidth: true; elide: Text.ElideRight }
            VButton { text: "‹"; textSize: 24; Accessible.name: "Previous system"; enabled: !cards.atXBeginning; onClicked: cards.positionViewAtIndex(Math.max(0, Math.ceil(home.position - 0.01) - 1), ListView.Beginning) }
            VButton { text: "›"; textSize: 24; Accessible.name: "Next system"; enabled: !cards.atXEnd; onClicked: cards.positionViewAtIndex(Math.min(cards.count - 1, Math.floor(home.position + 0.01) + 1), ListView.Beginning) }
        }

        // Swipe, drag or use the arrows. All four systems stay in the same order. Each card opens its detail.
        ListView {
            id: cards
            objectName: "cards"
            Layout.fillWidth: true
            Layout.topMargin: 8
            Layout.preferredHeight: 214
            orientation: ListView.Horizontal
            snapMode: ListView.SnapToItem
            boundsBehavior: Flickable.StopAtBounds
            spacing: 16
            clip: true
            cacheBuffer: 2000
            model: 4
            delegate: AbstractButton {
                id: card
                required property int index
                readonly property var s: home.d.systems[index]
                width: home.cardWidth
                height: 210
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.Button
                Accessible.name: s.name + ". " + (s.learning ? "No baseline yet." : Theme.statusWord(s.status) + ". Drift " + s.score + " of 100.") + " Open details."
                onClicked: vigil.navigate("/system/" + s.id)
                background: Rectangle {
                    color: Theme.panel
                    radius: Theme.radius
                    border.color: card.visualFocus ? Theme.link : card.hovered ? Theme.ink2 : Theme.rule
                    border.width: card.visualFocus ? 2 : 1
                    Rectangle {
                        visible: !card.s.learning && card.s.status !== "green"
                        anchors { left: parent.left; right: parent.right; top: parent.top }
                        height: 3
                        color: Theme.statusColor(card.s.status)
                    }
                    SoftShadow {}
                }
                contentItem: ColumnLayout {
                    spacing: 6
                    anchors { fill: parent; margins: 18 }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: card.s.name; font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 18; color: Theme.ink; Layout.fillWidth: true; elide: Text.ElideRight }
                        StatusPill { visible: !card.s.learning; status: card.s.status; compact: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 12
                        Gauge { size: 92; numberSize: 26; value: card.s.score; status: card.s.status; learning: card.s.learning; label: card.s.name }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 4
                            Sparkline { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 44; values: card.s.trend; label: card.s.name; status: card.s.learning ? "green" : card.s.status }
                            Placard { text: "30 days  ·  " + Math.round(card.s.confidence * 100) + "% data"; font.pixelSize: 11; font.letterSpacing: 1.4 }
                        }
                    }
                    Note {
                        maximumLineCount: 1
                        elide: Text.ElideRight
                        text: card.s.learning ? "Needs more readings" : card.s.flagged.length ? "Moved: " + card.s.flagged.map(function (id) { return home.names[id] || id }).join(", ") : "In the usual range"
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 14
            visible: !vigil.demo.active
            spacing: 12
            Repeater {
                model: vigil.isDemo ? [["/checkin", "Check in", "normal"], ["/chat", "Organ chat", "normal"], ["/radiation", "Radiation", "normal"], ["/crew", "Crew", "normal"], ["/earth", "Call Earth", "urgent"]]
                                    : [["/checkin", "Check in", "normal"], ["/log", "Log readings", "normal"], ["/chat", "Organ chat", "normal"], ["/crew", "Crew", "normal"], ["/earth", "Call Earth", "urgent"]]
                VButton {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 60
                    textSize: 18
                    text: modelData[1]
                    kind: modelData[2]
                    onClicked: vigil.navigate(modelData[0])
                }
            }
        }
    }
    }
}
