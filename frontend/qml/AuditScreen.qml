import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Who did what, and when. It never holds PINs, readings or journal words.
Item {
    id: screen
    readonly property var events: Api.ask("audit_log", { v: vigil.version }).events || []
    readonly property var words: ({
        signed_in: "Signed in", sign_in_refused: "Sign-in refused", signed_out: "Signed out", locked: "Locked the screen",
        auto_locked: "Screen locked when idle", unlocked: "Unlocked", unlock_refused: "Unlock refused", pin_changed: "Changed their PIN",
        pin_reset: "Reset a PIN", member_added: "Added a member", member_changed: "Changed a member", member_unlocked: "Unlocked a member",
        readings_logged: "Logged readings", reading_deleted: "Removed a reading", readings_imported: "Imported readings",
        data_exported: "Exported data", report_made: "Made a health summary", backup_made: "Made a backup",
        auto_lock_changed: "Changed the screen lock", thresholds_changed: "Changed thresholds", mission_created: "Created the mission",
        mission_archived: "Archived the mission"
    })

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            spacing: 12
            BackButton {}
            BigTitle { text: "Audit log" }
            Placard { text: "Latest " + screen.events.length + " events" }
        }
        Note { text: "Sign-ins, account changes, exports and data entry. Readings and journal words are kept out of it." }
        Banner { visible: screen.events.length === 0; text: "Nothing has happened yet." }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: screen.events
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                required property int index
                width: ListView.view.width
                height: 52
                radius: 8
                color: index % 2 ? "transparent" : Theme.panel2
                RowLayout {
                    anchors { fill: parent; leftMargin: 14; rightMargin: 14 }
                    spacing: 16
                    Text { Layout.preferredWidth: 180; text: modelData.when; font.family: Theme.body; font.pixelSize: 16; font.features: { "tnum": 1 }; color: Theme.ink2 }
                    Text { Layout.preferredWidth: 190; text: modelData.who; elide: Text.ElideRight; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 17; color: Theme.ink }
                    Text { Layout.preferredWidth: 250; text: screen.words[modelData.action] || modelData.action.replace(/_/g, " "); font.family: Theme.body; font.pixelSize: 17; color: Theme.ink }
                    Text { Layout.fillWidth: true; text: [modelData.about, modelData.detail].filter(function (x) { return x }).join(" · "); elide: Text.ElideRight; font.family: Theme.body; font.pixelSize: 16; color: Theme.ink2 }
                }
            }
        }
    }
}
