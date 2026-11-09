import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property string system: vigil.route.split("/")[2] || ""
    readonly property var fresh: Api.ask("system_detail", { id: vigil.astronaut, system: system, day: vigil.day, v: vigil.version })
    property var d: null
    onFreshChanged: if (!fresh.error) d = fresh
    Component.onCompleted: if (!fresh.error) d = fresh

    ErrorMessage { anchors.fill: parent; visible: screen.d === null; text: screen.fresh.error || "" }

    Loader {
        anchors.fill: parent
        active: screen.d !== null
        sourceComponent: PageScroll {
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                BackButton {}
                BigTitle { text: screen.d.name }
                Annunciator { visible: !screen.d.learning; status: screen.d.status }
                Item { Layout.fillWidth: true }
                Placard { text: "Drift " + screen.d.score + " / 100 · Confidence " + Math.round(screen.d.confidence * 100) + "%" }
            }
            Note { text: "The shaded band is your own normal. Tap a chart to read any day." }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 12
                rowSpacing: 12
                Repeater {
                    model: screen.d.signals.length
                    Panel {
                        id: tile
                        required property int index
                        readonly property var s: screen.d.signals[index]
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Body { text: tile.s.name; font.pixelSize: 20; font.bold: true }
                                Note { visible: !tile.s.flagged_now; text: tile.s.learning ? "Learning your normal" : "Inside your normal" }
                                Rectangle {
                                    visible: tile.s.flagged_now
                                    color: Theme.caution
                                    implicitWidth: tagText.implicitWidth + 16
                                    implicitHeight: 26
                                    Placard { id: tagText; anchors.centerIn: parent; text: "Drifting " + tile.s.drift_days + " d"; color: Theme.onLit; font.pixelSize: 18 }
                                }
                            }
                            Text { text: tile.s.current === null ? "--" : tile.s.current.toFixed(tile.s.decimals); font.family: Theme.body; font.bold: true; font.pixelSize: 30; color: Theme.ink }
                            Placard { text: tile.s.unit; Layout.alignment: Qt.AlignBottom }
                        }
                        SeriesChart { Layout.fillWidth: true; series: tile.s; chartHeight: 170 }
                    }
                }
            }
        }
    }
}
