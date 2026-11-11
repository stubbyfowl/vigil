import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Your account: who can see your data, your PIN, and taking your data with you.
Item {
    id: screen
    readonly property bool crewMember: ["commander", "medical", "crew"].indexOf(vigil.role) >= 0 || vigil.role === "presenter"
    property string exported: ""
    property string exportError: ""

    function exportCsv() {
        var out = Api.ask("export_data", { id: vigil.astronaut })
        exportError = out.error || ""
        exported = out.error ? "" : "Saved " + out.path
    }
    function exportPdf() {
        var out = JSON.parse(vigil.exportReport())
        exportError = out.error || ""
        exported = out.error ? "" : "Saved " + out.path
    }

    ChangePinDialog { id: pinDialog }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            spacing: 14
            BackButton {}
            Avatar { size: 56; name: vigil.session.name || ""; initials: vigil.session.tag || "" }
            ColumnLayout {
                spacing: 0
                BigTitle { text: vigil.session.name || ""; font.pixelSize: 32 }
                Note { text: vigil.session.role_name || "" }
            }
            Item { Layout.fillWidth: true }
            VButton { text: "Lock now"; onClicked: vigil.lock() }
            VButton { kind: "primary"; text: "Sign out"; onClicked: vigil.signOut() }
        }
        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                visible: screen.crewMember
                surface: true
                title: "Who can see your readings"
                Body { color: Theme.ink2; text: "The crew and Earth always see your status: Normal, Drifting or Alert. Raw readings and journal words reach them only if you turn these on." }
                ShareToggle { audience: "the crew"; field: "share_crew" }
                ShareToggle { audience: "Earth"; field: "share_ground" }
            }
            Panel {
                Layout.fillWidth: true
                surface: true
                title: "Security"
                Body { color: Theme.ink2; text: "The screen locks after a few idle minutes. The Commander sets how long." }
                VButton { text: "Change PIN"; onClicked: pinDialog.open() }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    visible: screen.crewMember
                    surface: true
                    title: "Export"
                    Body { color: Theme.ink2; text: "Files go to the exports folder on this computer." }
                    RowLayout {
                        spacing: 12
                        VButton { text: "Health summary (PDF)"; onClicked: screen.exportPdf() }
                        VButton { text: "All my data (CSV)"; onClicked: screen.exportCsv() }
                    }
                    Banner { tone: "success"; text: screen.exported }
                    Banner { tone: "error"; text: screen.exportError }
                }
            ]
        }
    }
}
