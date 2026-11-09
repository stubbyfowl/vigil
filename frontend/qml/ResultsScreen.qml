import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("results", { v: vigil.version })

    function verdict(e) {
        if (e.id === "solar_storm") return "Vigil passed on the monitor's warning " + Math.abs(e.vigil_vs_onset.mean) + " hours before onset. A fixed dose alarm fires " + e.fixed_alarm.mean + (e.fixed_alarm.mean === 1 ? " hour" : " hours") + " after onset."
        var quiet = e.fixed.quiet, lead = quiet.lead_vigil_earlier, missed = quiet.missed_by_fixed_found_by_vigil
        var never = missed > 0 ? " The fixed alarm never fired in " + missed + " of " + e.runs + " runs." : ""
        if (lead.n === 0 || lead.mean === null) return "A fixed alarm never fired." + never
        if (lead.mean >= 1) return "Vigil flagged this " + lead.mean.toFixed(1) + " days before the quieter fixed alarm." + never
        return "The quieter fixed alarm was about as fast here, within 1 day." + never
    }

    ColumnLayout {
        anchors.fill: parent
        visible: !screen.d.available
        BackButton {}
        BigTitle { text: "No results yet." }
        Body { text: "Run: make eval" }
        Item { Layout.fillHeight: true }
    }

    PageScroll {
        anchors.fill: parent
        visible: screen.d.available
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Measured, not claimed" }
            Item { Layout.fillWidth: true }
            Placard { text: (screen.d.seeds ? screen.d.seeds.length : 0) + " simulated missions · Held-out seeds · Simulated data only" }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Repeater {
                model: screen.d.events || []
                Panel {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                    divider: true
                    title: modelData.title
                    RowLayout {
                        spacing: 8
                        Text { text: modelData.detected + "/" + modelData.runs; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 46; font.letterSpacing: -1.4; font.features: { "tnum": 1 }; color: Theme.ink }
                        Note { text: "runs found"; Layout.fillWidth: false }
                    }
                    Note { text: modelData.id === "solar_storm" ? "Warning comes from the simulated solar monitor." : "First flag " + modelData.vigil_vs_onset.mean + " days after onset (sd " + modelData.vigil_vs_onset.sd + "). This event builds over several days." }
                    Body { text: screen.verdict(modelData) }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Repeater {
                model: screen.d.false_alarms ? [["False alarms per 100 days, quiet control", screen.d.false_alarms.quiet], ["False alarms per 100 days, all crew on non-event days", screen.d.false_alarms.non_event]] : []
                Panel {
                    id: bars
                    required property var modelData
                    readonly property var rows: [["Vigil, any alert", modelData[1].l1.mean], ["Vigil, Level 2 or more", modelData[1].l2.mean], ["Fixed limit, quiet", modelData[1].fixed_quiet.mean], ["Fixed limit, sensitive", modelData[1].fixed_sensitive.mean]]
                    readonly property real peak: Math.max.apply(null, rows.map(function (r) { return r[1] }))
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    divider: true
                    title: modelData[0]
                    Repeater {
                        model: bars.rows
                        RowLayout {
                            required property var modelData
                            spacing: 10
                            Body { text: modelData[0]; Layout.fillWidth: false; Layout.preferredWidth: 205 }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 14
                                radius: 7
                                color: Theme.panel2
                                Rectangle { width: parent.width * modelData[1] / bars.peak; height: parent.height; radius: 7; color: Theme.action }
                            }
                            Text { text: modelData[1]; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 18; color: Theme.ink; Layout.preferredWidth: 50; horizontalAlignment: Text.AlignRight }
                        }
                    }
                }
            }
        }
        Note { text: "We planted these events ourselves and chose their size, so this shows the method works in simulation. It says nothing about real people. Full table: docs/results.md." }
    }
}
