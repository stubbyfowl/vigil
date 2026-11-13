import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("earth_decision", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    property bool sent: false
    property string errorText: ""

    function send() {
        var out = Api.ask("call_earth", { astronaut: vigil.astronaut, note: note.text })
        if (out.error) errorText = out.error
        else sent = true
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            spacing: 12
            BackButton {}
            BigTitle { text: "Call Earth" }
            LevelBadge { level: screen.d.level; visible: screen.d.level > 0 || !(screen.d.learning || []).length }  // not "In range" before a range is known
        }
        Split {
            Layout.fillWidth: true
            Statement { lead: screen.d.title; detail: screen.d.detail; size: 36 }
            Note { visible: !!screen.d.reason; text: screen.d.reason || ""; font.pixelSize: 18 }
            Panel {
                Layout.fillWidth: true
                divider: true
                title: "One-way delay"
                Text { text: screen.d.delay_minutes + " minutes"; font.family: Theme.body; font.weight: Font.Medium; font.features: { "tnum": 1 }; font.pixelSize: 40; font.letterSpacing: -1; color: Theme.ink }
                Note { text: "A reply takes at least " + (screen.d.delay_minutes * 2) + " minutes." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "What Earth gets"
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: Object.keys(screen.d.preview.systems)
                            Row {
                                required property string modelData
                                spacing: 6
                                Placard { text: modelData.charAt(0).toUpperCase() + modelData.slice(1); anchors.verticalCenter: parent.verticalCenter }
                                StatusPill { status: screen.d.preview.systems[modelData]; compact: true }
                            }
                        }
                    }
                    Note { text: "System status and your note. Raw readings go too if you share them with Earth." }
                    ShareToggle { audience: "Earth"; field: "share_ground" }
                },
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: screen.sent ? "Sent" : "Note for Earth (optional)"
                    Body { visible: screen.sent; text: vigil.isDemo ? "It reaches Earth in " + screen.d.delay_minutes + " minutes." : "It is in the outbox for the comm system to send." }
                    VButton { visible: screen.sent && vigil.isDemo; text: "Show in Mission Control"; onClicked: vigil.navigate("/ground") }
                    TextField {
                        id: note
                        objectName: "note"
                        visible: !screen.sent
                        Layout.fillWidth: true
                        implicitHeight: Theme.touch
                        maximumLength: 280
                        font.family: Theme.body
                        font.pixelSize: 18
                        color: Theme.ink
                        Accessible.name: "Note to Earth"
                        background: Rectangle { color: Theme.panel2; border.color: note.activeFocus ? Theme.action : "transparent"; radius: 10 }
                    }
                    VButton { visible: !screen.sent; Layout.fillWidth: true; kind: "urgent"; text: screen.d.level >= 3 ? "Send priority packet" : "Send packet"; onClicked: screen.send() }
                    Body { visible: screen.errorText.length > 0; text: screen.errorText; color: Theme.warning }
                }
            ]
        }
    }
}
