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
            LevelBadge { level: screen.d.level }
        }
        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                title: "Vigil's decision"
                BigTitle { text: screen.d.title; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Body { text: screen.d.detail }
                Note { visible: !!screen.d.reason; text: screen.d.reason || ""; font.pixelSize: 18 }
            }
            Panel {
                Layout.fillWidth: true
                title: "One-way delay"
                Text { text: screen.d.delay_minutes + " min"; font.family: Theme.mono; font.bold: true; font.pixelSize: 56; color: Theme.ink }
                Note { text: "Any reply takes at least " + (screen.d.delay_minutes * 2) + " minutes. Act on the checklist first." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    title: "What Earth will receive"
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: Object.keys(screen.d.preview.systems)
                            Row {
                                required property string modelData
                                spacing: 6
                                Placard { text: modelData; anchors.verticalCenter: parent.verticalCenter }
                                Annunciator { status: screen.d.preview.systems[modelData]; compact: true }
                            }
                        }
                    }
                    Note { text: "Status only. No raw values and no journal text." }
                    ShareToggle { audience: "Earth"; field: "share_ground" }
                },
                Panel {
                    Layout.fillWidth: true
                    title: screen.sent ? "Sent" : "Add a short note (optional)"
                    Body { visible: screen.sent; text: "Your packet is on its way. It reaches Earth in " + screen.d.delay_minutes + " minutes." }
                    VButton { visible: screen.sent; text: "Watch it travel"; onClicked: vigil.navigate("/ground") }
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
                        background: Rectangle { color: Theme.panel2; border.color: note.activeFocus ? Theme.action : Theme.rule; radius: 4 }
                    }
                    VButton { visible: !screen.sent; Layout.fillWidth: true; kind: "primary"; text: screen.d.level >= 3 ? "Send priority packet" : "Send packet"; onClicked: screen.send() }
                    Body { visible: screen.errorText.length > 0; text: screen.errorText; color: Theme.warning }
                }
            ]
        }
    }
}
