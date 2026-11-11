import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The Commander adds the crew and keeps accounts working. Nobody here can read anyone's health data.
Item {
    id: screen
    property int refresh: 0
    readonly property var d: Api.ask("accounts_admin", { v: [vigil.version, refresh] })
    property string role: "crew"
    property var errors: ({})
    property string notice: ""
    property string failure: ""
    property var resetting: null

    function statusOf(m) {
        if (!m.active) return "Turned off"
        if (m.locked) return "Locked"
        if (m.must_change) return "Must choose a PIN"
        return "Active"
    }
    function run(name, args, done) {
        var out = Api.ask(name, args)
        failure = out.error || ""
        notice = out.error ? "" : done
        refresh += 1
        return out
    }
    function add() {
        var e = {}
        if (!memberName.text.trim()) e.name = "Enter a full name."
        if (pin.text.length < 4) e.pin = "A temporary PIN is 4 to 8 digits."
        errors = e
        if (Object.keys(e).length) return
        var out = run("add_member", { name: memberName.text, role: screen.role, pin: pin.text, prior_dose: Number(dose_.text || 0) },
                      memberName.text.trim() + " was added. Give them the temporary PIN. They choose their own at first sign-in.")
        if (!out.error) { memberName.text = ""; pin.text = ""; dose_.text = "0" }
    }

    Popup {
        id: resetDialog
        anchors.centerIn: Overlay.overlay
        width: 480
        modal: true
        padding: 28
        background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.rule }
        onOpened: { tempPin.text = ""; tempPin.input.forceActiveFocus() }
        ColumnLayout {
            anchors.fill: parent
            spacing: 14
            BigTitle { text: "Reset PIN"; font.pixelSize: 32 }
            Body { color: Theme.ink2; text: screen.resetting ? "Give " + screen.resetting.name + " a temporary PIN. They choose a new one when they sign in." : "" }
            Field { id: tempPin; label: "Temporary PIN"; secret: true; digits: true; maxLength: 8 }
            RowLayout {
                Layout.fillWidth: true
                VButton { text: "Cancel"; onClicked: resetDialog.close() }
                Item { Layout.fillWidth: true }
                VButton {
                    kind: "primary"
                    text: "Reset"
                    onClicked: {
                        screen.run("reset_member_pin", { member: screen.resetting.id, pin: tempPin.text }, "PIN reset for " + screen.resetting.name + ".")
                        resetDialog.close()
                    }
                }
            }
        }
    }

    Popup {
        id: archiveDialog
        anchors.centerIn: Overlay.overlay
        width: 560
        modal: true
        padding: 28
        background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.rule }
        ColumnLayout {
            anchors.fill: parent
            spacing: 14
            BigTitle { text: "Archive this mission?"; font.pixelSize: 32 }
            Body { color: Theme.ink2; text: "The mission file moves to the backups folder and everyone is signed out. Nothing is deleted. This computer can then start a new mission." }
            RowLayout {
                Layout.fillWidth: true
                VButton { text: "Keep the mission"; onClicked: archiveDialog.close() }
                Item { Layout.fillWidth: true }
                VButton { kind: "danger"; text: "Archive mission"; onClicked: { archiveDialog.close(); Api.ask("archive_mission", { confirm: true }) } }
            }
        }
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Accounts" }
            Item { Layout.fillWidth: true }
            VButton { text: "Audit log"; onClicked: vigil.navigate("/audit") }
            VButton { text: "Back up now"; onClicked: { var out = screen.run("backup", {}, ""); if (!out.error) screen.notice = "Backup saved to " + out.path } }
        }
        Banner { tone: "success"; text: screen.notice }
        Banner { tone: "error"; text: screen.failure }
        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                surface: true
                title: "Members"
                Repeater {
                    model: screen.d.members || []
                    RowLayout {
                        id: row
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 12
                        opacity: modelData.active ? 1 : 0.6
                        Avatar { size: 44; name: row.modelData.name; initials: row.modelData.tag }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Body { text: row.modelData.name; font.weight: Font.Medium; maximumLineCount: 1; elide: Text.ElideRight }
                            Note { text: row.modelData.role_name + " · " + screen.statusOf(row.modelData) }
                        }
                        VButton { visible: row.modelData.locked; text: "Unlock"; onClicked: screen.run("unlock_member", { member: row.modelData.id }, row.modelData.name + " can sign in again.") }
                        VButton { visible: screen.d.mode === "live"; text: "Reset PIN"; onClicked: { screen.resetting = row.modelData; resetDialog.open() } }
                        VButton {
                            visible: screen.d.mode === "live" && row.modelData.id !== vigil.session.id
                            kind: "quiet"
                            text: row.modelData.active ? "Turn off" : "Turn on"
                            onClicked: screen.run("update_member", { member: row.modelData.id, active: !row.modelData.active },
                                                  row.modelData.name + (row.modelData.active ? " can no longer sign in. Their data is kept." : " can sign in again."))
                        }
                    }
                }
            }
            Panel {
                Layout.fillWidth: true
                surface: true
                visible: screen.d.mode === "live"
                title: "Mission"
                Body { color: Theme.ink2; text: "When the mission is over, archive it. The file is kept in the backups folder." }
                VButton { kind: "danger"; text: "Archive this mission"; onClicked: archiveDialog.open() }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "Add a member"
                    Banner { visible: screen.d.mode === "demo"; text: "The demo crew is fixed. Set up a real mission to add people." }
                    ColumnLayout {
                        visible: screen.d.mode === "live"
                        Layout.fillWidth: true
                        spacing: 12
                        Field { id: memberName; label: "Full name"; maxLength: 40; error: screen.errors.name || "" }
                        Text { text: "Role"; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 17; color: Theme.ink }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: screen.d.roles || []
                                VButton { required property var modelData; text: modelData.name; selected: screen.role === modelData.id; onClicked: screen.role = modelData.id }
                            }
                        }
                        Note { text: screen.role === "ground" ? "Mission Control signs in on the ground station window, and sees only what packets carry." : screen.role === "medical" ? "The Medical Officer is told about Level 2 alerts and can enter lab results for anyone." : screen.role === "commander" ? "Commanders manage accounts and settings. They cannot read anyone's raw data." : "A crew member sees and enters only their own data." }
                        RowLayout {
                            spacing: 16
                            Field { id: dose_; visible: screen.role !== "ground"; label: "Prior career dose (mSv)"; text: "0"; maxLength: 6 }
                            Field { id: pin; label: "Temporary PIN"; secret: true; digits: true; maxLength: 8; error: screen.errors.pin || ""; onAccepted: screen.add() }
                        }
                        VButton { kind: "primary"; text: "Add member"; onClicked: screen.add() }
                    }
                },
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "Lock the screen after"
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: screen.d.auto_lock_choices || []
                            VButton {
                                required property int modelData
                                text: modelData + " min"
                                selected: screen.d.auto_lock_minutes === modelData
                                onClicked: screen.run("set_auto_lock", { minutes: modelData }, "The screen now locks after " + modelData + " idle minutes.")
                            }
                        }
                    }
                },
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    visible: screen.d.mode === "live"
                    title: "Folders on this computer"
                    Repeater {
                        model: screen.d.folders ? [["Outbox for Earth", screen.d.folders.outbox], ["Files to import", screen.d.folders.import], ["Exports", screen.d.folders.exports], ["Backups", screen.d.folders.backups]] : []
                        ColumnLayout {
                            required property var modelData
                            spacing: 0
                            Placard { text: modelData[0] }
                            Note { text: modelData[1]; wrapMode: Text.WrapAnywhere }
                        }
                    }
                }
            ]
        }
    }
}
