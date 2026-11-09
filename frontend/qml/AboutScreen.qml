import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("about", {})

    PageScroll {
        anchors.fill: parent
        RowLayout { spacing: 12; BackButton {} BigTitle { text: "About and honesty" } }
        Panel { Layout.fillWidth: true; title: "Data honesty"; Body { text: screen.d.statement; font.pixelSize: 25 } }
        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                title: "What this is"
                Body { text: "Vigil is a student prototype for the NASA Space Apps Challenge. No flight surgeon has reviewed it. The crew are invented. Protocols are samples, not medical advice." }
                Note { text: screen.d.must_verify_count + " reference figures are still marked \"must verify\". See data/real_ranges.json and SOURCES.md." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    title: "Privacy"
                    Body { text: "Vigil opens no network connections and listens on no ports. Journal text is scored on this computer and is not stored unless you choose to keep it." }
                    Note { text: "Typefaces: B612, made for cockpit screens, and Barlow Condensed." }
                }
            ]
        }
        Panel {
            Layout.fillWidth: true
            title: "Planned sources"
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 12
                rowSpacing: 8
                Placard { text: "Source"; Layout.preferredWidth: 4; Layout.fillWidth: true }
                Placard { text: "Planned use"; Layout.preferredWidth: 4; Layout.fillWidth: true }
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
