import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("crew_view", { day: vigil.day, v: vigil.version })

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Crew" }
            Item { Layout.fillWidth: true }
            Text { text: screen.d.summary; font.family: Theme.body; font.pixelSize: 25; color: Theme.ink }
        }
        Repeater {
            model: screen.d.crew.length
            Panel {
                id: row
                required property int index
                readonly property var m: screen.d.crew[index]
                Layout.fillWidth: true
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    ColumnLayout {
                        Layout.fillWidth: false
                        Layout.minimumWidth: 220
                        Layout.maximumWidth: 220
                        spacing: 4
                        Body { text: row.m.name; font.pixelSize: 20; font.bold: true }
                        Note { text: row.m.role }
                        LevelBadge { visible: row.m.max_level > 0; level: row.m.max_level; compact: true; label: "Level " + row.m.max_level }
                    }
                    Repeater {
                        model: 4
                        ColumnLayout {
                            required property int index
                            readonly property var s: row.m.systems[index]
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 4
                            Placard { text: s.name }
                            Note { visible: s.learning; text: "Learning" }
                            Annunciator { visible: !s.learning; status: s.status }
                            Sparkline { Layout.fillWidth: true; Layout.preferredHeight: 44; values: s.trend; label: row.m.name + " " + s.name }
                        }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Note { text: "The crew sees trends and status only. Raw values and journal text stay private." }
            ShareToggle { audience: "the crew"; field: "share_crew" }
        }
    }
}
