import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("about", {})
    readonly property var groups: {
        var seen = []
        screen.d.sources.forEach(function (s) { if (seen.indexOf(s.group) < 0) seen.push(s.group) })
        return seen
    }
    function counts(status) { return screen.d.sources.filter(function (s) { return s.status === status }).length }

    PageScroll {
        anchors.fill: parent
        RowLayout { spacing: 12; BackButton {} BigTitle { text: "About Vigil" } }
        Statement { lead: vigil.isDemo ? "The demo crew and all their readings are simulated." : "Readings come from what your crew enters."; detail: "A flight surgeon has not reviewed the thresholds, and Vigil does not diagnose anything."; size: 36 }
        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                divider: true
                title: "What Vigil is"
                Body { text: "A student project for the 2026 NASA Space Apps Challenge in Phoenix. The self-care protocols are samples the team wrote." }
                Note { text: screen.d.must_verify_count + " reference figures still need a source. They are marked must_verify in data/real_ranges.json." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    divider: true
                    title: "Privacy"
                    Body { text: "Vigil opens no network connections and listens on no ports. Journal words are scored on this computer and deleted unless you choose to keep them." }
                    Note { text: "Typefaces: Inter, Public Sans and DM Mono, after nasa.gov." }
                }
            ]
        }
        // The source catalog, grouped by topic. Each tag says how much of the source the team read.
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 8
            spacing: 24
            BigTitle { text: "Sources"; font.pixelSize: 28 }
            Placard {
                Layout.fillWidth: true
                text: screen.counts("verified") + " verified  ·  " + screen.counts("partly verified") + " from summaries  ·  " + screen.counts("not used yet") + " not used yet"
            }
        }
        Note {
            text: "Reference figures: " + screen.d.figure_counts["verified"] + " verified, " + screen.d.figure_counts["partly verified"] + " from summaries, "
                + screen.d.figure_counts["team choice"] + " defined by the team, " + screen.d.figure_counts["must_verify"] + " still need a source. The full list is in SOURCES.md and data/real_ranges.json."
        }
        Repeater {
            model: screen.groups
            Panel {
                id: groupPanel
                required property string modelData
                Layout.fillWidth: true
                divider: true
                title: modelData
                Repeater {
                    model: screen.d.sources.filter(function (s) { return s.group === groupPanel.modelData })
                    RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 16
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Body { text: modelData.name; font.weight: Font.DemiBold }
                            Note { text: modelData.use }
                            Placard { text: "Read: " + modelData.checked + "  ·  " + modelData.url.replace("https://", "").split("/")[0]; font.pixelSize: 11; font.letterSpacing: 1.2 }
                        }
                        StatusPill {
                            Layout.alignment: Qt.AlignTop
                            compact: true
                            status: modelData.status === "verified" ? "green" : modelData.status === "partly verified" ? "yellow" : "none"
                            label: modelData.status === "verified" ? "Verified" : modelData.status === "partly verified" ? "Summary only" : "Not used yet"
                        }
                    }
                }
            }
        }
    }
}
