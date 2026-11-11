import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("explainer", { v: vigil.version })

    ColumnLayout {
        anchors.fill: parent
        visible: !screen.d.available
        BackButton {}
        BigTitle { text: "No matching day in this mission." }
        Item { Layout.fillHeight: true }
    }

    PageScroll {
        anchors.fill: parent
        visible: screen.d.available
        RowLayout { spacing: 12; BackButton {} BigTitle { text: "Two people, the same heart rate" } }
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Repeater {
                model: screen.d.available ? screen.d.people : []
                Panel {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                    surface: true
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Body { text: modelData.name; font.pixelSize: 22; font.weight: Font.Medium }
                            Note { text: modelData.role + ", day " + screen.d.day }
                        }
                        StatusPill { status: modelData.verdict === "alert" ? "red" : "green"; label: modelData.verdict === "alert" ? "Alert" : "Normal" }
                    }
                    RowLayout {
                        spacing: 12
                        Text { text: modelData.value; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 84; font.letterSpacing: -3; font.features: { "tnum": 1 }; color: Theme.ink }
                        Placard { text: "bpm today"; Layout.alignment: Qt.AlignBottom; bottomPadding: 14 }
                    }
                    Body { text: "Normal for " + modelData.name.split(" ")[0] + ": " + modelData.low + " to " + modelData.high + " bpm" }
                    SeriesChart { Layout.fillWidth: true; series: modelData.chart; chartHeight: 230 }
                    Body {
                        font.pixelSize: 21
                        text: modelData.verdict === "alert" ? "+" + (modelData.value - modelData.median).toFixed(1) + " bpm above their own normal for " + modelData.drift_days + " days." : "Inside this person's usual range."
                    }
                }
            }
        }
        Note { text: "Both readings come from the same day of this simulated mission. A single limit for everyone treats them the same. Vigil compares each reading with that person's own range, so only one of them raises an alert." }
    }
}
