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
                StatusPill { visible: !screen.d.learning; status: screen.d.status }
                Item { Layout.fillWidth: true }
                Placard { text: "Drift " + screen.d.score + " / 100 · Confidence " + Math.round(screen.d.confidence * 100) + "%" }
            }
            Note { text: "The shaded band is your usual range. Tap a chart to read a day." }
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
                        surface: true
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Body { text: tile.s.name; font.pixelSize: 19; font.weight: Font.Medium }
                                Note { visible: !tile.s.flagged_now; text: tile.s.learning ? "Needs more readings" : "In your usual range" }
                                StatusPill { visible: tile.s.flagged_now; status: "yellow"; compact: true; label: "Drifting for " + tile.s.drift_days + (tile.s.drift_days === 1 ? " day" : " days") }
                            }
                            Text { text: tile.s.current === null ? "--" : tile.s.current.toFixed(tile.s.decimals); font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 32; font.letterSpacing: -0.8; font.features: { "tnum": 1 }; color: Theme.ink }
                            Placard { text: tile.s.unit; Layout.alignment: Qt.AlignBottom; bottomPadding: 5 }
                        }
                        SeriesChart { Layout.fillWidth: true; series: tile.s; chartHeight: 170 }
                    }
                }
            }
        }
    }
}
