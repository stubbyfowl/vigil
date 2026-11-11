import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("about", {})

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
                Note { text: screen.d.must_verify_count + " reference figures still need checking against sources. The list is in SOURCES.md." }
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
        Panel {
            Layout.fillWidth: true
            divider: true
            title: "Sources to check"
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 12
                rowSpacing: 8
                Placard { text: "Source"; Layout.preferredWidth: 4; Layout.fillWidth: true }
                Placard { text: "Use"; Layout.preferredWidth: 4; Layout.fillWidth: true }
                Placard { text: "Status"; Layout.preferredWidth: 1; Layout.fillWidth: true }
                Repeater {
                    model: screen.d.sources.length * 3
                    Body {
                        required property int index
                        readonly property var row: screen.d.sources[Math.floor(index / 3)]
                        Layout.preferredWidth: index % 3 === 2 ? 1 : 4
                        font.bold: index % 3 === 0
                        text: index % 3 === 0 ? row.name : index % 3 === 1 ? row.use : row.status
                    }
                }
            }
        }
    }
}
